# Wall-Street Equity Research Skill｜股票脱水质检 Prompt

一个用于个人投资研究的股票质检 Prompt / Agent Skill。

它把单只股票分析拆成可执行的研究流程：

- 数据源优先级：监管原文 / 公司 IR / 交易所公告优先
- Data Acquisition Workflow：先找财报原文，再取表格，再补行情和估值
- Evidence Ledger：关键数字必须标注日期、来源、口径、可信度
- 10 年回本测试：名义与贴现双口径，EPS 与 FCF/share 双口径
- A 股预抓取脚本：公告链接、行情、三表、分红、FCF、EV/FCF、同业比较、权益法平台识别、中国 10Y 缓存
- 三条投资纪律：持有=买入、机会成本、10 年回本
- 最终四档判决：Buy / Hold-Index / Watchlist / Avoid

> 免责声明：本仓库仅用于个人研究、学习和辅助信息整理，不构成投资建议。所有财务数据、估值和结论都必须回到监管原文、公司公告和可靠数据源复核。

## 文件

- [`SKILL.md`](SKILL.md)：完整 Prompt / Agent Skill 文档
- [`scripts/a_share_prefetch.py`](scripts/a_share_prefetch.py)：A 股预抓取脚本
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
3. 11 个固定分析模块
4. 最终 Buy / Hold-Index / Watchlist / Avoid 判决

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

当前公开版基于 `optimized-v4`。

主要特性：

- 新增 Data Source Priority
- 新增 Data Acquisition Workflow
- 新增 Filing Completeness Check
- 新增关键数字交叉验证
- 强制 Evidence Ledger
- 用 10 年期国债收益率 × 2 替代固定现金收益假设
- 新增 A 股预抓取脚本
- A 股脚本新增 `summary`、`peer_comparison`、权益法平台识别和人工复核提示
- 贴现回本测试升级为四档：10Y×1 / 10Y×2 / 8% / 10%
