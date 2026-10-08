# 开放门禁与可审核的后续操作

当前发行版本为 0.1.0-dev.5，分发执行资源与已实测 dev.3 的摘要一致，六项技能源与插件快照保持一致；已增加只读公开交接命令及 Harness 委托。新增显式跨仓验收脚本不引入运行时兄弟仓依赖。原生版本仍固定 0.2.1。

## 已准备的真实跨插件验收

- `tests/artcraft_acceptance.py` 显式接收 ArtCraft 项目、VectorCraft 技能、各原生运行时及新工作目录；不自动安装、不修改生产者。
- `tests/artcraft_producer.ts` 通过真实 ArtCraft WorkflowEngine/LocalRunner/publicSkillFactory 调用 VectorCraft 0.2.0-craft.2，保存两个原创色块工程及 PDF，修改其中一个源工程，检查另一个节点复用及摘要不变。
- 真实 ArtCraft 项目包包含工程、依赖、导出和记录；移动到含中文/空格的目录后，通过其公开 package 核验函数重新检查全部文件。
- PrintCraft 0.2.1 实际消费两个阶段的 PDF，合并、保存重开，只裁剪返工页；渲染摘要验证保留页不变。
- 只证明本机目录移动及真实本地调用。未验证另一台机器、手机/平板、已发布生产者身份或完整宿主编排。原验收条文的“移动端交付”与任务的“移动交付”需明确，不能自行视为同义。

## OCR 和平台的实际限制

- 固定 0.2.1 实时 `ocr_recognize` / `ocr_recognize_files` Schema 的 language 枚举只有 `en`，ocr_status 也没有中文支持。不能把另一引擎或界面中文化记为该原生能力通过。
- 本机已有 Tesseract 和 chi_sim/chi_tra 模型。如果允许扩展执行方案，可新增显式 `ocr.py --engine tesseract`，分别绑定引擎/模型/输入/输出摘要，保持固定原生 CLI 不变，不静默回退或安装。独立记录中文识别和可搜索 PDF 的保存重开；不会重命名为原生 OCR。
- 该方案将修改本 change 的运行时/专项能力契约、六项自包含资源清单及其文档、相应测试和插件快照，并提升候选版本；在确认执行方案前不实施此扩展。
- Linux aarch64 官方 0.2.1 TAR 包已下载并核对 SHA256SUMS，CLI 二进制已提取；现有 Docker daemon 的存储只读，容器创建失败，原生执行 NOT_RUN。
- macOS x86_64 的实际启动因 Rosetta 不可用失败；远程台式机连接不可用。没有安装 Rosetta、修复 Docker 或变更远程环境。

## 发行状态

用户已明确授权“提交、推送 发布”。两个独立公开仓库、不可变 v0.1.0-dev.5 tag、GitHub 预发布、摘要附件与真实来源锁已建立；插件市场与技能源中英文导航已推送。Codex 从公开来源更新及从公开市场全新安装均通过，原始 PDF 和用户任务摘要不变。详见 release-2026-10-08.md。

本次关闭插件 5.4/5.5，不改写上游验收标准。技能源 7.2、7.4、7.5 和插件最终 5.6 继续开放；中文 OCR 的外部引擎扩展方案及移动端语义仍待明确。没有静默升级 CLI、安装 Skills CLI、安装 Rosetta、修复 Docker 或修改远程环境。
