# 固定原生平台专项验收

任务关联：OpenSpec 7.2 / AE-03。此记录补充原生平台执行证据，未改变安装支持或中文/模型验收要求。

作者程序 `tests/platform_acceptance.py` 校验官方 0.2.1 归档及精确 CLI 成员的 SHA-256，仅取出已校验的普通文件，不执行其他归档成员。`tests/platform-artifacts.json` 记录五个 OS/CPU 组合的固定身份，macOS 两种 CPU 使用同一 universal 制品。

工作流 `Fixed native platform acceptance` 通过 workflow_dispatch 显式执行：Ubuntu 24.04 x64、Ubuntu 24.04 arm64、Windows 2025 x64、macOS 15 Intel、macOS 15 arm64。每个平台要求真实 OS/CPU 匹配、版本首行匹配、实时 123 项工具目录、原创 CC0 输入、五组修改/保存/新进程重开断言、相关渲染和原件不变。运行器原始 stdout/stderr、计划、PDF、PAM 及带摘要的报告作为 Actions artifacts 留存，包括失败记录。报告绑定提交和验收程序/锁/夹具摘要；作者脚本直接调用 CLI，不经过技能安装器和任务包装器。

## 本地执行与回归

- 本机 Darwin arm64 / Python 3.14.3，固定官方 universal CLI：五场景 PASS_SCOPED_NATIVE。报告 `/tmp/printcraft-publish-20261008/platform-local-2/native-platform-report.json`。
- 本地首次预检在表单场景发现作者工具构造器参数 `name` 与表单字段 `name` 冲突；重命名工具名参数后，完整五场景重新运行通过。该问题属于新增验收程序，不是原生 PDF 缺陷。
- 新增四项作者程序测试：归档/成员双摘要、只写精确普通成员、拒绝 TAR 链接、同页数错误顺序/空文本拒绝，均通过。首次运行因文件尚未实现产生导入失败，不宣称为目标行为红灯。
- 全部本地单元测试 56/56；包校验、六份资源同步检查通过；静态/夹具测试不替代平台原生结果。

## 边界

本轮没有修改六项技能的运行资源或版本，没有修改已发布 dev.5 制品。锁仍只支持 darwin-arm64 安装。直接原生执行即使通过，也不能宣称 Windows/Linux 的技能安装、执行互斥、权限或宿主入口已通过。

OCR 状态为真实观察；英语模型缺失和中文未支持不记为识别通过。手机/平板、跨机器交付、视觉审阅不由此矩阵替代。7.2、7.4、7.5 与插件 5.6 保持开放，未同步或归档。

CI 执行结果将在实际运行完成后追加，并保留失败原因。
