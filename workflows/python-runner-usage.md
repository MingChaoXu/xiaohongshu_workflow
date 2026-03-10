# Python Runner Usage

## 环境
优先支持 conda 环境运行。
当前机器上已检测到的环境包括：`base`、`pandaai`、`vllm`、`vnpy`。

默认启动脚本使用 `base`。如果你之后创建了 `py311`，只需设置：

```bash
export XHS_PY_ENV=py311
```

## 用法

### 直接调用 Python
```bash
$HOME/miniconda3/bin/conda run -n base python bin/run.py --topic "AI效率工具个人IP选题" --mode search-enhanced
```

### 使用启动脚本
```bash
bash bin/run-py311.sh --topic "AI效率工具个人IP选题" --mode search-enhanced
```

## 参数
- `--topic`
- `--title`
- `--date`
- `--mode`
- `--with-search`
- `--query`
- `--dry-run`

## 说明
Python 版已超过当前 Node runner，当前支持：
- 初始化 run 目录
- 生成 01~05 文件
- 生成 manifest.json
- 在联网模式下自动调用 Tavily 搜索
- 写入 sources.json 和 01-trends.md
- 自动生成 02-topics.md（候选选题 + 推荐选题）
- 自动生成 03-draft.md（标题备选 + 封面文案 + 正文初稿 + 互动引导 + 标签）
- 自动生成 04-reviewed.md（审核结论 + 问题 + 修改建议 + 终稿）
- 自动生成 05-publish-pack.md（发布时间 + 检查项 + 数据模板 + 复盘建议）
- 自动生成 06-assets.md（6页图文脚本 + 每页配图提示词）
- 视觉策划模型配置为 `aicodemirror-gpt/gpt-5.4`
- 出图模型配置切换为 `openrouter/bytedance-seed/seedream-4.5`
- 当前仍需继续验证该模型在 OpenRouter 上的真实图片输出接口方式
