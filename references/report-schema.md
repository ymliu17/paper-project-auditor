# Audit Report Schema

Create both Markdown and JSON outputs. Adapt headings only when a section is genuinely inapplicable.

## Markdown report

```markdown
# Paper Project Authenticity and Reproducibility Audit

## Executive summary
- Project: ...
- Manuscript: ...
- Audit date: ...
- Audit mode: FAST | STANDARD | FULL
- Execution budget/limits: ...
- Overall risk: LOW | MODERATE | HIGH | CRITICAL
- Claim coverage: PASS n / WARNING n / FAIL n / UNVERIFIABLE n
- Execution dispositions: EXECUTED n / SUPPORTED_WITHOUT_RERUN n / DEFERRED_BY_MODE n / BLOCKED n
- Highest reproduction tier achieved: R0-R4
- Bottom line: 2-5 sentences

## Scope and limitations
- Root inspected: ...
- Excluded/unreadable material: ...
- Selected audit mode: ...
- Execution constraints/budget: ...
- Network/downloads used: ...
- Hardware/backend: ...

## Project inventory
Summarize manuscript, code, configs, data, checkpoints, logs, results, table/figure generators, archives, and unusual files. Link to `inventory.json`.

## Manuscript claim ledger
| ID | Manuscript location | Claim / expected result | Required evidence |
|---|---|---|---|

## Paper-to-code consistency
For methods, data/splits, model, training, evaluation, metrics, statistics, baselines, and ablations, give exact source locations and discrepancies.

## Execution strategy
Explain why expensive runs were selected or deferred and which anomalies triggered escalation.

## Execution record
| Run ID | Purpose | Command/config | Exit | Produced artifacts | Reproduction tier |
|---|---|---|---|---|---|

## Result reproduction
| Claim ID | Paper value | Supplied artifact | Regenerated/observed value | Difference | Tier | Disposition | Status | Evidence |
|---|---:|---:|---:|---:|---|---|---|---|

## Claim-evidence matrix
| Claim ID | Code path | Config | Raw artifact | Final generator | Status | Reason |
|---|---|---|---|---|---|---|

## Authenticity / integrity findings
For each finding include:
- Severity: INFO | LOW | MEDIUM | HIGH | CRITICAL
- Status: PASS | WARNING | FAIL | UNVERIFIABLE
- Evidence: exact files/lines/cells/commands/artifacts
- Why it matters
- Plausible benign explanation, if any
- What would resolve the issue

## Data leakage and split checks
...

## Statistical and seed checks
...

## Missing or unverifiable components
...

## Overall assessment
Explain why the risk rating follows from the central claims. Separate reproducibility failure from evidence of manual result injection or other integrity concerns.

## Evidence index
List logs, hashes, generated artifacts, `static_risks.json`, and comparison reports.
```

## JSON report

Use this top-level structure:

```json
{
  "schema_version": "1.1",
  "project_root": "...",
  "audit_mode": "FAST|STANDARD|FULL",
  "execution_budget": {"max_wall_time": null, "max_gpu_hours": null, "max_training_runs": null},
  "manuscript": {"path": "...", "title": "...", "version_notes": "..."},
  "overall_risk": "LOW|MODERATE|HIGH|CRITICAL",
  "highest_reproduction_tier": "R0|R1|R2|R3|R4",
  "summary": "...",
  "limitations": [],
  "environment": {
    "runtime": {},
    "hardware": {},
    "network_used": false,
    "downloads": [],
    "dependency_deviations": []
  },
  "claims": [
    {
      "id": "TAB-01-R1",
      "manuscript_location": "...",
      "claim": "...",
      "expected": null,
      "observed": null,
      "difference": null,
      "status": "PASS|WARNING|FAIL|UNVERIFIABLE",
      "reproduction_tier": "R0|R1|R2|R3|R4",
      "execution_disposition": "EXECUTED|SUPPORTED_WITHOUT_RERUN|DEFERRED_BY_MODE|BLOCKED",
      "code_locations": [],
      "configs": [],
      "inputs": [],
      "raw_artifacts": [],
      "final_generators": [],
      "run_ids": [],
      "evidence": [],
      "notes": ""
    }
  ],
  "runs": [
    {
      "id": "RUN-001",
      "purpose": "...",
      "argv": [],
      "cwd": "...",
      "exit_code": 0,
      "log": "...",
      "artifacts": []
    }
  ],
  "findings": [
    {
      "id": "F-001",
      "severity": "INFO|LOW|MEDIUM|HIGH|CRITICAL",
      "status": "PASS|WARNING|FAIL|UNVERIFIABLE",
      "category": "...",
      "title": "...",
      "evidence": [],
      "impact": "...",
      "benign_explanation": "...",
      "resolution": "..."
    }
  ],
  "coverage": {"pass": 0, "warning": 0, "fail": 0, "unverifiable": 0},
  "execution_dispositions": {"executed": 0, "supported_without_rerun": 0, "deferred_by_mode": 0, "blocked": 0},
  "evidence_index": []
}
```

## Reporting rules

- Prefer exact evidence locations over generic prose.
- Never hide failed commands; include them in the execution record.
- Report every material deviation introduced by the auditor.
- Keep generated audit files outside the original project.
- If a status is disputed or uncertain, use WARNING/UNVERIFIABLE and explain why.
- Do not infer intent from an anomaly.
- Never use a PASS label or LOW risk rating as shorthand for full end-to-end reproduction; state the achieved tier and selected audit mode explicitly.
- List expensive runs intentionally deferred by mode/budget so the user can later request targeted escalation or FULL mode.
