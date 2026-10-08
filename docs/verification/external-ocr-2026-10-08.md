# 显式外部中文 OCR 验收（2026-10-08）

已获用户授权并实施独立可选 Tesseract 后端。固定 printcraft-cli 0.2.1 与原有七份共享执行资源均未改变；原生 ocr_recognize 仍只有 en，未宣称原生中文支持。六技能新增独立 ocr.py 和 references/ocr.md，共 78 个分发文件。

## 已实现与实测

- 显式 backend、可信本机身份锁、chi_sim/chi_tra、栅格化新副本策略；只读诊断，不安装、升级、改 PATH、透明回退或覆盖原件。
- SHA-256/版本/平台绑定 Tesseract、模型、pdf.ttf；输入/技能/后端前后校验；全新私有任务目录、attempted UNKNOWN、分阶段 execution/1、总截止、未知/失败不重放。
- 固定原生逐页渲染 → 不透明 RGB 无损 PNG → Tesseract 整页 PSM 3 → 多页带文本层 PDF/TXT → 新原生进程逐页检查；完整回执落盘，stdout 精简摘要。
- 当前源 73/73 基础单元测试，其中外部 OCR 10 项。初始红灯为缺失入口/接口，路径/无损 PNG 补充有接口缺失红灯；stdout 摘要补充为实际行为断言红灯，不把这些包装测试当成 OCR 识别证据。
- macOS arm64，已有 Tesseract 5.5.3，官方 tessdata_fast 4.1.0 简繁模型。原生二进制摘要固定，模型及字体与固定官方 URL 实际内容摘要一致；不捆绑模型、字体或二进制。
- 原创 CC0 简体/繁体各两页 PDF，输入逐页原生 text 为空。实际识别后 TXT 全部 12 行中文目标正确，新原生每页有中文及指定目标行，2+2 页、输入/输出同 DPI 逐像素一致、原件与资源/后端未变。`external-ocr/report.json` 与 final-chinese.zip 绑定当前执行资源和作者验收程序 SHA。
- 当前共享资源下原生 11 个场景回归通过，另有 ocr_status 实际观察；native-regression.zip 保留独立回执和产物。既有五平台原生/英语 OCR 证据继续只证明固定原生制品和原模型，不推广外部后端平台。

## 独立技能使用验证与真实限制

skill-creator 指引的独立使用验证已执行简体和当前源繁体场景。当前繁体 ocr.py SHA 为 `83d84b578e86753c689dadcab5f1be28551fd5db885b8a799f9f17302b3c878e`；完整证据在 forward-current.zip。两页视觉图像及 TXT 六行检查通过，输入与同 DPI 像素一致，stdout 1836 字节。

**PDF 阅读顺序审阅 FAIL，长句搜索未可靠通过。** 固定原生提取繁体文本时出现“合同金額”→“合金同額”、首行乱序及词间空格；searchable.txt 正确。“驗收”在两页均命中，但“合同”和金额整句不命中。简体亦有金额长句搜索 0 命中的观察。独立 GUI 阅读器搜索/选择 NOT_RUN。自动结果保持 DETERMINISTIC_PASS_REVIEW_REQUIRED、completeAcceptance=false；宿主视觉 PASS 单独记录，不能把它升级为 PDF 文字/搜索整体通过。

该版本提供明确限定的中文识别和带文本层图像 PDF 能力，不保证全文可检索、文字阅读顺序或任意 OCR 精度。关键内容须核对 TXT、实际 PDF 搜索与目标阅读器。若要求可靠整句搜索或保留交互语义，当前路径不满足。栅格化也不保留原表单、签名、书签、附件和矢量文本；页面点尺寸有一像素内取整差异。每页必须含中文；空白/纯英语混合页暂不自动跳过。

## 失败证据与范围

开发中保留的真实失败：Leptonica 无法读 /tmp 别名；PPM 触发 Tesseract 有损 JPEG，像素不一致；PSM 6 漏掉繁体一整行。分别通过真实父目录、无损 PNG、PSM 3 修正；原失败证据不改成 PASS。失败后创建新的明确开发验收任务，无业务 UNKNOWN 自动重放。

7.2 按“语言/模型矩阵 + 各自真实证据”的能力门禁关闭：原生中文仍 UNSUPPORTED，显式外部简繁识别 PASS_SCOPED_MACOS_ARM64，PDF 全文搜索/阅读顺序限制如上。其他外部平台、任意扫描质量和生产验收未声明。7.4 的手机/平板真机仍 NOT_RUN，7.5 与插件 5.6 不归档。

原始归档、成员和源文件摘要：external-ocr/collection.json。官方命令：[Tesseract CLI](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)；模型：[tessdata_fast 4.1.0](https://github.com/tesseract-ocr/tessdata_fast/tree/4.1.0)；字体：[Tesseract 5.5.3 pdf.ttf](https://github.com/tesseract-ocr/tesseract/blob/5.5.3/tessdata/pdf.ttf)。
