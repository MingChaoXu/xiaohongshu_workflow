# Search-Enhanced Workflow

## 目标
在 MVP 基础上引入联网增强搜索，提升趋势发现、选题验证、素材准确度。

## 搜索层分工
1. Tavily：快速获取趋势摘要与当前热点
2. Multi Search Engine：跨引擎验证、中文生态补充、定向站点搜索
3. web_search / web_fetch：补充信息与读取页面正文
4. browser：必要时查看具体页面和产品信息

## 步骤
1. Trend Radar 先用 Tavily 扫描 AI / 效率工具近期变化
2. 用 multi-search-engine + web_fetch 验证中文语境下的内容机会
3. Topic Planner 将趋势转成 5 个选题并排序
4. Copywriter 结合最新资料写初稿
5. Style Reviewer 去 AI 味并输出终稿
6. Launch Analyst 整理待发布清单
