# 真实跨插件及定向返工验收

结果：真实本地跨插件流程 PASS；当前归档 PDF 的确定性检查与 Codex 实际图像审阅组合为 VERIFIED，范围仅为原创色块夹具。本报告原始执行仅覆盖本机；后续 cross-machine-2026-10-08.md 已补独立 Linux/Intel Mac 接收。任务 7.4 的手机/平板部分未满足，整体任务继续开放。

## 实际流程与身份

```mermaid
flowchart LR
    A[ArtCraft 真实 WorkflowEngine] --> B[VectorCraft 公开 workflow.py]
    B --> C[保存两个工程和 PDF]
    C --> D[目标源工程只改红色为蓝色]
    D --> E[另一个绿色工程复用原任务和摘要]
    E --> F[ArtCraft package 及移动后验包]
    F --> G[PrintCraft 校验 producer 版本与 PDF 摘要]
    G --> H[合并两个 PDF并重开]
    H --> I[仅裁剪第1页并保存]
    I --> J[第2页渲染摘要保持不变]
    J --> K[归档后重新核验并审阅]
```

- ArtCraft 当前源码版本 0.1.0-dev.113-runtime.1；记录整个 src/、schemas/ 及 package.json 的执行前后摘要，不将当前工作树称为已发布宿主插件。
- VectorCraft 使用现有固定原生 0.2.0-craft.2 及公开、自包含技能资源。资源在前后核对，当前源码身份随报告保存，没有升级或修改生产者仓库。
- PrintCraft 固定原生 0.2.1，二进制 SHA-256 b7783b596870ed5a326f29456d4647382d2e1e4d7b7ffe75ded192cd15b86995。
- Python 3.13.5，Node 实际版本可见已有运行环境；不依赖另一个模型、源码构建或模拟 CLI。

## 验收断言

1. 两个原生节点初次生成并保存工程、PDF 和 PNG；ArtCraft 状态保持 review_ready。
2. 只通过原源工程和 expectedRevision 改目标填色；只重跑 change 节点，preserve 节点任务 ID 与 PDF 摘要不变。
3. 原工程、引用、依赖与导出被实际项目包收集；目录移动后通过 ArtCraft 的公开 verifyProjectPackage 检查。
4. PrintCraft 使用校验过的两个 PDF 合并；第1页返工前后渲染变化，第2页在两轮合并和局部裁剪后渲染摘要相同。
5. 局部裁剪仅作用于第1页，重新打开仍为两页。目标色块完整，独立绿色页不变，Codex 实际查看 PNG；最终 PAM 与被查看图像的原始 PAM 六项摘要一致。
6. 归档后的输入与产物再绑定验收请求，重新重开；组合审阅通过，不延伸为任意 PDF 创作接受或真实人工接受。

## 证据与复现

`cross-plugin-artifacts/` 保留首次真实运行；`cross-plugin-public-artifacts/` 为当前 dev.3 公开 handoff 命令的重验，包含运行报告、两个完整项目包、原始/返工 PDF、PAM/PNG 和归档验收请求/回执。原报告内临时路径是历史运行位置；archive-* 文件针对当前归档文件重新核验。所有示例图形为本次原创简单矩形，CC0；不包含字体、品牌标志、用户媒体或凭据。

```bash
python3 -I -B tests/artcraft_acceptance.py \
  --artcraft-root "$ARTCRAFT_ROOT" --vector-skill "$VECTOR_SKILL" \
  --vector-executable "$VECTOR_CLI" --vector-runtime-home "$VECTOR_RUNTIME_HOME" \
  --runtime-home "$PRINTCRAFT_RUNTIME_HOME" --workdir "$NEW_WORKDIR"
```

所有依赖路径需由调用者显式提供；缺少依赖直接失败，不在基础 unittest 中假装跨项目通过。producerVersion 兼容列表由本次明确指定的实际生产者版本传入；默认夹具版本 1.0.0 仍不是实际版本支持声明。

限制：本流程不证明手机/平板、另一台机器、正式发布身份、完整宿主跨插件路由或任意复杂工程的无损交换。原生语言/平台限制和 Git/发行权限门禁单独开放。
