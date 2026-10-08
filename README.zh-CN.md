# PrintCraft 独立技能

预发布 **0.1.0-dev.6**，固定 `printcraft-cli 0.2.1`，Python 3.11+ / macOS arm64。六项技能可单独复制安装；默认自然语言入口 `printcraft-use`，专业入口显式调用。GitHub 发行身份与发布回执见 project-status.json；该版本用于受控测试。

| 技能 | 职责 |
|---|---|
| printcraft-use | 任务路由、输入登记和交付 |
| printcraft-cli-setup | 只读诊断与固定安装 |
| printcraft-cli-inspect | 元数据、文本和预览 |
| printcraft-cli-pages | 提取、合并、重排、旋转、裁剪 |
| printcraft-cli-automation | 单会话计划、状态和恢复 |
| printcraft-cli | 工具 Schema 与专项契约 |

从宿主实际加载的 SKILL.md 确定 `SKILL_DIR`，不要使用开发路径。

```bash
python3 -I -B "$SKILL_DIR/scripts/bootstrap.py" --diagnose --runtime-home "$RUNTIME_DIR"
# 已授权安装时使用普通 bootstrap；支持 --archive 固定离线 ZIP。
python3 -I -B "$SKILL_DIR/scripts/commands.py" list --runtime-home "$RUNTIME_DIR"
python3 -I -B "$SKILL_DIR/scripts/commands.py" describe doc_open --runtime-home "$RUNTIME_DIR"
python3 -I -B "$SKILL_DIR/scripts/commands.py" check "$PLAN" --runtime-home "$RUNTIME_DIR"
python3 -I -B "$SKILL_DIR/scripts/commands.py" run "$PLAN" --output "$NEW_TASK_DIR" --run-id "$RUN_ID" --input "$ORIGINAL" --expect "$OUTPUTS" --runtime-home "$RUNTIME_DIR"
python3 -I -B "$SKILL_DIR/scripts/commands.py" reconcile "$NEW_TASK_DIR/receipt.json"
python3 -I -B "$SKILL_DIR/scripts/commands.py" verify "$VERIFY_REQUEST" --runtime-home "$RUNTIME_DIR"
```

普通 cli 首用可能安装，不是只读诊断。离线 `--catalog` 仅支持 list/describe/check，不能执行。计划为 `{"domain":"printcraft","steps":[{"command":"真实工具","params":{}}]}`；输出声明为 `{"outputs":[{"path":"绝对 PDF 路径","role":"delivery","mediaType":"application/pdf"}]}`。--output 是回执目录，与 PDF 业务输出路径不同。

执行通道 `printcraft.execution/1` 保留 UNKNOWN、阶段、退出码与诊断；查询/编辑/渲染采用不同截止，MCP 由 EOF/显式停止结束。runId 注册表位于输出父目录 `.printcraft-runs`，防止同根重复启动；不承诺跨根全局幂等。历史状态损坏或丢失只读保留，不换身份自动重放。doc ID 只在一次原生进程内有效，多步非事务。

验收通道 `printcraft.verification/1` 绑定输入、候选摘要、规则版本和页数/逐页内容/几何/来源页映射；零退出仍待验收。确定性检查后，`verification.accept_review` 接受同请求摘要的显式视觉审阅；内容变动使旧结论失效，修订不自动循环。

## 验证与证据

```bash
python3 -I -B scripts/validate_package.py
python3 -I -B scripts/sync_skill_resources.py --check
python3 -I -B -m unittest discover -s tests
python3 -I -B scripts/check_tool_coverage.py --catalog "$LIVE_CATALOG"
# 显式原生验收，workdir 必须全新：
python3 -I -B tests/native_acceptance.py --runtime-home "$RUNTIME_DIR" --workdir "$NEW_ACCEPTANCE_DIR"
```

本地回归与原生验收分别执行。固定制品冷安装、123 项工具发现及原创 PDF 页面/表单/脱敏/签名语义/PDF-A 子集已有实际证据；签名夹具为未受信任自签名，不能报告签名有效。固定原生 OCR 的语言枚举仅支持英语，中文请求仍被原生明确拒绝。新增显式 Tesseract 简繁中文后端，使用契约见 [中文 OCR](skills/printcraft-use/references/ocr.md)；五平台直接原生/英语 OCR 已验证，包装器安装仍仅 macOS arm64，手机真机交付仍开放。真实 ArtCraft → VectorCraft → PrintCraft 本机公开入口及定向返工已经通过，范围见 cross-plugin-2026-10-08.md。完整标准符合性不由子集检查推导。

当前结果及命令见 [实施验收报告](docs/verification/implementation-2026-10-08.md)，源码指纹见 [证据索引](docs/verification/evidence-index.json)。

## 插件受控同步

技能源拥有同步器；本插件运行时不依赖此工具。同步先检查现有摘要/来源，不覆盖漂移、不删除源移除项，不降级正式身份；保留插件本地 `printcraft-harness`。同步中断可能留下部分文件已更新，必须核对摘要后处理，不能直接改锁掩盖漂移。

```bash
python3 scripts/sync_local_snapshot.py --plugin-root "$PLUGIN_ROOT"
```

[OpenSpec 变更](openspec/changes/harden-printcraft-skill-execution/proposal.md)与[任务](openspec/changes/harden-printcraft-skill-execution/tasks.md)是唯一正式规格；外部验收/发行门禁未满足前不归档。

## 预发布安装

```bash
npx skills add https://github.com/full-aigc-skills/printcraft-skills/tree/v0.1.0-dev.6/skills/printcraft-use
```

[GitHub 预发布](https://github.com/full-aigc-skills/printcraft-skills/releases/tag/v0.1.0-dev.6)。不捆绑原生二进制、字体或 OCR 模型；需要运行时安装时按技能入口明确执行。
