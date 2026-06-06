# Wall-Street Equity Research Skill｜股票脱水质检 Prompt

一个用于个人投资研究的股票质检 Prompt / Agent Skill。

它把单只股票分析拆成可执行的研究流程：

- 数据源优先级：监管原文 / 公司 IR / 交易所公告优先
- Data Acquisition Workflow：先找财报原文，再取表格，再补行情和估值
- Evidence Ledger：关键数字必须标注日期、来源、口径、可信度
- 10 年回本测试：名义与贴现双口径，EPS 与 FCF/share 双口径
- 三条投资纪律：持有=买入、机会成本、10 年回本
- 最终四档判决：Buy / Hold-Index / Watchlist / Avoid

> 免责声明：本仓库仅用于个人研究、学习和辅助信息整理，不构成投资建议。所有财务数据、估值和结论都必须回到监管原文、公司公告和可靠数据源复核。

## 文件

- [`SKILL.md`](SKILL.md)：完整 Prompt / Agent Skill 文档
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

当前公开版基于 `optimized-v3`。

主要特性：

- 新增 Data Source Priority
- 新增 Data Acquisition Workflow
- 新增 Filing Completeness Check
- 新增关键数字交叉验证
- 强制 Evidence Ledger
- 用 10 年期国债收益率 × 2 替代固定现金收益假设
