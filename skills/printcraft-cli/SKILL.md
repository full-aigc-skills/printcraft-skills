---
name: printcraft-cli
description: 用户明确要求 PrintCraft 原生 CLI、具体工具、参数 Schema、表单、签名、脱敏或 PDF/A 专项操作时使用；先发现固定版本能力。
license: Apache-2.0
---

# 原生工具契约

先 list/describe 获取真实 Schema；专项操作分别验收，不从工具存在推断功能已通过。

受控开发预发布。Python 3.11+；固定发行 printcraft-cli 0.2.1，仅 macOS arm64 锁已验证。入口保持 printcraft，不把 research 的 PdfCraft 新接口当成当前发行能力。

将 `SKILL_DIR` 设置为宿主实际加载的本文件目录。所有脚本和引用都随本技能分发，不依赖兄弟目录；运行时放在独立用户数据目录。

```bash
python3 -I -B "$SKILL_DIR/scripts/bootstrap.py" --diagnose
# 仅已有安装授权时：
python3 -I -B "$SKILL_DIR/scripts/bootstrap.py" --runtime-home "$RUNTIME_DIR"
python3 -I -B "$SKILL_DIR/scripts/commands.py" list --runtime-home "$RUNTIME_DIR"
python3 -I -B "$SKILL_DIR/scripts/commands.py" describe doc_open --runtime-home "$RUNTIME_DIR"
```

`--archive` 可指定离线固定 ZIP，仍验证全部摘要；不修改 PATH。`cli.py -- tools` 首用可能安装，不能称为只读安装诊断。

计划格式：`{"domain":"printcraft","steps":[{"command":"实际工具名","params":{}}]}`。先查 Schema 再填参数。

```bash
python3 -I -B "$SKILL_DIR/scripts/commands.py" check "$PLAN" --runtime-home "$RUNTIME_DIR"
python3 -I -B "$SKILL_DIR/scripts/commands.py" run "$PLAN" --output "$NEW_TASK_DIR" --expect "$OUTPUTS" --input "$ORIGINAL_PDF" --runtime-home "$RUNTIME_DIR"
python3 -I -B "$SKILL_DIR/scripts/commands.py" status "$NEW_TASK_DIR/receipt.json"
python3 -I -B "$SKILL_DIR/scripts/commands.py" reconcile "$NEW_TASK_DIR/receipt.json"
python3 -I -B "$SKILL_DIR/scripts/commands.py" verify "$VERIFY_REQUEST" --runtime-home "$RUNTIME_DIR"
```

输出目录必须全新；runId 只用于追踪，不保证 exactly-once。已执行/结果不明的任务不能通过换目录或 runId 重放。只读对账不启动原生编辑。旧/损坏回执拒绝恢复，保留原件调查。

显式 `--input` 登记需保护的文件或目录，执行前后检测摘要；参数中未登记的路径不受该检查覆盖，这不是沙箱。优先编辑工作副本；现有用户授权直接复用，仅新增加原件覆盖、真实打印或超出输出范围时重新确定授权。原生过程可能写文件、联网或使用系统资源。

零退出只到 REVIEW_REQUIRED。必须检查显式清单、大小/摘要、新进程重开、逐页文本与几何，再完成当前摘要绑定的视觉审阅。未知或部分结果不自动重放；不自动循环修订。表单、脱敏、签名、PDF/A、OCR 分别记录验收状态。

秘密字段包含 password/passwd/secret/token/api_key/credential；公开回执脱敏，私有执行材料权限 0600，结束后清理。避免把秘密放进文件名或不相关普通字段。任务目录仍可能含敏感 PDF，应由用户按保留策略清理。

中文扫描识别：显式可选 Tesseract 后端见 [中文 OCR 契约](references/ocr.md)。原生 0.2.1 仍只有英语；该路径生成栅格化新副本，先核实输出策略及后端身份。

详见 [契约与边界](references/contracts.md)、[成功/失败/拒绝案例](examples/scenarios.md)。

路由：一般任务 **printcraft-use**；环境 **printcraft-cli-setup**；检查 **printcraft-cli-inspect**；页面 **printcraft-cli-pages**；批处理恢复 **printcraft-cli-automation**；专项契约 **printcraft-cli**。若需要其他技能，按名称安装：`npx skills add full-aigc-skills/printcraft-skills --skill <技能名>`。
