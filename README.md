# 小红书多 Agent 框架

面向：个人IP / AI / 效率工具

目标：
- 用 5 个 Agent 串起小红书内容生产流程
- 支持无网版与联网增强版两种工作模式
- 所有 Prompt、Workflow、模板、运行结果都可追踪、可复用、可迭代

## 目录说明

- `agents/`：每个 Agent 的独立配置与 Prompt
- `config/`：模型、搜索、流程等结构化配置
- `templates/`：选题、草稿、审核、发布模板
- `workflows/`：流程说明文档
- `runs/`：每次实际执行的产物归档

## 当前 6 个 Agent

1. `trend-radar.md`：趋势雷达
2. `topic-planner.md`：选题策划
3. `copywriter.md`：文案脚本
4. `style-reviewer.md`：风格审核
5. `launch-analyst.md`：发布复盘
6. `visual-packager.md`：图文资产与出图任务打包

## 推荐运行方式

### MVP 无网版
- 适合先快速产出内容
- 重点在选题、文案、审核、待发布清单

### 联网增强版
- 趋势雷达优先使用 Tavily + multi-search-engine + web_search
- 适合抓热点、补素材、验证选题

## 最小调度器（Runner）

已内置一个最小可执行 runner：
- `bin/run.js`
- `bin/run.sh`

示例：

```bash
cd agents/xiaohongshu
node bin/run.js --topic "我现在用AI提效，最重要的已经不是提示词了" --mode search-enhanced
```

它会自动：
- 创建 `runs/YYYY-MM-DD/`
- 生成 `manifest.json`
- 生成 `01~05` 步骤文件骨架
- 带入 workflow / model / search 配置
- 在 `search-enhanced` 模式下自动执行 Tavily 搜索并落盘
- 在 Python 版中自动生成 `02-topics.md`
- 在 Python 版中自动生成 `03-draft.md`
- 在 Python 版中自动生成 `04-reviewed.md`
- 在 Python 版中自动生成 `05-publish-pack.md`
- 在 Python 版中自动生成 `06-assets.md`
- `06-assets.md` 当前使用 GPT-5.4 做图文策划，并调用 `bytedance-seed/seedream-4.5` 真实生成图片
- 注意：OpenRouter 实际请求时模型 ID 使用 `bytedance-seed/seedream-4.5`，不带 `openrouter/` 前缀

更多说明见：`workflows/runner-usage.md` 和 `workflows/python-runner-usage.md`

## 建议节奏

- 每周：做 1 次趋势扫描
- 每天：完成 1 个选题到终稿的闭环
- 每周：做 1 次发布复盘
