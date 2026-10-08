# Paper Project Auditor

An agent skill for auditing research-paper project directories for authenticity, internal consistency, provenance, and computational reproducibility.

The workflow inventories the complete project, compares manuscript claims with code and artifacts, performs static safety checks before execution, selectively reruns analyses in an isolated copy, and produces an evidence-backed audit report.

## Install

Clone this repository into a supported personal skills directory:

```sh
git clone https://github.com/ymliu17/paper-project-auditor.git ~/.agents/skills/paper-project-auditor
```

For older Codex installations that use `~/.codex/skills`:

```sh
git clone https://github.com/ymliu17/paper-project-auditor.git ~/.codex/skills/paper-project-auditor
```

Restart the app if the skill does not appear immediately.

## Use

In Codex, invoke the skill with:

```text
$paper-project-auditor audit the current project
```

The skill treats submitted project code as untrusted, preserves the original project, and performs execution only in an isolated working copy.

## Contents

- `SKILL.md`: workflow and audit requirements
- `references/`: audit checklist, execution policy, and report schema
- `scripts/`: inventory, risk scanning, captured execution, and result-comparison utilities
- `agents/openai.yaml`: UI metadata
