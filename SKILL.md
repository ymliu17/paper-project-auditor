---
name: paper-project-auditor
description: Audit a research-paper project directory for authenticity, internal consistency, provenance, and computational reproducibility. Use when an agent is given a local project/repository path and must inspect the complete file tree, identify the manuscript and supplementary material, verify that methods/data/splits/models/hyperparameters/metrics in code match the paper, safely test the submitted workflow, trace every major quantitative claim to code and artifacts, selectively reproduce results according to cost and risk, and detect missing experiments, hard-coded or manually injected results, stale/precomputed outputs, data leakage, cherry-picking, seed/statistics problems, provenance gaps, or other evidence that weakens confidence in the reported results.
---

# Paper Project Auditor

Audit the project as an evidence-tracing and reproduction task, not as a code-style review. Establish whether the submitted files genuinely implement the study described by the manuscript and whether they can produce the reported results.

## Non-negotiable principles

- Treat the supplied project as untrusted code. Perform static safety inspection before executing anything.
- Preserve the original project. Never edit, delete, rename, reformat, or overwrite source files or supplied results.
- Create an isolated working copy or temporary workspace for all execution and generated artifacts.
- Inventory the entire directory before deciding what matters. Do not inspect only obvious Python files.
- Distinguish evidence from inference. Never call a result reproduced merely because code looks plausible.
- Distinguish `PASS`, `WARNING`, `FAIL`, and `UNVERIFIABLE` exactly as defined in `references/audit-checklist.md`.
- Treat timestamps, filenames, comments, README claims, and screenshots as weak evidence unless corroborated by executable provenance.
- Do not silently install packages, download data/models, enable network access, or change hardware/backend. Record each such action when it is necessary for reproduction.
- Prefer declared environments and lockfiles. Install missing dependencies only into an isolated environment, never system-wide.
- Use GPU only when available and materially required by the submitted workflow. Record device/model/backend and any CPU fallback.
- Never use private credentials or upload project data to third parties.
- Audit every major claim, but do not rerun every experiment by default. Separate audit coverage from execution coverage and use the selected audit mode to control computational cost.
- Never describe a claim as fully reproduced unless the achieved reproduction tier actually supports that statement.

## Required workflow

Follow all phases in order. Do not stop after a successful smoke test.

### Audit mode and execution budget

Determine the audit mode before expensive execution:

- **FAST**: complete inventory, manuscript/code/provenance audit, safety checks, and cheap R1/R2/R3 checks. Do not launch full-data training except when it is clearly trivial.
- **STANDARD**: default when the user does not specify a mode. Perform the complete static/provenance audit, cheap execution, evaluation/aggregation reproduction from supplied artifacts, and targeted end-to-end reruns selected by claim centrality and risk. Do not launch exhaustive seed, baseline, ablation, or hyperparameter sweeps.
- **FULL**: attempt all computationally attainable experiments and the paper-stated repeated-run protocol, subject to safety, available resources, and explicit user constraints.

The audit scope is always comprehensive: every major manuscript claim must be traced and assessed. The mode changes how much expensive computation is executed, not which claims are inspected.

In `STANDARD`, prefer evidence in this order before retraining: raw per-run outputs -> submitted aggregation -> checkpoints + submitted evaluation -> targeted training. Select targeted reruns to maximize information gain. Prioritize central claims, suspicious provenance, paper/code mismatches, numeric discrepancies, leakage concerns, duplicate artifacts, or questionable seed/statistical reporting.

Treat a command as expensive in `STANDARD` when it is a multi-seed/sweep job, a full baseline/ablation grid, a full-data training run that existing logs/docs suggest is long-running, or a training command whose cost is unknown but clearly nontrivial. Do not automatically launch such a command solely to increase reproduction tier. If no user budget is supplied, use a soft guardrail of about 30 minutes for any single targeted run and about 1 GPU-hour total; when cost cannot be estimated reliably, prefer the cheaper evidentiary path. Record deferred runs as `DEFERRED_BY_MODE`, not as executed failures.

User-specified limits such as maximum wall time, GPU-hours, number of runs, or selected claims override these default cost guardrails without weakening safety rules.

### Phase 1: Preserve and inventory

1. Resolve the user-provided project path and verify that it exists.
2. Record the root path, filesystem metadata, and whether `.git` history is present.
3. Run `scripts/inventory_project.py <root> --output <audit-dir>/inventory.json`.
4. Review the complete inventory, including unusual extensions, symlinks, archives, hidden files, generated outputs, notebooks, binaries, checkpoints, and large files.
5. Identify likely roles:
   - manuscript and supplementary material;
   - source code and notebooks;
   - configs, launchers, workflows, Makefiles, containers, lockfiles;
   - raw/intermediate/processed data and split definitions;
   - pretrained models/checkpoints;
   - logs, metrics, tables, figures, result bundles;
   - scripts that aggregate, format, or plot final results.
