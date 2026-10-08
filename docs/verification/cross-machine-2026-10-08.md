# 跨机器完整项目包与 PDF 交付验收

任务：OpenSpec AE-03、PV-04 / 7.4，补跨机器部分，手机/平板继续独立开放。

使用此前真实 ArtCraft 0.1.0-dev.113-runtime.1 / VectorCraft 0.2.0-craft.2 生成的完整两个项目包、依赖、源工程、返工 PDF 和原始 PAM，均为原创 CC0 色块场景。tests/cross-machine-fixture.json 绑定项目清单摘要、producer 报告摘要、PDF 摘要及两个交付页渲染摘要。未重新执行原始过期的 ArtCraft 工作流。

发送作业在 macOS 创建传输 ZIP，记录每一成员身份、真实 OS/CPU、当前提交、作业与运行器身份。独立 Linux x64 和 macOS Intel 接收作业从同一 Actions artifact 下载，先验 ZIP 与文件表，再展开到含中文与空格的新路径。固定 ArtCraft 消费者源码 4ff30a88bbdc0c268dc17d7cddb7f3aed77544e8，调用官方 verify-package；这与原 producer 113 的身份分别记录。PrintCraft 公开 handoff 入口验证原 producer 兼容和 PDF 摘要，随后直接执行官方固定 0.2.1 原生 CLI，重开 PDF、核对两个页渲染，再在接收机仅裁剪第1页并保存重开，第2页渲染保持相同。全部传输输入必须保持不变。

不把跨机器证据推广为手机/平板、任意复杂工程、原生产者在新平台重新执行、其他平台技能安装器或完整宿主路由验收。接收报告仍标记 visualReview=NOT_RUN，像素断言绑定此前实际审阅的原创色块交付。

## 开发验证

- 路径边界测试先暴露九个不安全/不可移植成员被接受的行为红灯（cross-machine-red.log），再实现拒绝并验证绿灯。
- 六项传输测试覆盖 Unicode/空格、逃逸路径、传输摘要、成员摘要、未列文件和已有目的目录/用户内容保护。
- 本机打包成功；本机接收预检在 ArtCraft HEAD 身份检查处拒绝：当前本地依赖已变化为 ef6656f0fa6c51717e8eaa7a09fbdfd3ea0d0d55，与锁定 4ff30a88 不同。见 cross-machine-local-identity-refusal.json；没有把该预检称为跨机器通过。CI 将按固定提交独立检出消费者。
- 实际 CI 运行结果随后追加；尚未运行时不关闭任务。

## 真实 CI 与证据收集

[运行 37773443950](https://github.com/full-aigc-skills/printcraft-skills/actions/runs/37773443950)，源提交 `cb90b21920e04fbe0f65be3d0fe8619cbe33e1da`。发送作业和两个接收作业均成功：macOS arm64 发送 → Linux x86_64、macOS x86_64 接收。两接收机均记录 PASS_SCOPED_CROSS_MACHINE，原始 ArtCraft 工作流未重新运行，手机/平板与视觉审阅保持 NOT_RUN。

传输 ZIP 含 59 个登记文件，两个接收机核对同一传输 SHA。官方 ArtCraft 消费者固定提交 4ff30a88，实际 Node 版本随每份报告保存。两份项目包的清单、portable plan、源工程及登记引用分别通过官方 verify-package；PrintCraft 公共 handoff 入口接受原 producerVersion 113 的明确兼容配置。固定原生制品下载/CLI 摘要和 123 项实时目录均绑定；传入返工 PDF 与接收机新返工 PDF 的两页 PAM 均匹配原交付像素摘要，第2页保留不变。全部传输输入保持原摘要。

`cross-machine-ci/` 保存三份官方 Actions ZIP、发送/接收报告、运行/任务/制品 API、完整原始日志和 collection.json。外层 ZIP SHA 均匹配 GitHub API digest，内层传输 ZIP、59 个成员及接收报告的所有产物/日志摘要逐项核对，总计 165 个成员摘要与 14 项作者/消费源文件摘要通过。全部源指纹对应上述源提交，而不是事后文档提交。相关包 CI [37773438285](https://github.com/full-aigc-skills/printcraft-skills/actions/runs/37773438285) 四项成功，本地单元测试 63/63、包校验和受控资源检查通过。

## 剩余门禁

ADB 检测到一台 Android USB 设备，但状态 unauthorized，具体手机/平板型号尚不能读取。设备所有者需在设备上允许 USB 调试；未将 ADB 命令退出 0 当成设备已授权。当前状态见 mobile-device-status.json，未保存设备标识。iOS devicectl 未安装，不进行工具安装。

7.4 的跨机器部分已取得真实范围证据，但手机/平板仍未验收，整体继续开放。7.2 的固定原生中文 OCR 缺口也仍存在；7.5 与插件 5.6 的全门禁同步/归档继续等待，不因 CI 通过或既有发布关闭。
