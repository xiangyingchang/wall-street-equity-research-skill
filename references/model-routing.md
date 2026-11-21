# 模型分工与验收边界

依据：2026-11-06 复盘第4节 P1-2，经用户补充纳入本次 P0。档位固定为 Terra/high、Luna/max、Sol/medium；不是复盘中 low 档的直接迁移，也不推定订阅额度或 token 一定减少。

- Terra/high：已定位原文的取数、字段提取、单位/期间整理，以及仅凭已接受 Facts 写事实窄章节。来源冲突、四季缺失、ADR/FX、GAAP 与 adjusted 混淆、现金归一化交 Sol。
- Luna/max：窄字段/路径映射、格式和单条机器错误解释。不得补事实、决定新动作、改估值假设。缺一手来源交 Sol。
- Sol/medium：来源取舍、商业机制、财务判断、最强反方、风险、归一化、情景、综合和最终裁决；全文 Reader 验收。
- Python/shell：build、完整 verify、独立 lint、结构化完成 JSON；不为执行程序另开模型。

## 实际调用

`python3 scripts/run_model_task.py --profile terra --task extract --input /run/extract-prompt.txt --out /run/terra-candidate`

允许 task：extract、section、format、error、judgment。judgment 拒绝低档。入口固定实际模型和 effort，新会话、禁用网页、只读、不继承用户配置或会话；输入必须包含所需任务/契约/摘录，不能让低档自行搜全报告。不要粘全 Spec/Audit、完整历史或其他公司的上下文。抓取原文优先使用 shell/API，低档只整理已给内容。

输出目录必须新建；低档输出为 candidate.md，Sol 为 output.md；日志和 run-metrics.jsonl 独立于证据包。此脚本不自动提升候选为已接受事实，不自动改 Spec，不默认接受 candidate。

## 同输入门槛

同一 prompt hash 跑 Sol 基线与拟降档模型，逐字段对照原文和预先确定的正确值。必须检查日期/单位/季度、GAAP 与 adjusted、forecast 与 actual、缺失值不补造、冲突不擅自消解。事实窄章节逐句检查来源对应、口径限制、不新增裁决；错误解释检查根因、正确修复位置及升级条件。原始输出、失败和补错成本全部保留，不挑最好的一次冒充稳定性。

只有负责人确认无新增关键错误且相应类型通过后才合并候选，写明输入/输出 hash、核验项、接受者和适用边界；质量差则保留 Sol 并撤销该任务类型降档。完整 verify/lint 继续执行，它们不能代替语义验收。

本次单例仅验证美光给定摘录及两个窄错误形状。ADR/FX、现金流缺失、reported/adjusted 冲突、跨公司稳定性仍需覆盖；没有相应验收的类型继续 Sol。模型降档的预计费用区间引用复盘：Terra 整套约15%—25%、Luna 局部约5%—10%，二者重叠，且不是本次实测或 Codex 额度承诺。
