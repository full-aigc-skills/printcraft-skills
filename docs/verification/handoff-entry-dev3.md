# 0.1.0-dev.3 公开交接入口补充

已实现 `commands.py handoff` 及插件 Harness 的 `delegate handoff`。只读核验 artcraft.printcraft-handoff/1，要求调用者显式提供已确认的 producerVersion，拒绝缺失/不匹配版本、非法字段、相对路径、重复文件、错误摘要和链接；不安装或自动编辑。默认模块测试的 1.0.0 夹具不成为公开命令的默认信任版本。

```bash
python3 -I -B "$SKILL_DIR/scripts/commands.py" handoff "$HANDOFF_JSON" \
  --producer-version "$EXPECTED_ARTCRAFT_VERSION"
```

实际红灯：新增公开入口测试被旧参数解析器拒绝，退出 2，证据 handoff-entry-red.log。最小实现后，同一测试通过，缺失/错误版本仍拒绝，缺失运行时目录未被创建。

当前验证：技能包 52/52，插件 12/12；两个独立临时副本分别通过，真实原生 11 项场景通过。跨插件验收已改为公开 handoff 命令，实际生产者及源工程/定向返工、未修改页、移动目录重开均有当前证据，见 cross-plugin-public-artifacts/。手机平板及跨机器 NOT_RUN。

插件本地更新测试最初因旧夹具把“新版本”硬编码为 dev.3，与当前版本相同而失败；修正为从实际版本生成更高候选，保留正向更新、回退拒绝和用户数据保留断言。原失败与绿灯日志均保留，没有修改运行时回退判定。

当前 Codex 缓存实际安装 dev.3；plugin/read 发现七项技能。gpt-5.6-sol 的自然语言检查及显式 Harness 交接/PDF 重排/重开实际通过；缓存 69 项技能文件与当前插件一致，模型凭据临时链接已移除。模型原始结果仍为待视觉审阅，主任务随后实际查看三页图像并对归档副本独立验收；仅原创夹具组合 VERIFIED。

上述宿主证据由 printcraft-plugin 的 docs/verification/plugin-read-dev3.json、model-handoff-dev3-binding.json、model-handoff-*-dev3.jsonl 和 model-handoff-dev3-artifacts/ 持有。旧版本模型报告保留为历史，不替代本次复验。

OpenSpec 已完成任务数仍为技能源 35/38、插件 21/24；7.2、7.4、7.5 与插件 5.4、5.5、5.6 的剩余门禁未满足。Git/远端/发行、OCR 执行方案与移动端定义仍待对应授权或澄清，没有提前同步或归档。
