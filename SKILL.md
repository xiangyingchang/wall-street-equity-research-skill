---
name: wall-street-equity-research
description: 用 optimized-v3 的 11 模块华尔街式股票脱水质检框架，基于监管原文和 Evidence Ledger，完成单只股票的财务、护城河、估值、10 年回本、税后收益、机会成本、仓位与最终 Buy/Hold-Index/Watchlist/Avoid 判决。用户说“华尔街分析”“脱水质检”“10 年回本”“跑一下 [股票]”“该不该买”或要求比较单只股票时使用；默认采用 V3-Fast 的轻量确定性校验，不运行完整 v3.1 Compiler。
---

# Wall Street Equity Research — optimized-v3

执行一份证据约束、数学可复现、读者优先的单股票研究备忘录。V3 是默认公开报告合同；V3-Fast 只保留必要的确定性校验，不把 Compiler、Bundle、Research Graph 或审计元数据写进正文。

## 版本与执行模式

- 当前基线：`optimized-v3`，11 个固定模块，三条贴现 scale：10Y 国债 ×2、8%、10%。可额外展示 10Y ×1，但不能替代 V3 三档。
- 默认模式：`V3-Fast`。一次取数、一个 Evidence Ledger、一次 Reader 写作、一次本地 math/lint 校验。
- 深度模式：`V3-Deep`。仅在高 CapEx、关键数据冲突、重大财报变化或用户明确要求审计时增加定向复核；不要默认生成 v3.1 的 Spec/Bundle/Graph/Audit 四件套。
- GitHub 中保留了 v3.1 Compiler/Research Graph 的兼容文件；本机的完整 v3.1 回滚快照在仓库外维护，不属于报告运行时。

## 核心纪律

1. 持有 = 买入：用今天的价格重新判断，不用沉没成本替代判断。
2. 机会成本才是真成本：与对应计价货币的 10Y 国债 ×2、指数、同行和高确定性替代资产比较。
3. 十年回本测试：EPS 与 FCF/share 都要测试名义和贴现增长是否物理可达。
4. 数据诚实：当前价格、财务、估值、公告和收益率不能凭模型记忆填写；无法确认就降置信度并列入人工复核。
5. 读者优先：先给结论，再讲业务机制、财务质量、估值和行动；审计细节服务于判断，不抢正文的视觉权重。

## 输入与默认值

记录 ticker、市场、投资者税务身份、计划持有周期、机会成本、当前状态、现有仓位或计划金额。缺失时只询问一次；若用户允许默认值，在报告中明确写出：

> 默认输入：税务身份=中国大陆个人；持有周期=长期 3-10 年；机会成本=对应计价货币 10Y 国债 ×2 + 高质量替代资产；持仓未核验。

## V3-Fast 工作流

1. 读取 `references/report-contract-v3.md`、`references/source-map.md` 和 `references/full-methodology-v3.md`。
2. 对美股、港股和其他非 A 股，先收集公司 IR 最新业绩、监管 filing、当前收盘/最新交易价、对应 10Y 收益率、同行估值和 filing gap。优先 SEC、公司 IR、HKEX、交易所公告；二手数据只作交叉验证。
3. 先建立 Evidence Ledger，再写结论。每个关键数字记录日期、来源层级、URL/定位、单位、期间/口径和置信度。
4. 按 11 个模块写 Reader：Overview、Financial Autopsy、Moat、Valuation、Liquidity/Cap Filter、Risk Ranking、Growth Potential、Tax Drag/Net Yield、Institutional/Opportunity Cost、Position/Exit、Final Verdict。
5. 对 TTM、Forward、Normalized EPS 和 FCF/share 分别标注口径。高 CapEx 公司同时检查 CapEx 制度、OCF 运行率、折旧、未投产资产和 EV/FCF；不要把 GAAP 非经营投资收益资本化为经营能力。
6. 用 `scripts/valuation_math.py` 计算 payback、目标回报价格、IRR、Price Discipline 和多年度税后股息累计。报告记录完整 input vector 与 dividend treatment，禁止手填无法复现的价格或股息总额。
7. 运行 `python3 scripts/report_lint.py --profile v3 <report.md>`。失败必须修正或明确降级，不得把“已生成”当作“已完成”。
8. 保存到 Obsidian `股票/<公司名>/`，新文件不覆盖旧报告；需要重跑时加入“与之前的差异”区段，但不破坏 V3 顶层 11 模块顺序。

## 轻量后台校验

只校验同一份 Evidence Ledger 和输入向量，不另起一套研究：

- 确定性 payback、target-price、IRR 和 dividend-total；
- EPS/FCF 每股分母披露：市值使用 point-in-time common shares，EPS 使用 diluted weighted-average shares，FCF/share 使用匹配期间的稀释分母或明确 proxy；
- 现金、有价证券、非上市证券、受限证券、债务和租赁负债分类；
- 来源、日期、单位、期间、TTM bridge、Reported/Adjusted/Normalized 和 CapEx regime 检查；
- V3 11 模块、三档 discount table、税后股息处理、三条纪律和 Sources 检查。

不要默认运行 Research Graph、Spec/Bundle 编译、重复 provider 抓取、内部 ID 生成或完整 Audit Appendix。只有 V3-Deep 且确有必要时才启用这些重型步骤。

## 关键口径硬规则

### 股息

名义多年度税后股息使用：

```text
sum(dividend_0 × (1 + dividend_growth)^t × (1 - withholding_rate))
```

运行：

```bash
python3 scripts/valuation_math.py dividend-total \
  --annual-dividend <value> --growth-rate <decimal> \
  --years <integer> --withholding-rate <decimal>
```

明确区分“名义股息累计”和“再投资股息收益率”。

### 股数

在 Evidence Ledger 和估值段同时披露：市值股数、EPS 股数、FCF/share 股数及其日期/期间。不同分母可以共存，但不能无标签地混用。

### 证券和净现金

将现金、current/non-current marketable securities、non-marketable securities、restricted securities、债务和 lease liabilities 分列；只有可合理变现且定义一致时才使用“净现金”。

## 评级闸门

- `Buy`：现价重新买入、机会成本、10 年回本三关同时通过，且关键数据不是未解决的低置信度。
- `Hold-Index`：已有资产可继续观察，但不代表新资金可买；必须说明新资金边界。
- `Watchlist`：公司质量或数据值得跟踪，但价格、现金回报或证据不足以执行。
- `Avoid`：论文破坏、估值无法解释或风险回报明显不对称。

## 必须阅读的资源

- `references/report-contract-v3.md`：每份完整报告的 V3 输出合同。
- `references/full-methodology-v3.md`：11 模块研究方法和计算口径。
- `references/source-map.md`：Obsidian 权威路径和历史报告定位。
- `scripts/valuation_math.py`：确定性估值、IRR、Price Discipline 与股息计算。
- `scripts/report_lint.py`：使用 `--profile v3` 做 V3 交付检查。
- `templates/full-report-v3.md`：用 `scripts/new_report.py --profile v3` 生成骨架。

## 安全边界

这套 10 年回本模型是压力测试，不是完整 DCF；它天然偏保守，可能误伤超级复利公司。报告必须把事实、解释、假设和行动分开，并提醒用户回到监管原文复核。不要把未核验的 Ledger 持仓、税务身份或当前价格写成事实。
