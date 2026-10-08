> 当前实现/验收状态以 [2026-10-08 报告](verification/implementation-2026-10-08.md) 和 project-status.json 为准；下文保留早期架构/候选说明。

# Local delivery architecture

The independently maintained skills are the source. Each skill includes its own pinned CLI bootstrap, public argv launcher, command catalog gateway and runtime lock. A local plugin snapshot carries checksums for those skill files. It is unpublished; it must not enter the marketplace until source release pinning and host acceptance pass.

```mermaid
flowchart LR
 H[Host skill discovery: pending] --> S[Loaded standalone skill]
 S --> B[Checksummed bootstrap]
 B --> N[Pinned native CLI: execution pending]
 S --> Q[Live catalog and plan validation]
 Q --> N
 N --> A[Native projects and exports: acceptance pending]
 A --> R[Reopen and targeted revision: acceptance pending]
```

PrintCraft supplies JSON Schema. LightCraft and DesignCraft supply parameter guidance text; it must not be promoted to machine-checked schema. Plans execute in one native process. Timeouts remain unknown and never trigger automatic replay. Zero exit requires artifact inspection and creative review. Installation, host discovery, model selection and final output are separate acceptance gates.

OpenSpec is initialized and the optimization change is authored; implementation and native installation remain pending. No Git repository or remote release has been created. Existing five plugin specifications remain authoritative for their domains; shared ArtCraft integration for these three domains is still pending.


Runtime preflight now binds the release tag and archive name to the locked binary identity and version, rejecting mismatches before runtime creation. The pinned releases remain 0.2.1. Upstream source is now named PdfCraft; skill names and plan domain remain printcraft. The bootstrap supports separately pinned printcraft-cli and pdfcraft-cli binaries without moving old installations; the current released lock remains printcraft-cli 0.2.1.

## 优化规格与任务

已建立 OpenSpec 变更 [harden-printcraft-skill-execution](../openspec/changes/harden-printcraft-skill-execution/proposal.md)，见[设计](../openspec/changes/harden-printcraft-skill-execution/design.md)与[任务](../openspec/changes/harden-printcraft-skill-execution/tasks.md)。当前仅完成规格编写；实现、原生、宿主及发布门禁保持未完成。
