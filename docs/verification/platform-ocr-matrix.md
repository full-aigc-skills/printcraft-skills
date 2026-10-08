# 平台与 OCR 矩阵

| 平台/能力 | 结果 | 证据 |
|---|---|---|
| macOS arm64 / printcraft-cli 0.2.1 | 冷安装及原生样例 PASS | 固定 SHA、native-report.json |
| macOS x86_64 | BLOCKED_BEFORE_NATIVE_EXECUTION | 实际 arch -x86_64 启动固定 CLI 返回 Bad CPU type；未安装 Rosetta |
| Linux aarch64 | ARTIFACT_HASH_PASS / NATIVE_NOT_RUN | 官方 0.2.1 TAR 与 CLI 摘要已核对；Docker 存储只读导致容器创建失败 |
| Windows | UNSUPPORTED_BY_CURRENT_LOCK / NOT_RUN | 远程执行连接不可用；未建立目标运行证据 |
| 英语 OCR | MODEL_MISSING / NOT_RUN | ocr_status: available=false，languages=[en] |
| 中文原生 OCR | UNSUPPORTED_BY_PINNED_NATIVE | 实时 Schema enum=[en]，实际 zh 请求返回 unsupported language；不能记为支持通过 |
| 外部 Tesseract 中文模型 | PRESENT / INTEGRATION_NOT_RUN | 本机只读列出 chi_sim/chi_tra；未集成技能，不能替代原生能力 |
| 扫描件分类 | PASS | scan-receipt.json: 无文本图像 PDF 需 OCR/意图审阅 |
| ArtCraft 协议 | 夹具完整性/兼容拒绝 PASS | verification.validate_handoff 单测 |
| ArtCraft 实际生产者及选择性返工 | PASS_SCOPED_LOCAL_NATIVE | 真实调度器/VectorCraft 源工程/PDF 交接，详见 cross-plugin-2026-10-08.md |
| 本机目录移动交付 | PASS_SCOPED | 实际项目包验包、PDF 重开及保留页渲染摘要 |
| 跨机器/手机平板交付 | NOT_RUN | 不用本机目录移动替代设备验收；7.4 继续开放 |

实际探测记录见 platform-probe.json。发行制品的归档摘要为 c7ae5dac00b3c11bea4e7cc502878a1b6ab520362d09885293e48417452e5dc0，CLI 摘要为 8123365733dbfd70e982eaad2bec6e12b87a203ee9ffa9acf7bc8ceba6a0ad36；它们未加入当前仅 macOS arm64 的运行时安装锁。
