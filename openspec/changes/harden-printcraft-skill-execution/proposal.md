## Why

当前六项技能已经提供固定运行时安装、工具查询和单会话计划，但职责重叠、嵌套超时状态丢失、输出缺少可执行验收，无法仅凭现有 22 项本地测试证明 PDF 任务正确。借鉴 Dreamina 的职责分离、状态持久化和证据绑定，补齐可验证的执行交付链路。

## What Changes

- 明确六项技能职责，增加按需参考、成功/失败/边界案例和工具覆盖映射，保留独立安装能力。
- 区分只读诊断、授权安装、短任务与 MCP 长驻服务，绑定真实固定发行版的能力。
- 引入版本化执行结果、稳定任务身份、互斥和对账，修复 600 秒内层超时被外层误判的问题。
- 增加输出清单、保存重开、PDF 任务断言及绑定文件摘要的验收记录。
- 增加敏感数据处理、故障注入、原生兼容及高级能力分级门禁。
- **BREAKING（实施时）**：旧无版本回执只读保留，不能自动恢复执行；未知结果不重放，新增结构化结果不得混入原生 stdout。旧入口通过兼容适配保留，具体退出与状态迁移见 design.md。

## Capabilities

### New Capabilities
- `skill-routing`: 六技能职责、渐进披露、自包含分发和命令归属。
- `runtime-contract`: 只读诊断、固定制品身份、实时能力及进程生命周期。
- `execution-lifecycle`: 版本化回执、单会话、任务身份、对账、授权范围和敏感数据。
- `pdf-delivery-verification`: 输出身份、保存重开、任务断言和定向修订。
- `acceptance-evidence`: 分层测试、当前证据绑定、高级能力与交接准入。

### Modified Capabilities
无。此前没有正式 OpenSpec 主规格；本变更以 ADDED 建立目标行为，包含需要保留的已有契约，不声称所有条目都是新增代码。

## Impact

主要涉及 skills/*/SKILL.md、其 scripts/、后续 references/examples、tests/、包校验与同步工具。PrintCraft 名称与计划 domain 保留；固定运行时仍为 printcraft-cli 0.2.1，未来 PdfCraft 制品须单独验证，不能把 research/printcraft 的新接口视为已发布能力。

插件消费方：full-aigc-plugins-repositories/printcraft-plugin 的 `harden-printcraft-plugin-delivery`。本项目拥有执行和验收契约；插件只消费这些契约，不复制执行实现。Dreamina 仅作为模式参考，不复制积分报价或远端 submitId 语义。

本次交付仅为规格和未执行任务；不授权自动安装、Git 初始化、发布或任何原生 PDF 写入。
