#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const root = path.resolve(__dirname, '..');
const args = process.argv.slice(2);

function getArg(name, fallback = '') {
  const i = args.indexOf(`--${name}`);
  if (i >= 0 && i + 1 < args.length) return args[i + 1];
  return fallback;
}

function hasFlag(name) {
  return args.includes(`--${name}`);
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeFile(file, content) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, content, 'utf8');
}

function today() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function sh(cmd, options = {}) {
  return cp.execSync(cmd, {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
    ...options
  });
}

function safeReadOpenClawEnv(key) {
  try {
    const p = path.join(process.env.HOME || '', '.openclaw', 'openclaw.json');
    const data = JSON.parse(fs.readFileSync(p, 'utf8'));
    return data?.env?.[key] || '';
  } catch {
    return '';
  }
}

function parseTavilyOutput(text) {
  const lines = text.split('\n');
  let answer = '';
  const sources = [];
  let inAnswer = false;
  let inSources = false;

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith('📝 Answer:')) {
      inAnswer = true;
      inSources = false;
      continue;
    }
    if (line.startsWith('🔗 Sources:')) {
      inAnswer = false;
      inSources = true;
      continue;
    }
    if (line.startsWith('Searching:')) continue;
    if (inAnswer) {
      answer += (answer ? ' ' : '') + line;
      continue;
    }
    if (inSources && line.startsWith('- ')) {
      sources.push({ title: line.slice(2), url: '' });
      continue;
    }
    if (inSources && /^https?:\/\//.test(line)) {
      if (sources.length) sources[sources.length - 1].url = line;
    }
  }

  return { answer, sources };
}

function runTavily(query) {
  const tavilyKey = process.env.TAVILY_API_KEY || safeReadOpenClawEnv('TAVILY_API_KEY');
  if (!tavilyKey) {
    return { ok: false, reason: 'TAVILY_API_KEY not configured', answer: '', sources: [] };
  }

  const skillDir = path.join(process.env.HOME || '', '.agents', 'skills', 'tavily-search');
  const script = path.join(skillDir, 'scripts', 'search');
  if (!fs.existsSync(script)) {
    return { ok: false, reason: 'tavily-search skill script not found', answer: '', sources: [] };
  }

  try {
    const output = sh(`${script} ${JSON.stringify(query)}`, {
      env: { ...process.env, TAVILY_API_KEY: tavilyKey },
      cwd: root,
      maxBuffer: 1024 * 1024 * 8
    });
    return { ok: true, ...parseTavilyOutput(output), raw: output };
  } catch (err) {
    return {
      ok: false,
      reason: err.stderr || err.message || 'Unknown Tavily error',
      answer: '',
      sources: []
    };
  }
}

const date = getArg('date', today());
const topic = getArg('topic', '未命名选题');
const mode = getArg('mode', 'mvp');
const title = getArg('title', topic);
const dryRun = hasFlag('dry-run');
const withSearch = hasFlag('with-search') || mode === 'search-enhanced';
const searchQuery = getArg('query', `${topic} AI 效率工具 小红书 选题 趋势`);

const configDir = path.join(root, 'config');
const workflow = readJson(path.join(configDir, 'workflow.json'));
const models = readJson(path.join(configDir, 'models.json'));
const search = readJson(path.join(configDir, 'search.json'));

const runDir = path.join(root, 'runs', date);
const manifestPath = path.join(runDir, 'manifest.json');
const sourcesPath = path.join(runDir, 'sources.json');

const stepFiles = [
  ['01-trends.md', '# Run ${date} / Step 01 / Trends\n\n- Topic: ${topic}\n- Mode: ${mode}\n- Agent: trend-radar\n- Model: ${trendModel}\n- Search: ${trendSearch}\n\n## Notes\n\n'],
  ['02-topics.md', '# Run ${date} / Step 02 / Topics\n\n- Topic: ${topic}\n- Agent: topic-planner\n- Model: ${topicModel}\n\n## Candidate Topics\n\n'],
  ['03-draft.md', '# Run ${date} / Step 03 / Draft\n\n- Selected Title: ${title}\n- Agent: copywriter\n- Model: ${copyModel}\n\n## Draft\n\n'],
  ['04-reviewed.md', '# Run ${date} / Step 04 / Reviewed\n\n- Selected Title: ${title}\n- Agent: style-reviewer\n- Model: ${reviewModel}\n\n## Review\n\n'],
  ['05-publish-pack.md', '# Run ${date} / Step 05 / Publish Pack\n\n- Selected Title: ${title}\n- Agent: launch-analyst\n- Model: ${launchModel}\n\n## Publish Checklist\n\n']
];

const vars = {
  date,
  topic,
  mode,
  title,
  trendModel: models.agents['trend-radar'] || models.default,
  topicModel: models.agents['topic-planner'] || models.default,
  copyModel: models.agents['copywriter'] || models.default,
  reviewModel: models.agents['style-reviewer'] || models.default,
  launchModel: models.agents['launch-analyst'] || models.default,
  trendSearch: (search['trend-radar'] || []).join(', ') || 'none'
};

function render(tpl, vars) {
  return tpl.replace(/\$\{(\w+)\}/g, (_, k) => (vars[k] ?? ''));
}

const manifest = {
  name: workflow.name,
  version: workflow.version,
  date,
  mode,
  topic,
  title,
  runDir,
  createdAt: new Date().toISOString(),
  steps: workflow.steps,
  humanCheckpoints: workflow.humanCheckpoints,
  models: models.agents,
  search,
  searchEnabled: withSearch,
  searchQuery: withSearch ? searchQuery : '',
  files: stepFiles.map(([name]) => name)
};

if (dryRun) {
  console.log(JSON.stringify(manifest, null, 2));
  process.exit(0);
}

ensureDir(runDir);
writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
for (const [name, tpl] of stepFiles) {
  writeFile(path.join(runDir, name), render(tpl, vars));
}

if (withSearch) {
  const result = runTavily(searchQuery);
  writeFile(sourcesPath, JSON.stringify(result, null, 2) + '\n');

  const trendsFile = path.join(runDir, '01-trends.md');
  const base = fs.readFileSync(trendsFile, 'utf8');
  let appended = '\n## Search Query\n\n' + searchQuery + '\n';

  if (result.ok) {
    appended += '\n## Tavily Summary\n\n' + (result.answer || 'No summary returned.') + '\n';
    appended += '\n## Sources\n\n';
    if (result.sources.length) {
      for (const s of result.sources) {
        appended += `- ${s.title}${s.url ? `\n  ${s.url}` : ''}\n`;
      }
    } else {
      appended += '- No sources returned\n';
    }
  } else {
    appended += '\n## Search Error\n\n' + result.reason + '\n';
  }

  fs.writeFileSync(trendsFile, base + appended, 'utf8');
}

console.log(`Initialized run: ${runDir}`);
console.log(`Topic: ${topic}`);
console.log(`Mode: ${mode}`);
if (withSearch) console.log(`Search query: ${searchQuery}`);
console.log(`Files:`);
for (const [name] of stepFiles) console.log(`- ${name}`);
if (withSearch) console.log(`- sources.json`);
console.log(`- manifest.json`);
