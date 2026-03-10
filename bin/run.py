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


def infer_signals(topic: str, search_result: dict):
    answer = (search_result or {}).get('answer', '')
    sources = (search_result or {}).get('sources', [])
    titles = ' | '.join([s.get('title', '') for s in sources[:5]])
    blob = f'{topic} {answer} {titles}'.lower()

    signals = []
    if any(k in blob for k in ['creator', 'content', 'social media', 'solopreneur']):
        signals.append('创作者/内容生产场景上升')
    if any(k in blob for k in ['productivity', 'workflow', 'streamline', 'efficiency']):
        signals.append('用户更关心工作流和提效闭环')
    if any(k in blob for k in ['tools', 'best', 'essential']):
        signals.append('用户正在筛选真正值得留下的工具')
    if any(k in blob for k in ['new', 'latest', 'release', '2026', '2025']):
        signals.append('新工具和新版本持续刺激选题更新')
    if not signals:
        signals = ['AI/效率工具仍然适合做个人经验型内容', '用户更愿意收藏可复制的提效方案']
    return signals[:4]


def generate_topic_candidates(topic: str, search_result: dict):
    signals = infer_signals(topic, search_result)
    summary = (search_result or {}).get('answer', '')

    base_candidates = [
        {
            'title': '我现在用 AI 提效，最重要的已经不是提示词了',
            'audience': '已经尝试过 AI，但效果不稳定的人',
            'click_reason': '有观点反差，容易点开',
            'save_reason': '适合收藏后对照自己的工作流',
            'structure': '问题感受 → 核心观点 → 3 个接入场景 → 总结',
            'priority': '高',
        },
        {
            'title': '我试了一圈 AI 工具，最后真正留下来的只有这 3 类',
            'audience': '工具焦虑、选择困难的用户',
            'click_reason': '“留下来”比“推荐更多”更有筛选价值',
            'save_reason': '方便后续选工具时回看',
            'structure': '为什么开始筛 → 留下的 3 类 → 分别适合谁 → 建议',
            'priority': '高',
        },
        {
            'title': '如果你想少折腾，直接抄我这套 AI 工作流就行',
            'audience': '想要低门槛提效方案的人',
            'click_reason': '有明确获得感和可复制感',
            'save_reason': '适合直接照抄执行',
            'structure': '适合谁 → 工作流步骤 → 每步用什么工具 → 注意点',
            'priority': '高',
        },
        {
            'title': '很多人用 AI 没效果，不是不会提问，而是卡在这里',
            'audience': '用过 AI 但觉得没想象中好用的人',
            'click_reason': '问题导向，容易引发共鸣',
            'save_reason': '适合做避坑提醒',
            'structure': '低效表现 → 根因分析 → 替代做法 → 结论',
            'priority': '中高',
        },
        {
            'title': '适合内容创作者留下来的 AI 工具，不一定是最强的那个',
            'audience': '内容创作者、个人IP经营者',
            'click_reason': '贴近身份场景，容易精准吸引',
            'save_reason': '后续选型和搭配都有复用价值',
            'structure': '误区 → 选择标准 → 推荐类别 → 个人建议',
            'priority': '中高',
        },
    ]

    preferred = 0
    blob = f"{topic} {summary}".lower()
    if 'creator' in blob or 'content' in blob:
        preferred = 4
    elif 'workflow' in blob or 'productivity' in blob:
        preferred = 2

    return signals, base_candidates, preferred


def format_topics_markdown(topic: str, model_name: str, signals: list, candidates: list, recommended_index: int):
    lines = []
    lines.append('# Step 02 / Topics\n')
    lines.append(f'- Topic: {topic}')
    lines.append('- Agent: topic-planner')
    lines.append(f'- Model: {model_name}\n')
    lines.append('## Signals')
    for s in signals:
        lines.append(f'- {s}')
    lines.append('\n## Candidate Topics\n')

    for i, c in enumerate(candidates, start=1):
        lines.append(f'### 题 {i}')
        lines.append(c['title'])
        lines.append(f"- 核心受众：{c['audience']}")
        lines.append(f"- 点击理由：{c['click_reason']}")
        lines.append(f"- 收藏理由：{c['save_reason']}")
        lines.append(f"- 内容结构：{c['structure']}")
        lines.append(f"- 优先级：{c['priority']}\n")

    rec = candidates[recommended_index]
    lines.append('## Recommended Topic\n')
    lines.append(rec['title'])
    lines.append(f"- 推荐原因：{rec['click_reason']}；同时适合当前个人IP方向。")
    return '\n'.join(lines) + '\n'


def create_title_variants(base_title: str):
    variants = [
        base_title,
        f'我后来才发现：{base_title}',
        f'如果你也在折腾 AI，建议先看这篇：{base_title}',
        f'{base_title}，这可能是我最近最认同的一点',
        f'很多人忽略了一点：{base_title}',
    ]
    seen = []
    for v in variants:
        if v not in seen:
            seen.append(v)
    return seen[:5]


