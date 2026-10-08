> 当前实现/验收状态以 [2026-10-08 报告](verification/implementation-2026-10-08.md) 和 project-status.json 为准；下文保留早期架构/候选说明。

# 本地交付架构

独立技能项目是源码来源，每项技能携带固定CLI安装器、公开argv入口、命令目录网关及运行时锁。插件保存逐文件摘要的本地快照；来源未发布，不能登记为可安装市场发行。

PrintCraft使用原生JSON Schema；LightCraft、DesignCraft保留参数说明文本。计划在一个原生进程中执行；超时保留未知状态，不自动重放。零退出仍需检查工程、输出、保存重开和创作质量。安装、宿主发现、模型选用及最终交付分别验收。

OpenSpec优化规范已建立；实现及原生安装验收仍待完成。尚未创建Git仓库或远端发行。已有五套仍使用原OpenSpec；三领域的ArtCraft公共协议映射、依赖交接、返工和移动交付仍未接入。


安装锁现在绑定发行标签、归档名、二进制身份与版本；不一致时在创建运行时目录前拒绝。当前所有三领域真实固定发行仍为0.2.1。上游产品源码已改名PdfCraft，技能名和计划domain继续保留printcraft；安装器分别支持printcraft-cli与pdfcraft-cli，不移动旧运行时，当前发行锁保持printcraft-cli 0.2.1。

## 优化规格与任务

已建立 OpenSpec 变更 [harden-printcraft-skill-execution](../openspec/changes/harden-printcraft-skill-execution/proposal.md)，见[设计](../openspec/changes/harden-printcraft-skill-execution/design.md)与[任务](../openspec/changes/harden-printcraft-skill-execution/tasks.md)。当前仅完成规格编写；实现、原生、宿主及发布门禁保持未完成。
