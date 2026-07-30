# Wall-Street Equity Research Skill｜股票脱水质检 Prompt

一个用于个人投资研究的股票质检 Prompt / Agent Skill。

它把单只股票分析拆成可执行的研究流程：

- 数据源优先级：监管原文 / 公司 IR / 交易所公告优先
- Data Acquisition Workflow：先找财报原文，再取表格，再补行情和估值
- Evidence Ledger：关键数字必须标注日期、来源、口径、可信度
- 10 年回本测试：名义与贴现双口径，EPS 与 FCF/share 双口径
- A 股预抓取脚本：公告链接、行情、三表、分红、FCF、EV/FCF、同业比较、权益法平台识别、中国 10Y 缓存
- 非 A 股 preflight：公司 IR、SEC/HKEX filing、PDF deck、收盘/盘后价格、10Y 收益率和同业估值
- 周期/高 Capex 双估值：峰值利润、新周期中枢、旧周期平准、EV/FCF
- 三条投资纪律：持有=买入、机会成本、10 年回本
- 最终四档判决：Buy / Hold-Index / Watchlist / Avoid
- 单一 Action Matrix：所有条件交易与阈值只在第 9 模块定义

> 免责声明：本仓库仅用于个人研究、学习和辅助信息整理，不构成投资建议。所有财务数据、估值和结论都必须回到监管原文、公司公告和可靠数据源复核。

## 文件

- [`SKILL.md`](SKILL.md)：完整 Prompt / Agent Skill 文档
- [`references/report-contract.md`](references/report-contract.md)：报告输出契约
- [`references/full-methodology.md`](references/full-methodology.md)：9 个固定模块加前置模块区段的方法论
- [`references/data-validation.md`](references/data-validation.md)：数据验证与可执行审计流程
- [`references/researchability.md`](references/researchability.md)：A/B/C 与置信度定义
- [`references/source-map.md`](references/source-map.md)：Obsidian 路径和历史报告定位
- [`scripts/a_share_prefetch.py`](scripts/a_share_prefetch.py)：A 股预抓取脚本
- [`scripts/pdf_text_extract.py`](scripts/pdf_text_extract.py)：财报 PDF / earnings deck 文本抽取
- [`scripts/report_lint.py`](scripts/report_lint.py)：报告交付前的硬约束检查
- [`scripts/financial_rigor.py`](scripts/financial_rigor.py)：Decimal 计算与交叉验证
- [`scripts/report_audit.py`](scripts/report_audit.py)：v4 manifest/results 与 pack-backed v5 派生值审计
- [`scripts/research_pack.py`](scripts/research_pack.py)：可恢复的研究包与估值口径锁
- [`references/research-pack-v1.md`](references/research-pack-v1.md)：`research-pack-v1` 数据契约和命令
- [`examples/input-template.md`](examples/input-template.md)：使用时的输入模板
- [`LICENSE`](LICENSE)：MIT License

## 快速使用

把 [`SKILL.md`](SKILL.md) 的内容交给支持长上下文的 LLM / Agent，然后输入股票信息：

```md
股票代码：0700.HK
交易市场：港股
投资者税务身份：中国大陆个人
计划持有周期：长期 3-10 年
对标机会成本：10 年期国债收益率 × 2 / 中海油 / 神华 / 标普500 / 纳指100
当前状态：未持有
现有仓位或计划投入资金：待定
```

模型应先输出：

1. First-Page Verdict
2. Evidence Ledger
3. 9 个固定分析模块
4. 最终 Buy / Hold-Index / Watchlist / Avoid 判决

完整 Obsidian 报告交付前必须跑：

```bash
python3 scripts/report_audit.py recognize --report "/path/to/report.md"
python3 scripts/report_lint.py "/path/to/report.md"
```

没通过就修报告，不能说“跑完了”。

`scripts/new_report.py` 会在写出模板骨架后自动执行字段识别并在失败时删除无效输出。手工创建或复制模板骨架时，必须立即显式运行 `recognize`。两种路径都必须在填完报告后、运行 `report_audit.py extract` 前再执行一次；`recognize` 不要求数值单元格已经填好。

