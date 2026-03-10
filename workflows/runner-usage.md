# Runner Usage

## 功能
最小调度器当前负责：
- 创建当天 run 目录
- 写入 `manifest.json`
- 生成 01~05 步骤文件骨架
- 自动带入 workflow / model / search 配置
- 在联网模式下自动调用 Tavily 搜索并写入 `01-trends.md` 与 `sources.json`

## 用法
在 `agents/xiaohongshu/` 目录下：

```bash
node bin/run.js --topic "我现在用AI提效，最重要的已经不是提示词了" --mode search-enhanced
```

或：

```bash
bash bin/run.sh --topic "我现在用AI提效，最重要的已经不是提示词了" --mode search-enhanced
```

## 可选参数
- `--topic`：本次主题
- `--title`：本次标题（可选）
- `--date`：日期，格式 `YYYY-MM-DD`
- `--mode`：`mvp` 或 `search-enhanced`
- `--with-search`：强制启用联网搜索
- `--query`：自定义搜索 query
- `--dry-run`：只打印 manifest，不写文件

## 示例

```bash
node bin/run.js \
  --date 2026-03-11 \
  --mode search-enhanced \
  --topic "如果你想少折腾，直接抄我这套AI工作流就行"
```

自定义 query：

```bash
node bin/run.js \
  --date 2026-03-11 \
  --mode search-enhanced \
  --topic "AI效率工具选题"
  --query "latest AI productivity tools news for content creators"
```
