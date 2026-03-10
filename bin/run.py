#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()


def today_str() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def read_json(p: Path):
    return json.loads(p.read_text(encoding='utf-8'))


def write_text(p: Path, content: str):
    ensure_dir(p.parent)
    p.write_text(content, encoding='utf-8')


def render(template: str, vars_: dict) -> str:
    def repl(match):
        key = match.group(1)
        return str(vars_.get(key, ''))
    return re.sub(r'\$\{(\w+)\}', repl, template)


def safe_read_openclaw_env(key: str) -> str:
    p = HOME / '.openclaw' / 'openclaw.json'
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        return data.get('env', {}).get(key, '')
    except Exception:
        return ''


def parse_tavily_output(text: str):
    lines = text.splitlines()
    answer = ''
    sources = []
    in_answer = False
    in_sources = False

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if line.startswith('📝 Answer:'):
            in_answer = True
            in_sources = False
            continue
        if line.startswith('🔗 Sources:'):
            in_answer = False
            in_sources = True
            continue
        if line.startswith('Searching:'):
            continue
        if in_answer:
            answer += (' ' if answer else '') + line
            continue
        if in_sources and line.startswith('- '):
            sources.append({'title': line[2:], 'url': ''})
            continue
        if in_sources and line.startswith('http'):
            if sources:
                sources[-1]['url'] = line

    return {'answer': answer, 'sources': sources}


def run_tavily(query: str):
    tavily_key = os.environ.get('TAVILY_API_KEY') or safe_read_openclaw_env('TAVILY_API_KEY')
    if not tavily_key:
        return {'ok': False, 'reason': 'TAVILY_API_KEY not configured', 'answer': '', 'sources': []}

    script = HOME / '.agents' / 'skills' / 'tavily-search' / 'scripts' / 'search'
    if not script.exists():
        return {'ok': False, 'reason': 'tavily-search skill script not found', 'answer': '', 'sources': []}

    env = os.environ.copy()
    env['TAVILY_API_KEY'] = tavily_key

    try:
        proc = subprocess.run(
            [str(script), query],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        parsed = parse_tavily_output(proc.stdout)
        return {'ok': True, **parsed, 'raw': proc.stdout}
    except subprocess.CalledProcessError as e:
        return {
            'ok': False,
            'reason': (e.stderr or str(e)).strip(),
            'answer': '',
            'sources': []
        }


def main():
    parser = argparse.ArgumentParser(description='Xiaohongshu multi-agent runner (Python)')
    parser.add_argument('--date', default=today_str())
    parser.add_argument('--topic', default='未命名选题')
    parser.add_argument('--title', default=None)
    parser.add_argument('--mode', default='mvp')
    parser.add_argument('--query', default=None)
    parser.add_argument('--with-search', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    date = args.date
    topic = args.topic
    title = args.title or topic
    mode = args.mode
    with_search = args.with_search or mode == 'search-enhanced'
    search_query = args.query or f'{topic} AI 效率工具 小红书 选题 趋势'

    workflow = read_json(ROOT / 'config' / 'workflow.json')
    models = read_json(ROOT / 'config' / 'models.json')
    search = read_json(ROOT / 'config' / 'search.json')

    run_dir = ROOT / 'runs' / date
    manifest_path = run_dir / 'manifest.json'
    sources_path = run_dir / 'sources.json'

    step_files = [
        ('01-trends.md', '# Run ${date} / Step 01 / Trends\n\n- Topic: ${topic}\n- Mode: ${mode}\n- Agent: trend-radar\n- Model: ${trendModel}\n- Search: ${trendSearch}\n\n## Notes\n\n'),
        ('02-topics.md', '# Run ${date} / Step 02 / Topics\n\n- Topic: ${topic}\n- Agent: topic-planner\n- Model: ${topicModel}\n\n## Candidate Topics\n\n'),
        ('03-draft.md', '# Run ${date} / Step 03 / Draft\n\n- Selected Title: ${title}\n- Agent: copywriter\n- Model: ${copyModel}\n\n## Draft\n\n'),
        ('04-reviewed.md', '# Run ${date} / Step 04 / Reviewed\n\n- Selected Title: ${title}\n- Agent: style-reviewer\n- Model: ${reviewModel}\n\n## Review\n\n'),
        ('05-publish-pack.md', '# Run ${date} / Step 05 / Publish Pack\n\n- Selected Title: ${title}\n- Agent: launch-analyst\n- Model: ${launchModel}\n\n## Publish Checklist\n\n')
    ]

    vars_ = {
        'date': date,
        'topic': topic,
        'mode': mode,
        'title': title,
        'trendModel': models['agents'].get('trend-radar', models['default']),
        'topicModel': models['agents'].get('topic-planner', models['default']),
        'copyModel': models['agents'].get('copywriter', models['default']),
        'reviewModel': models['agents'].get('style-reviewer', models['default']),
        'launchModel': models['agents'].get('launch-analyst', models['default']),
        'trendSearch': ', '.join(search.get('trend-radar', [])) or 'none',
    }

    manifest = {
        'name': workflow['name'],
        'version': workflow['version'],
        'date': date,
        'mode': mode,
        'topic': topic,
        'title': title,
        'runDir': str(run_dir),
        'createdAt': datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        'steps': workflow['steps'],
        'humanCheckpoints': workflow['humanCheckpoints'],
        'models': models['agents'],
        'search': search,
        'searchEnabled': with_search,
        'searchQuery': search_query if with_search else '',
        'files': [name for name, _ in step_files],
    }

    if args.dry_run:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return

    ensure_dir(run_dir)
    write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')

    for name, tpl in step_files:
        write_text(run_dir / name, render(tpl, vars_))

    if with_search:
        result = run_tavily(search_query)
        write_text(sources_path, json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        trends_file = run_dir / '01-trends.md'
        base = trends_file.read_text(encoding='utf-8')
        appended = f'\n## Search Query\n\n{search_query}\n'
        if result.get('ok'):
            appended += f"\n## Tavily Summary\n\n{result.get('answer') or 'No summary returned.'}\n"
            appended += '\n## Sources\n\n'
            if result.get('sources'):
                for s in result['sources']:
                    appended += f"- {s.get('title', '')}\n"
                    if s.get('url'):
                        appended += f"  {s['url']}\n"
            else:
                appended += '- No sources returned\n'
        else:
            appended += f"\n## Search Error\n\n{result.get('reason', 'Unknown error')}\n"
        write_text(trends_file, base + appended)

    print(f'Initialized run: {run_dir}')
    print(f'Topic: {topic}')
    print(f'Mode: {mode}')
    if with_search:
        print(f'Search query: {search_query}')
    print('Files:')
    for name, _ in step_files:
        print(f'- {name}')
    if with_search:
        print('- sources.json')
    print('- manifest.json')


if __name__ == '__main__':
    main()