6. Create a writable audit workspace outside the original tree. Copy only what is needed for execution while preserving relative paths. Record SHA-256 hashes of original inputs whenever practical.

If the project contains archives, inspect their member lists and extract copies only into the audit workspace. Do not execute from archives.

### Phase 2: Identify and read the manuscript

Identify the primary manuscript from PDF, DOCX, LaTeX, Markdown, or other source. If multiple candidates exist, use title/author/content consistency and build files to determine the submitted version; record ambiguity rather than guessing.

Extract a structured claim ledger containing at least:

- datasets, cohorts, inclusion/exclusion criteria, preprocessing, augmentation;
- train/validation/test split policy and sample counts;
- model architecture and initialization/pretraining;
- losses, optimizers, schedulers, epochs/steps, batch size, learning rate, regularization;
- random seeds and repeated-run protocol;
- evaluation metrics and exact definitions;
- baselines, ablations, variants, statistical tests, confidence intervals;
- every main table, figure, headline metric, comparison, and claimed improvement;
- supplementary experiments needed to support main conclusions.

Assign stable IDs such as `MTH-01`, `TAB-02-R3`, `FIG-04`, `CLM-07` so later evidence can point back to exact claims.

### Phase 3: Static code and provenance audit

Before execution:

1. Run `scripts/scan_code_risks.py <root> --output <audit-dir>/static_risks.json`.
2. Inspect entrypoints, shell scripts, subprocess usage, file deletion/mutation, network calls, dynamic code loading, external downloads, package installation, and credential access.
3. Do not execute unsafe or destructive paths unless they can be neutralized in an isolated environment without weakening the audit.
4. Build a paper-to-code mapping for every method and result claim. For each claim, identify the exact config, function/class, dataset/split, command/entrypoint, raw output, aggregation step, and final table/figure generator.
5. Check that paper settings match the settings actually selected by launch scripts/configs/defaults. Inspect config precedence and CLI overrides rather than reading only default values.
6. Inspect notebooks for hidden state, out-of-order execution, manually edited outputs, or cells that consume precomputed results.
7. Trace final tables/figures backwards. Flag manual spreadsheets, literal metric arrays, copied values, or plotting scripts that do not derive numbers from raw experiment artifacts.
8. If git history exists, use it only as supplementary provenance: inspect tracked/untracked status, relevant commits/tags, and whether result/code relationships are plausible. Never treat git metadata alone as proof of authenticity.

Consult `references/audit-checklist.md` for the full static checklist.

### Phase 4: Environment reconstruction

1. Determine the intended environment from files such as `pyproject.toml`, `requirements*.txt`, lockfiles, `environment.yml`, Dockerfiles, R/MATLAB metadata, README commands, CI workflows, or manuscript supplements.
2. Record language/runtime versions and relevant hardware/backend information.
3. Prefer an existing valid isolated environment if supplied. Otherwise create a fresh isolated environment.
4. Reproduce declared versions where feasible. Record every deviation.
5. Do not use undeclared local packages, user site-packages, cached private modules, or hidden datasets without explicitly reporting them.
6. If network access or downloads are essential, record URL/source, version/identifier, hash when feasible, and which claim depends on that download.

### Phase 5: Smoke tests before expensive runs

Run the cheapest meaningful checks first:

- imports and CLI help;
- configuration parsing;
- unit/integration tests if present;
- one-batch or tiny-subset train/eval pass where valid;
- checkpoint loading;
- metric computation on controlled synthetic examples;
- result aggregation/plotting from supplied raw logs.

Use `scripts/run_capture.py` for commands whenever practical so exit status, stdout/stderr, duration, environment markers, and created/modified/deleted files are logged.

A smoke-test pass only proves executability of that path. It does not prove paper results.

### Phase 6: Risk-driven result reproduction

Reproduce results according to the selected audit mode and the evidence already available. Do not equate comprehensive auditing with exhaustive retraining.

For every table/figure/metric, first trace the strongest existing provenance chain. Then choose the cheapest execution that can materially increase confidence:

1. Regenerate deterministic aggregation, statistics, tables, and figures from supplied raw per-run/per-example artifacts when available.
2. Re-run submitted evaluation from supplied checkpoints when available, and compare regenerated metrics with both raw artifacts and manuscript values.
3. Use targeted end-to-end training only when it adds material evidence. In `STANDARD`, normally select at most one representative run/seed per major experiment family and only a small number of high-value baselines or ablations. Do not run all seeds merely to verify that a multi-seed result file exists; instead recompute its reported statistics from the submitted individual runs and inspect seed provenance.
4. Escalate targeted execution when a central claim has broken provenance, a regenerated value disagrees, code and paper settings differ materially, hard-coded/manual result injection is suspected, leakage/fairness concerns exist, or purportedly independent artifacts look duplicated or selectively chosen.
5. Escalate to exhaustive reruns only in `FULL` mode, when the user explicitly requests them, or when the remaining high-risk question cannot be resolved with cheaper evidence and the required execution fits the user-provided budget.
6. Use the submitted command/config path rather than constructing a replacement implementation that merely resembles the paper.
7. Capture the exact command, working directory, environment, seed, input identifiers/hashes, checkpoint, logs, and generated artifacts for every executed run.
8. Compare regenerated values with manuscript values and supplied result files using `references/execution-policy.md`. Use `scripts/compare_results.py` for matching machine-readable artifacts when useful, but inspect semantic alignment rather than trusting positional equality alone.

