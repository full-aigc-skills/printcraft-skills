# PrintCraft skills

Prerelease **0.1.0-dev.5**, pinned printcraft-cli 0.2.1 for macOS arm64 / Python 3.11+.
Six independently installable skills provide runtime diagnostics, PDF inspection/page edits, single-session plans, uncertain-outcome reconciliation and digest-bound artifact verification.

Execution and verification use independent versioned protocols. A zero exit is not delivery acceptance. Native sample evidence is separate from host/model, OCR, cross-plugin and release gates. Chinese OCR, other native platforms and mobile-device delivery remain unverified. See project-status.json for the current publication receipt.

See [中文使用说明](README.zh-CN.md), [implementation evidence](docs/verification/implementation-2026-10-08.md), and [OpenSpec tasks](openspec/changes/harden-printcraft-skill-execution/tasks.md).

Install a single skill from the immutable prerelease:

```bash
npx skills add full-aigc-skills/printcraft-skills@v0.1.0-dev.5 --skill printcraft-use
```

[Release](https://github.com/full-aigc-skills/printcraft-skills/releases/tag/v0.1.0-dev.5). This is a development prerelease, not full platform or production acceptance.
