# 固定运行时与任务契约

- bootstrap --diagnose：只读；普通 bootstrap/cli 首用可能安装。仅支持锁内平台，不靠 PATH 找其他同名二进制。新旧 binary 名和版本目录隔离。
- 页码为 1-based；页框以 point 表示。page_set_box 的 rect 从显示页左上角起；margins 从 MediaBox 左/下/右/上量。先 describe，不把 UI 坐标直接塞入 PDF。
- doc_open 返回的 ID 仅当前 run 有效；新进程必须重开。首次单会话只打开一个文档才可预期 ID 1，不跨任务保存 ID。多步骤非事务，错误可能留下前序输出。
- doc_save 带新 path 为另存；省略会写原路径，必须具有原件修改授权。只读对账不会重新保存。书签/表单/签名/加密的保留须独立比较，不从页数推断。
- 扫描件空文本分类为 EMPTY_NEEDS_OCR_OR_INTENT_REVIEW，不能当成无内容；OCR 语言和模型须现场 ocr_status 确认，原生中文仍不支持。显式 Tesseract 中文路径、版本与平台边界见本技能 ocr.md，不把外部能力计入原生目录。
- query 120s，edit 600s，render/run 1800s；MCP/UI 无普通任务截止，通过 EOF/显式停止结束。超时即 UNKNOWN；后代未确认结束时绝不重放。
- execution/1 回执绑定 runId、attempted、plan/catalog/input/resource/runtime 摘要；私有文件原子写入。status/reconcile 只读，旧回执拒绝恢复。
- verification/1 请求包含 ruleVersion:1 和 outputs，每项 path、sha256、pages，可选 pageText、firstPagePt、textPolicy(required/scan/optional)。内容或规则变化需重新验收，不能复用审阅。
- accept_review 要求 reviewer/notes/decision(approve 或 revise)、同 requestSha256/ruleVersion，重新核对所有产物摘要。局部修订只提出下一候选，不自动重新执行整个任务。
- 外部交接 artcraft.printcraft-handoff/1 要求兼容 producer、producerVersion 和逐文件 sha256。验证完整性不证明真实跨插件交付。

本入口重点：新进程 info/text 检查内容；空文本分类需要 OCR 或视觉确认。需要修改时交给页面或专项入口。

默认自然语言入口为 printcraft-use；专业入口元数据为显式调用。runId 互斥与消费标记作用于输出父目录的 .printcraft-runs 注册表；跨任务根不提供全局幂等。--expect 指定 {"outputs":[{"path":"绝对路径","role":"delivery","mediaType":"application/pdf"}]}，在副作用前登记并在执行/对账后收集身份。验证请求可用 sourcePages 对照来源文件摘要和页码、pageGeometry 检查逐页旋转/尺寸。ArtCraft 交接默认仅接受候选夹具 producerVersion 1.0.0；实际来源版本需显式兼容表，尚未做真实 ArtCraft 集成。

已确认的覆盖/打印授权由调用方传入重复 --allow-scope，例如 overwrite:/absolute/original.pdf 或 print；原件保存（doc_save 不带 path）、已存在目标及 doc_print 在缺少范围时于原生编辑前拒绝。该检查只识别已知显式保存/输出/打印工具，不是其他原生能力的沙箱；已有会话授权直接复用，不重复询问。

公开只读交接：`python3 -I -B "$SKILL_DIR/scripts/commands.py" handoff "$HANDOFF_JSON" --producer-version "$EXPECTED_ARTCRAFT_VERSION"`。兼容版本来自调用者已确认的生产者配置，不能从陌生交接文件自身推导信任。仅检查协议、版本和逐 PDF 摘要，不安装、不启动原生编辑，不证明生产者已执行或完整创作通过。
