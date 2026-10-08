# 平台与 OCR 矩阵

| 平台/能力 | 结果 | 证据 |
|---|---|---|
| macOS arm64 / printcraft-cli 0.2.1 | 技能冷安装 PASS；直接原生五场景及英语 OCR PASS | 已发布 dev.5 冷安装记录、五平台专项报告 |
| macOS x86_64 | PASS_SCOPED_NATIVE_DIRECT | CI macos-15-intel，官方 universal 固定摘要 |
| Linux aarch64 | PASS_SCOPED_NATIVE_DIRECT | CI ubuntu-24.04-arm，官方 TAR / CLI 双摘要 |
| Linux x86_64 | PASS_SCOPED_NATIVE_DIRECT | CI ubuntu-24.04，官方 TAR / CLI 双摘要 |
| Windows x86_64 | PASS_SCOPED_NATIVE_DIRECT | CI windows-2025，官方 portable ZIP / CLI 双摘要 |
| 其他平台的技能安装/包装执行 | NOT_RUN / UNSUPPORTED_BY_CURRENT_LOCK | 安装锁仍只声明 darwin-arm64，不把直接原生测试推广到包装器 |
| 英语 OCR | PASS_SCOPED_5_NATIVE_PLATFORMS | 固定上游模型双摘要；无文本扫描件识别、保存、新进程读回 PAGE-GAMMA、原件不变 |
| 中文原生 OCR | UNSUPPORTED_BY_PINNED_NATIVE | 五平台实时 Schema 均 enum=[en]；既有本机真实 zh 请求拒绝，不记为识别通过 |
| 显式外部 Tesseract 中文 OCR | PASS_SCOPED_MACOS_ARM64 | Tesseract 5.5.3 / 官方 tessdata_fast 4.1.0，简繁各两页无文本扫描件、中文目标、新进程重开与无损像素一致；不替代原生中文能力，见 external-ocr-2026-10-08.md |
| 扫描件分类 | PASS | scan-receipt.json: 无文本图像 PDF 需 OCR/意图审阅 |
| ArtCraft 协议 | 夹具完整性/兼容拒绝 PASS | verification.validate_handoff 单测 |
| ArtCraft 实际生产者及选择性返工 | PASS_SCOPED_LOCAL_NATIVE | 真实调度器/VectorCraft 源工程/PDF 交接，详见 cross-plugin-2026-10-08.md |
| 本机目录移动交付 | PASS_SCOPED | 实际项目包验包、PDF 重开及保留页渲染摘要 |
| 跨机器项目包/PDF 交付 | PASS_SCOPED_CROSS_MACHINE | macOS arm64 发送，Linux x64 / macOS Intel 实际接收验包、PDF 重开及单页返工；见 cross-machine-2026-10-08.md |
| 手机/平板交付 | DEVICE_AUTHORIZATION_REQUIRED / NOT_RUN | 已连接 Android USB 设备尚未授权；不将跨机器托管运行器替代手机/平板实测，7.4 继续开放 |

五平台真实执行与模型来源见 [专项验收](native-platforms-2026-10-08.md)。初始本机探测 platform-probe.json 作为历史记录保留；其中 Docker/Rosetta/远程主机的阻塞不再代表原生平台矩阵当前状态。

第二轮 CI 37772042337 绑定提交 bad64e181e1b6b4e8d60e10cdb7623b6d2710d74，五个平台各六项场景通过。实际 OS/CPU、官方归档/CLI 摘要、模型摘要/许可、输入/产物/日志摘要和源码指纹均独立记录。OCR 模型未随技能/插件及证据包再分发，未用其他引擎替代固定原生。