For skipped expensive runs, record the reason and the strongest achieved reproduction tier. A claim may be strongly supported by provenance and lower-tier execution without being end-to-end reproduced; state this distinction explicitly. Never label a supplied final CSV/JSON/table as regenerated evidence unless the submitted pipeline actually recreated it.

### Phase 7: Authenticity and integrity checks

Actively test for explanations that can make a project look reproducible without actually supporting the paper:

- hard-coded headline metrics or arrays used to render tables/figures;
- manually edited CSV/JSON/Excel results with no raw-run provenance;
- dead training code while evaluation loads unrelated precomputed outputs;
- scripts that copy bundled expected results rather than compute them;
- mismatched dataset versions, sample counts, labels, folds, or split files;
- train/test overlap, subject leakage, duplicate samples, temporal leakage, normalization fitted on test data, or tuning on the final test set;
- incorrect metric definitions, averaging, thresholding, class weighting, sign/direction, unit conversion, or denominator;
- defaults/config overrides that differ from the manuscript;
- missing baselines/ablations or incomplete result rows;
- selective seeds/runs, best-checkpoint selection inconsistent with the paper, or post-hoc cherry-picking;
- reported variance/statistical tests not reproducible from individual runs;
- checkpoints incompatible with claimed architecture/config;
- final plots/tables that cannot be regenerated from raw artifacts;
- duplicated or suspiciously reused result artifacts across supposedly different conditions;
- stale outputs whose provenance cannot be connected to current code/config;
- undocumented external files, private data, manual steps, or secret parameters required for success.

Treat anomalies as evidence requiring explanation, not automatic proof of misconduct. State benign alternatives where plausible.

### Phase 8: Coverage audit

Create a claim-evidence matrix. Every major manuscript claim must end in one of:

- `PASS`: direct evidence supports the claim at the verification depth required by the selected audit mode; report the achieved reproduction tier and never imply R4 if only R0-R3 was achieved;
- `WARNING`: broadly supported but with a material caveat, deferred higher-tier execution, ambiguity, fragility, or undocumented deviation that does not overturn the claim;
- `FAIL`: direct evidence contradicts the claim, a required project path fails for a project-attributable reason, or regenerated values materially disagree;
- `UNVERIFIABLE`: the truth cannot be determined because required data, dependency, credential, hardware, license, or indispensable artifact is unavailable.

Also assign an execution disposition to each material claim: `EXECUTED`, `SUPPORTED_WITHOUT_RERUN`, `DEFERRED_BY_MODE`, or `BLOCKED`. A deliberate `STANDARD`-mode deferral is not itself a failure.

Compute coverage counts, but do not collapse the audit into a single numeric score. Give an overall risk rating of `LOW`, `MODERATE`, `HIGH`, or `CRITICAL` based on the severity and centrality of findings, not merely the number of warnings.

### Phase 9: Report

Produce:

1. a concise chat summary;
2. `<audit-dir>/audit_report.md` following `references/report-schema.md`;
3. `<audit-dir>/audit_report.json` following the machine-readable structure in the same reference;
4. logs and intermediate evidence files in `<audit-dir>/evidence/`.

The report must include exact file paths and line/cell/config locations when available, manuscript page/section/table/figure references when available, commands executed, exit codes, artifact paths/hashes, numeric expected-vs-observed differences, and a clear statement of what was not checked.

Do not use accusatory language such as "fraud" or "fabrication" unless the evidence independently establishes that conclusion. Prefer precise descriptions such as "hard-coded reported value", "no executable provenance found", "result not reproduced", or "data split contains overlap".

## Resource usage

- `scripts/inventory_project.py`: complete project inventory, role hints, file hashes, sizes, and symlinks.
- `scripts/scan_code_risks.py`: heuristic static scan for destructive/external execution and possible manually embedded result values. Treat findings as leads, not verdicts.
- `scripts/run_capture.py`: execute one command without a shell and capture reproducibility metadata plus filesystem changes.
- `scripts/compare_results.py`: compare matching JSON/CSV/TSV/NPY/NPZ/text result artifacts with numeric tolerances.
- `references/audit-checklist.md`: detailed methodological, statistical, provenance, leakage, and result-integrity checks.
- `references/execution-policy.md`: audit modes, cost-aware execution rules, reproduction tiers, safe-execution rules, and comparison tolerances.
- `references/report-schema.md`: mandatory Markdown and JSON report formats.