## 可恢复研究包

跨会话或可能中断的完整研究，建议在生成骨架时同时创建 `research-pack-v1`：

```bash
python3 scripts/new_report.py \
  --ticker META --company Meta --market US \
  --out "/path/to/META.md" --research-pack
```

也可以单独运行 `scripts/research_pack.py init`，随后用 `source-add`、`fact-add`、`derived-add`、`checkpoint`、`valuation-lock` 和 `status` 保存确定性的上游状态。完整命令和 JSON 契约见 [`references/research-pack-v1.md`](references/research-pack-v1.md)。

研究包是持久化恢复检查点，不是 provider/model/token/timing/retry/runtime telemetry，不抓取数据，也不替代报告、lint 或人工审计。

派生记录的输入是引用，不是调用方复制的数据：财务和市场输入使用 `fact_ref`，可组合结果使用无环 `derived_ref`；解析时从不可变 pack 快照取得 value、unit、as-of 和 source IDs。唯一 literal 是 payback 公式的正整数 `years`。TTM sum 要求四个连续财季、70-115 天相邻间隔，且这组中唯一的 `FYyyyy-Q4` 期末年份必须正好等于 `yyyy`；TTM bridge 要求年度 FY 期末年份正好等于声明财年、相邻财年、相同 1-3 季 YTD 长度、350-385 天同比间隔以及兼容 52/53 周财年的桥接日期。公式同时执行维度和十亿单位缩放代数。

包含严格派生记录并完成 `draft_ready` 后，运行 pack-backed Audit v5：

```bash
python3 scripts/report_audit.py extract --report "/path/to/report.md" --pack "/path/to/pack.json" --manifest-out "/path/to/manifest-v5.json"
python3 scripts/report_audit.py verdict --report "/path/to/report.md" --pack "/path/to/pack.json" --manifest "/path/to/manifest-v5.json"
```

v5 不读取 `results.json`，也不抓取网络数据。Extract/verdict 都拒绝 report/pack/manifest symlink 和路径碰撞；严格 JSON 拒绝重复键，公共 snapshot API 也拒绝伪造的 text/bytes、parsed/bytes 或容器类型组合。所有 skill 自带的 research-pack 写入器与 v5 verdict 共用 pack 旁的 advisory lock；verdict 持锁后重新读取并比对快照，再完成重建、复算和提交，因此协作写入器并发时不会丢失更新。该保证只适用于遵守此锁协议的 skill 写入器，无法阻止任意外部程序直接改写文件。成功后 pack 的实际 SHA-256 与 manifest 一致，相同 verdict 重跑仍 PASS 且不改字节。未使用 pack 时，v4 manifest/results 字节、判定逻辑和数值语法保持不变（例如 `$10/share` 仍不是 v4 数值）；v4 同时拒绝破坏性路径碰撞和 symlink 输出，并原子提交两个输出。

## A 股预抓取脚本

对 A 股，建议先运行脚本生成 Evidence Ledger 草稿：

```bash
python3 scripts/a_share_prefetch.py 600900 --peers 600905 600025 600886 600674 600795 601985
```

脚本会抓取并输出 JSON：

- 上交所公告链接：年报、季报、分红、分红回报规划等（沪市）
- 腾讯行情：GBK 解码后的价格、PE、PB、市值、成交额、同业估值
- 东方财富三表：资产负债表、利润表、现金流量表，自动处理 gzip
- 东方财富分红：分红方案、股本、EPS
- 自动派生：TTM EPS、TTM FCF、FCF/share、P/FCF、EV/FCF
- 顶层摘要：`summary` 汇总 quote、rates、TTM、分红、估值和人工复核提示
- 同业比较：`peer_comparison` 输出同业价格、PE、PB、市值、换手率
- 业务模型提示：`business_model_flags` 识别投资收益主导 / 权益法平台，并提示 FCF 降权
- 中国 10Y 国债收益率：来自中债/财政部收益率曲线，本地缓存 30 天
- 10 年回本：名义、10Y×1、10Y×2、8%、10% 压力测试

