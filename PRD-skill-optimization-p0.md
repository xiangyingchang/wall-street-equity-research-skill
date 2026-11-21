# P0 输入与执行优化（2026-11-06）
依据：/Users/haoshifasheng/skill-optimization-review-20261106.md 第4节 P0-1/2/3。
目标：消除契约摸索、重复取证和中断重跑；不改变估值、裁决、renderer、verify/lint 。模型路由按用户 2026-11-06 补充范围执行，窄任务可 Terra/high、Luna/max，裁决保留 Sol/medium。
P0-1：生产 Spec 骨架、初始化、汇总静态预检；骨架无公司事实或假设默认值。
P0-2：沿用 research_pack 的 canonical hash、锁与原子写，新增 v3 证据适配器；原 v1 严格契约不放宽。保存原文、定位、日期、期间、单位、核验状态；过期/变更阻断复用。
P0-3：顺序启动器、阶段状态与独立遥测；最小子任务上下文，默认不 fork 历史。完整研究视角保留。
验收：五份既有 Spec 副本、反例、原 CI、本次一份 Sol/medium 负责美光重跑，以及同证据窄任务 Sol/Terra/Luna 对照；质量退化回滚相关改动。不会改旧研报、Notion、远端机器。
