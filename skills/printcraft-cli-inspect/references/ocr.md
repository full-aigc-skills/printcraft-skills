# 显式 Tesseract 中文 OCR

原生 0.2.1 的 `ocr_recognize` 仍只支持 en。简繁中文使用本技能自身 `scripts/ocr.py`，必须显式选择 tesseract；不自动回退、不安装/升级依赖。当前真实验收组合是 macOS arm64、Tesseract 5.5.3、官方 tessdata_fast 4.1.0 的 chi_sim/chi_tra。其他外部平台尚未验收。

## 先诊断身份

将 TESSERACT 和 TESSDATA_DIR 指向用户已有可信安装；先核对来源，再把只读诊断输出保存为任务专用锁。不能把诊断当成对未知程序的信任认证。锁含实际可执行路径/摘要、版本、平台、模型和 pdf.ttf 摘要；升级后旧锁拒绝执行。诊断本身无写入，下例重定向是显式保存锁。

```bash
python3 -I -B "$SKILL_DIR/scripts/ocr.py" diagnose --backend tesseract --language chi_sim --tesseract "$TESSERACT" --tessdata-dir "$TESSDATA_DIR" > "$BACKEND_LOCK"
```

## 执行一次新任务

仅当用户要求或授权了 OCR 修改时执行。该方式将全部页栅格化为新图像 PDF，原表单、签名、书签、附件及矢量/原文字语义不保留；原件不覆盖。需要保留这些语义时停止选择此路径，说明缺口。用户已有该输出策略授权时无需再次确认。

```bash
python3 -I -B "$SKILL_DIR/scripts/ocr.py" run --backend tesseract --language chi_sim --backend-lock "$BACKEND_LOCK" --input "$ORIGINAL_PDF" --output-dir "$NEW_TASK_DIR" --runtime-home "$RUNTIME_DIR" --rasterize --dpi 150 --timeout 1800
```

繁体将两条命令 language 都改成 chi_tra。全新输出目录的父目录须已存在。固定原生须先由 setup 完成可信安装，本入口只复用已安装版本。Python 3.11+，外部执行入口当前仅随原生安装支持 macOS arm64；不捆绑字体、模型或二进制，不改变系统 PATH/配置。

每次渲染全部页，采用无损 PNG 避免 Tesseract 对 PPM 默认有损 JPEG；模型和 pdf.ttf 拷到隔离任务子目录，结束清理。使用整页自动分段 PSM 3；生成 searchable.pdf、searchable.txt、input.pdf、receipt.json 和最后子进程结果，任务目录私有。receipt 的 printcraft.ocr/1 与 commands.py 的 execution/verification 回执类型分开，不能把它传给 commands.py reconcile。stdout 只打印摘要和 receiptPath；完整原生目录及阶段诊断在该私有回执。查看 JSON 和实际输出进行只读对账；UNKNOWN/部分结果不自动重跑或换目录重放。

## 验收及限制

仅输出 DETERMINISTIC_PASS_REVIEW_REQUIRED：新原生进程重开页数/逐页中文文本、同 DPI 图像像素与尺寸一致，输入、技能和后端身份未漂移。每页必须包含中文，否则本严格入口拒绝确定性通过；空白/纯英语混合页目前不自动跳过。上限 100 页、256 MiB PDF、单页 4000 万像素；DPI 150–300。加密 PDF 没有密码接口。

像素几何与原生渲染相同；PDF 点尺寸可能因像素取整有不到一像素的差异，不保证原始页面点尺寸精确不变。提取文本存在阅读顺序/词间空格差异：searchable.txt 是后端识别结果，原生 PDF text 是独立检查，两者不能宣称逐字等同。固定原生 text_find 的整句搜索可能无命中，即使短词可找到、searchable.txt 正确；未完成独立 GUI 阅读器的搜索/选择验收，不承诺长句搜索可靠性。业务关键文字应按任务要求核对，排版、手写、表格、任意扫描精度均未保证。复杂页的识别错误需要人工或宿主审阅，不能凭“有中文”声称内容完全正确。

最终交付应绑定 searchable.pdf 摘要，审阅图像与目标文字；视觉未执行保持 NOT_RUN，不把零退出或确定性检查升级为全局 VERIFIED。普通入口超时只记录 UNKNOWN，无自动重试或回滚保证。

官方接口参考：[Tesseract 命令行与可搜索 PDF](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html)。模型归属/许可：[tessdata_fast 4.1.0](https://github.com/tesseract-ocr/tessdata_fast/tree/4.1.0)，Apache-2.0；随现有 Tesseract 的 pdf.ttf 单独校验。夹具证据与语言/平台矩阵由项目验收报告记录，不由这份使用说明替代。