def choose_cover_line(base_title: str):
    if '不是提示词' in base_title:
        return 'AI提效最重要的\n已经不是提示词了'
    if '工作流' in base_title:
        return '少折腾一点\n直接抄这套AI工作流'
    if '留下来' in base_title:
        return '试了一圈后\n我只留下这几类工具'
    return base_title.replace('，', '\n', 1)


def generate_draft(topic: str, selected_topic: dict, search_result: dict):
    title = selected_topic['title']
    titles = create_title_variants(title)
    cover = choose_cover_line(title)
    summary = (search_result or {}).get('answer', '')
    summary_line = summary if summary else '最近我越来越明显地感觉到，大家对 AI 的期待已经不只是“会不会写提示词”，而是它到底能不能真的帮上忙。'

    body = f"""最近我有一个很明显的感受：

{summary_line}

但真正让我改变看法的，不是又出了多少新工具，
而是我开始意识到一件更现实的事：
**{title}**

以前我也会花很多时间看新工具、试新功能、研究各种玩法。
但用到后面我发现，真正能长期留下来的，不一定是最强的那个，
而是那个你愿意反复打开、能自然接进自己日常工作里的那个。

对我来说，现在判断一个 AI / 效率工具值不值得留下，基本会看这几件事：

1. 上手是不是太重
2. 能不能直接接进我现在的工作流
3. 它到底是在“看起来很厉害”，还是能长期帮我省事

很多人一开始用 AI，会很容易掉进一个误区：
总想找最强的那个、最新的那个、功能最多的那个。
但真实使用一段时间后你会发现，
**适合长期使用的工具，往往不是参数最夸张的，而是最顺手的。**

尤其如果你本身在做内容、做个人IP、或者本来就有很多重复性工作，
你真正需要的不是一堆新名字，
而是 2～3 个你真的会持续用下去的工具或流程。

我现在更在意的是：
- 它能不能让我更快开始
- 它能不能帮我整理混乱信息
- 它能不能减少重复劳动

如果一款工具做不到这几点，
哪怕它再火、再多人推荐，我最后大概率也不会留下。

所以如果你最近也在各种 AI 工具之间来回试，
我的建议反而是：**先别急着追新。**

先想清楚你每天最常发生的几个场景，
再去找真正适合自己的那 2～3 个工具。 
你会比盲目堆工具，更快感受到提效这件事真的发生了。
"""

    interaction = '你现在长期留下来的 AI 工具，或者最常用的 AI 场景是什么？'
    tags = ['#AI工具', '#效率工具', '#AI提效', '#AI工作流', '#个人IP', '#内容创作', '#生产力工具', '#小红书运营']

    return {
        'selected_title': title,
        'title_variants': titles,
        'cover': cover,
        'body': body.strip(),
        'interaction': interaction,
        'tags': tags,
    }


def format_draft_markdown(model_name: str, draft: dict):
    lines = []
    lines.append('# Step 03 / Draft\n')
    lines.append(f"- Selected Title: {draft['selected_title']}")
    lines.append('- Agent: copywriter')
    lines.append(f'- Model: {model_name}\n')
    lines.append('## Title Variants')
    for i, t in enumerate(draft['title_variants'], start=1):
        lines.append(f'{i}. {t}')
    lines.append('\n## Cover Copy\n')
    lines.append(draft['cover'])
    lines.append('\n## Body Draft\n')
    lines.append(draft['body'])
    lines.append('\n## Interaction Prompt\n')
    lines.append(draft['interaction'])
    lines.append('\n## Tags\n')
    lines.append(' '.join(draft['tags']))
    return '\n'.join(lines) + '\n'


