# PrintCraft skills

Prerelease **0.1.0-dev.6**, pinned printcraft-cli 0.2.1 for macOS arm64 / Python 3.11+.
Six independently installable skills provide runtime diagnostics, PDF inspection/page edits, single-session plans, uncertain-outcome reconciliation and digest-bound artifact verification.

Execution and verification use independent versioned protocols. A zero exit is not delivery acceptance. Native sample evidence is separate from host/model, OCR, cross-plugin and release gates. Explicit optional Tesseract Chinese OCR is validated on macOS arm64; pinned native OCR remains English-only. Five native platforms have separate direct-runtime evidence; the skill installer supports macOS arm64. Mobile-device delivery remains unverified. See project-status.json for the current publication receipt.

See [中文使用说明](README.zh-CN.md), [implementation evidence](docs/verification/implementation-2026-10-08.md), and [OpenSpec tasks](openspec/changes/harden-printcraft-skill-execution/tasks.md).

Install a single skill from the immutable prerelease:

```bash
npx skills add https://github.com/full-aigc-skills/printcraft-skills/tree/v0.1.0-dev.6/skills/printcraft-use
```

[Release](https://github.com/full-aigc-skills/printcraft-skills/releases/tag/v0.1.0-dev.6). This is a development prerelease, not full platform or production acceptance.