强制刷新中国 10Y：

```bash
python3 scripts/a_share_prefetch.py 600900 --refresh-china-10y
```

调整缓存天数：

```bash
python3 scripts/a_share_prefetch.py 600900 --china-10y-cache-days 7
```

限制：

- 深市股票目前仍需单独补巨潮公告链接；脚本可抓行情、财务、分红。
- PDF 正文/表格抽取不在脚本内完成；脚本只确认公告链接和结构化数据。
- JSON 不能直接当报告粘贴。应先读 `summary`，再读 `peer_comparison`，最后按需钻取 raw `financials`，并转换成 Evidence Ledger、标注 Tier 1 / Tier 2。
- 如果 `summary.business_model_flags.equity_method_holding_company=true`，合并 FCF 必须降权，重点改看 EPS、分红、投资收益持续性、主要参股资产质量和现金分配机制。

## 非 A 股 preflight

美股、港股和其他非 A 股报告，在写结论前先完成：

- 公司 IR 最新 earnings release；
- earnings deck / prepared remarks PDF；
- SEC 10-K / 10-Q / 8-K / 20-F / 6-K，或 HKEX 年报 / 中报 / 公告；
- filing gap，例如 earnings release 新于正式 10-Q；
- 收盘价、最新 regular-session 价格、盘前/盘后价格分开；
- 对应计价货币 10Y 国债收益率；
- 同业估值和关键口径冲突。

PDF 抽取：

```bash
python3 scripts/pdf_text_extract.py <pdf_or_url>
```

如果 PDF 抽取失败，报告必须写明失败原因；不能用新闻摘要冒充管理层原文。

## 周期股和高 Capex 闸门

以下行业默认必须拆峰值利润和中周期利润：存储、半导体硬件链、能源、煤炭、化工、航运、面板、银行、保险、券商、地产、汽车、航空。

报告必须同时看：

- 峰值 / 当前周期 EPS 与 FCF；
- 新周期中枢 EPS 与 FCF；
- 旧周期平准 EPS 与 FCF；
- EV/FCF。

只靠峰值利润支撑的 Buy，评级默认降为 Watchlist 或 Avoid；追高风险单独标记为高，不得写成第五档评级。

## 核心原则

### 数据优先级

1. Tier 1：监管原文 / 公司 IR / 交易所公告
2. Tier 2：标准化数据商
3. Tier 3：财经媒体 / 网页摘要 / 搜索结果
4. Forbidden：LLM 训练记忆

### 三条投资纪律

1. **持有 = 买入**：每天的持仓都等于用今天现价重新买一次。
2. **机会成本才是真成本**：本金锁在低效资产里错过的复利，比浮亏可怕。
3. **十年回本测试**：未来 10 年累计利润倍数必须能覆盖现在估值。

## 适用场景

适合：

- 单只股票深度质检
- 股票是否值得买 / 持有 / 卖出的辅助判断
- 财报驱动的基本面分析
- 估值安全边际检查
- 中美港股的横向机会成本比较

不适合：

- 高频交易
- 纯技术分析
- 宏观择时
- 不看原始财报的数据速读
- 直接替代专业投顾意见

## 版本

当前公开版基于 `optimized-v7-preflight-cycle-pdf`。

主要特性：

- Data Source Priority / Data Acquisition Workflow / Filing Completeness Check
- 关键数字交叉验证和 Evidence Ledger
- 10 年期国债收益率 × 2 机会成本
- A 股预抓取脚本：`summary`、`peer_comparison`、权益法平台识别、中国 10Y 缓存
- 非 A 股 preflight：IR + filing + PDF + 收盘/盘后价格分离
- PDF 文本抽取脚本
- 报告 lint：三原则、四档贴现、Evidence Ledger、9 个固定模块、source links 等交付前检查
- 报告识别预检：占位符骨架也能验证强制决策字段标签；Action Matrix lint 阻止重复条件交易
- 周期/高 Capex 双估值闸门
- 四档贴现回本测试：10Y×1 / 10Y×2 / 8% / 10%