def review_draft(draft: dict):
    body = draft['body']
    issues = []
    suggestions = []

    replacements = {
        '参数最夸张的': '功能最猛的',
        '看起来很厉害': '看起来很强',
        '我有一个很明显的感受': '我越来越明显地感觉到',
    }

    reviewed_body = body
    for old, new in replacements.items():
        if old in reviewed_body:
            reviewed_body = reviewed_body.replace(old, new)
            issues.append(f'存在偏书面或略硬的表达：{old}')
            suggestions.append(f'改为更自然的表达：{new}')

    if 'Adobe Express' in reviewed_body or 'Jasper' in reviewed_body or 'Microsoft 365 Copilot' in reviewed_body:
        issues.append('开头直接堆具体工具名，会让内容有一点资讯感')
        suggestions.append('开头更适合先说个人感受，再带出工具筛选逻辑')
        reviewed_body = reviewed_body.replace(
            '最近我有一个很明显的感受：\n\nAdobe Express, Descript, Jasper, and Microsoft 365 Copilot are top AI productivity tools for creators and personal brands, enhancing creativity and efficiency.\n\n但真正让我改变看法的，',
            '最近我越来越明显地感觉到，大家对 AI 的期待已经不只是“新不新”，而是它到底能不能真的帮上忙。\n\n但真正让我改变看法的，'
        )

    if 'AI tools like' in reviewed_body or 'Essential AI tools for creators include' in reviewed_body:
        issues.append('英文摘要直接进入正文，会削弱小红书口吻')
        suggestions.append('将英文工具摘要改写成中文感受型开头')
        reviewed_body = re.sub(
            r'最近我越来越明显地感觉到：\n\n.*?\n\n但真正让我改变看法的，',
            '最近我越来越明显地感觉到，大家对 AI 的期待已经不只是“新不新”，而是它到底能不能真的帮上忙。\n\n但真正让我改变看法的，',
            reviewed_body,
            flags=re.S,
        )

    if not issues:
        issues = ['整体方向正确，但可以进一步减少说明书感']
        suggestions = ['保留核心观点，增加更自然的人话表达']

    reviewed_title = draft['title_variants'][0]
    return {
        'selected_title': reviewed_title,
        'conclusion': '适合发布，建议采用润色后的版本',
        'issues': issues,
        'suggestions': suggestions,
        'final_body': reviewed_body.strip(),
        'cover': draft['cover'],
        'interaction': draft['interaction'],
        'tags': draft['tags'],
    }


def format_review_markdown(model_name: str, review: dict):
    lines = []
    lines.append('# Step 04 / Reviewed\n')
    lines.append(f"- Selected Title: {review['selected_title']}")
    lines.append('- Agent: style-reviewer')
    lines.append(f'- Model: {model_name}\n')
    lines.append('## Review Conclusion\n')
    lines.append(review['conclusion'])
    lines.append('\n## Main Issues\n')
    for item in review['issues']:
        lines.append(f'- {item}')
    lines.append('\n## Suggestions\n')
    for item in review['suggestions']:
        lines.append(f'- {item}')
    lines.append('\n## Final Cover Copy\n')
    lines.append(review['cover'])
    lines.append('\n## Final Body\n')
    lines.append(review['final_body'])
    lines.append('\n## Interaction Prompt\n')
    lines.append(review['interaction'])
    lines.append('\n## Tags\n')
    lines.append(' '.join(review['tags']))
    return '\n'.join(lines) + '\n'


def generate_publish_pack(review: dict):
    title = review['selected_title']
    return {
        'title': title,
        'cover': review['cover'],
        'body': review['final_body'],
        'tags': review['tags'],
        'publish_time': '工作日晚 20:00 左右',
        'checklist': [
            '封面文案控制在 2~3 行内，确保一眼能看懂观点',
            '首段不要太长，尽量在前 3 句里讲清楚核心观点',
            '全文避免堆太多工具名，先讲选择逻辑再讲工具',
            '标签控制在 6~8 个，避免过度堆砌',
            '发布后尽快补一条首评，承接下一篇内容',
        ],
        'metrics_template': [
            '发布时间：',
            '曝光：',
            '点赞：',
            '收藏：',
            '评论：',
            '涨粉：',
            '评论区高频问题：',
            '下次是否继续做同类题：',
        ],
        'retrospective': [
            '如果收藏高于点赞，说明这类内容更偏工具型/决策型价值',
            '如果评论多，优先继续做“我留下了哪些工具/为什么留下”系列',
            '如果点击一般，下一次可加强标题的反差感或问题感',
        ],
    }


def format_publish_markdown(model_name: str, publish_pack: dict):
    lines = []
    lines.append('# Step 05 / Publish Pack\n')
    lines.append(f"- Selected Title: {publish_pack['title']}")
    lines.append('- Agent: launch-analyst')
    lines.append(f'- Model: {model_name}\n')
    lines.append('## Final Title\n')
    lines.append(publish_pack['title'])
    lines.append('\n## Final Cover Copy\n')
    lines.append(publish_pack['cover'])
    lines.append('\n## Final Body\n')
    lines.append(publish_pack['body'])
    lines.append('\n## Tags\n')
    lines.append(' '.join(publish_pack['tags']))
    lines.append('\n## Suggested Publish Time\n')
    lines.append(publish_pack['publish_time'])
    lines.append('\n## Pre-Publish Checklist\n')
    for item in publish_pack['checklist']:
        lines.append(f'- {item}')
    lines.append('\n## Metrics Template\n')
    for item in publish_pack['metrics_template']:
        lines.append(f'- {item}')
    lines.append('\n## Retrospective Suggestions\n')
    for item in publish_pack['retrospective']:
        lines.append(f'- {item}')
    return '\n'.join(lines) + '\n'


def generate_assets_pack(review: dict):
    title = review['selected_title']
    cover = review['cover']
    pages = [
        {
            'page': 1,
            'title': '封面',
            'copy': cover,
            'visual': '极简封面，大字观点，白底或浅灰底，黑字 + 蓝色点缀',
            'prompt': '小红书封面，4:5比例，极简风，白色和浅灰背景，黑色粗体中文标题，少量蓝色高亮，现代感，适合AI效率工具个人IP账号',
        },
        {
            'page': 2,
            'title': '问题提出',
            'copy': '很多人用 AI 没效果，不一定是因为不会用，而是因为一直在追新，却没有形成自己的使用标准。',
            'visual': '中间大字排版，弱背景，突出问题感',
            'prompt': '小红书图文内页，4:5比例，极简信息卡片风，白灰底，黑色中文排版，强调问题感，现代知识博主视觉',
        },
        {
            'page': 3,
            'title': '核心观点',
            'copy': '真正值得留下来的工具，不一定最强，但一定最顺手、最容易接进日常工作。',
            'visual': '观点卡片，左侧关键词，右侧一句核心判断',
            'prompt': '小红书知识分享卡片，4:5比例，简洁现代排版，白底黑字，蓝色强调，适合效率工具与AI主题',
        },
        {
            'page': 4,
            'title': '筛选标准',
            'copy': '我现在筛 AI / 效率工具，主要看 3 点：上手成本、接入工作流能力、是否真的长期省事。',
            'visual': '三栏信息卡片，三个标准分块展示',
            'prompt': '小红书三栏信息图，4:5比例，白色背景，简洁图标，展示三个筛选标准，适合个人IP干货分享',
        },
        {
            'page': 5,
            'title': '实用建议',
            'copy': '先别急着找最强工具，先找 2～3 个你真的会长期打开的工具。',
            'visual': '建议型卡片，留白更多，句子简洁有力',
            'prompt': '小红书建议型排版，4:5比例，留白感强，白灰背景，黑色文字，强调“少而精”的工具选择理念',
        },
        {
            'page': 6,
            'title': '互动收尾',
            'copy': review['interaction'],
            'visual': '结尾总结页，带互动提问感',
            'prompt': '小红书结尾互动页，4:5比例，极简总结卡片风，白底黑字，轻科技感，适合AI效率主题内容收尾',
        },
    ]
    return {'title': title, 'pages': pages}


def format_assets_markdown(model_name: str, assets: dict):
    lines = []
    lines.append('# Step 06 / Assets\n')
    lines.append(f"- Selected Title: {assets['title']}")
    lines.append('- Agent: visual-packager')
    lines.append(f'- Model: {model_name}\n')
    lines.append('## 6-Page Script\n')
    for page in assets['pages']:
        lines.append(f"### 第 {page['page']} 页｜{page['title']}")
        lines.append(f"- 文案：{page['copy']}")
        lines.append(f"- 视觉建议：{page['visual']}")
        lines.append(f"- 配图提示词：{page['prompt']}\n")
    return '\n'.join(lines) + '\n'


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
        ('05-publish-pack.md', '# Run ${date} / Step 05 / Publish Pack\n\n- Selected Title: ${title}\n- Agent: launch-analyst\n- Model: ${launchModel}\n\n## Publish Checklist\n\n'),
        ('06-assets.md', '# Run ${date} / Step 06 / Assets\n\n- Selected Title: ${title}\n- Agent: visual-packager\n\n## Assets\n\n')
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
        'steps': workflow['steps'] + ['visual-packager'],
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

    search_result = {}
    if with_search:
        result = run_tavily(search_query)
        search_result = result
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
            signals, candidates, recommended_index = generate_topic_candidates(topic, result)
        else:
            appended += f"\n## Search Error\n\n{result.get('reason', 'Unknown error')}\n"
            signals, candidates, recommended_index = generate_topic_candidates(topic, {})
        write_text(trends_file, base + appended)
    else:
        signals, candidates, recommended_index = generate_topic_candidates(topic, {})

    write_text(run_dir / '02-topics.md', format_topics_markdown(topic, vars_['topicModel'], signals, candidates, recommended_index))

    selected_topic = candidates[recommended_index]
    draft_result = generate_draft(topic, selected_topic, search_result)
    write_text(run_dir / '03-draft.md', format_draft_markdown(vars_['copyModel'], draft_result))

    review_result = review_draft(draft_result)
    write_text(run_dir / '04-reviewed.md', format_review_markdown(vars_['reviewModel'], review_result))

    publish_pack = generate_publish_pack(review_result)
    write_text(run_dir / '05-publish-pack.md', format_publish_markdown(vars_['launchModel'], publish_pack))

    assets_pack = generate_assets_pack(review_result)
    write_text(run_dir / '06-assets.md', format_assets_markdown(vars_['launchModel'], assets_pack))

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
