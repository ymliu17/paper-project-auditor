# Execution and Reproduction Policy

## 1. Treat submitted code as untrusted

Static-inspect launchers and transitive helpers before execution. Look for deletion, filesystem traversal, shell execution, network transfer, credential access, package installers, privilege changes, background processes, and dynamic downloads/imports.

Prefer a container or disposable isolated environment. Keep the original project read-only. Do not mount unrelated user directories or credentials into the execution environment.

If isolation cannot safely contain a suspicious command, do not run it. Record the affected claim as UNVERIFIABLE or FAIL depending on whether the unsafe behavior itself contradicts the submitted workflow.

## 2. Network and downloads

Default to no network during execution when the project is self-contained. If declared public dependencies, datasets, or model weights are required:

- use only documented/official sources when possible;
- record the source URL or package index, exact version/identifier, and hash when practical;
- place downloads in the audit workspace/cache, not the original project;
- never provide private credentials or transmit project content outward;
- state which results rely on externally retrieved material.

A result that depends on an unversioned mutable external resource deserves at least a WARNING.


## 3. Audit modes and cost control

The selected mode controls execution depth, not inspection depth.

### FAST

Perform full file/manuscript/provenance inspection plus cheap execution. Prefer imports, tests, tiny batches, checkpoint loading, metric sanity checks, and deterministic regeneration from existing raw results. Do not run nontrivial full-data training.

### STANDARD (default)

Perform everything in FAST, then maximize confidence per unit cost:

- regenerate all cheap deterministic aggregations/tables/figures that have usable raw inputs;
- rerun evaluation from supplied checkpoints when practical;
- recompute reported multi-seed statistics from individual submitted runs;
- run targeted training for representative or suspicious experiment families rather than exhaustive sweeps;
- normally avoid all-seed, all-baseline, all-ablation, or hyperparameter-grid execution;
- escalate execution when lower-tier evidence exposes a discrepancy or broken provenance.

Unless the user provides another budget, treat a single run expected to exceed roughly 30 minutes, a total audit expected to exceed roughly 1 GPU-hour, any multi-seed sweep, or any full baseline/ablation grid as an expensive boundary. These are soft guardrails, not claims about exact runtime. If cost is uncertain and the command is clearly nontrivial training, defer it rather than launching it automatically.

### FULL

Attempt all computationally attainable paper experiments, including the stated repeated-run protocol, baselines, and ablations needed to reproduce reported aggregates. Still obey safety constraints and user resource limits.

For all modes, accept explicit limits such as `max_wall_time`, `max_gpu_hours`, `max_training_runs`, selected claim IDs, or a user request to avoid downloads. Record actual execution against those limits.

Use the following execution dispositions:

- `EXECUTED`: the relevant command was run during the audit;
- `SUPPORTED_WITHOUT_RERUN`: direct provenance/artifact evidence supports the claim without a new expensive run;
- `DEFERRED_BY_MODE`: a higher-cost run was intentionally not launched under the selected mode/budget;
- `BLOCKED`: execution could not proceed because a required resource or safe path was unavailable.

## 4. Dependency installation

Prefer, in order:

1. supplied container/environment;
2. lockfile-based fresh isolated environment;
3. pinned requirements;
4. best-effort reconstruction from declared minimum versions.

Never install system-wide merely to make the project pass. Record any manual package/version substitution.

## 5. Reproduction tiers

Use the strongest feasible tier for each claim and report the tier:

- **R0 Static trace only**: code/artifact inspection; no execution.
- **R1 Executability**: imports/tests/small smoke path runs.
- **R2 Evaluation reproduction**: supplied checkpoint + submitted evaluation code regenerate metrics.
- **R3 Aggregation reproduction**: raw per-example/per-run outputs regenerate reported tables/figures/statistics.
- **R4 End-to-end reproduction**: training from legitimate inputs through evaluation and final report artifacts.

Do not call R1 or R3 "full reproduction". Always report the achieved tier separately from claim status. `PASS` under FAST/STANDARD means the available direct evidence meets that mode's required verification depth; it does not imply R4.

## 6. Command capture

For each meaningful execution record:

- exact argv and working directory;
- start/end time and duration;
- return code;
- stdout/stderr;
- relevant environment variables;
- runtime/framework versions when material;
- CPU/GPU/backend identifiers when material;
- config and seed;
- created/modified/deleted files;
- hashes or stable identifiers of key inputs/outputs.

Use `scripts/run_capture.py` when practical.

## 7. Numeric comparison policy

Select tolerance based on the manuscript's reporting precision and the experiment's expected determinism. Always report raw expected and observed values.

### Deterministic transforms and aggregation

Expect exact equality for integer counts, labels, sample membership, and deterministic text/config outputs. For floating-point deterministic aggregation, use a tight numerical tolerance such as `atol=1e-8`, `rtol=1e-6` unless the pipeline justifies another value.

### Rounded manuscript values

If the paper prints `d` decimal places, a regenerated underlying value should ordinarily round to the same printed value. A useful display-consistency threshold is approximately half a unit in the last reported place, while also checking relative error.

Examples:

- reported `0.87`: tolerance about `0.005` for display agreement;
- reported `87.3%`: tolerance about `0.05` percentage points for display agreement.

This is not a license to ignore stochastic discrepancies larger than the study's claimed uncertainty.

### Stochastic training

When exact reruns are not expected, compare the reproduced distribution with the paper's stated multi-run protocol:

- same number/type of seeds if feasible;
- central tendency;
- dispersion/CI;
- ranking and effect direction;
- whether differences are material relative to reported uncertainty.

Do not use a generous arbitrary tolerance to turn a failed stochastic result into PASS.

## 8. Expensive experiments

Estimate cost from configs/logs before launching and prefer the execution that provides the most information per unit cost.

In FAST, do not launch nontrivial full-data training. In STANDARD, do not exhaustively rerun seeds, baselines, ablations, or sweeps merely because they are computationally attainable. First use R2/R3 evidence, then targeted R4 where it can resolve a meaningful uncertainty. In FULL, execute the submitted full paths when resources and safety constraints allow.

If a run is skipped only because of the selected mode/budget, mark its disposition `DEFERRED_BY_MODE` and state the achieved lower-tier evidence. Use `UNVERIFIABLE` only when indispensable evidence/resources are unavailable such that the claim's truth cannot be determined. Do not imply successful end-to-end reproduction when R4 was not performed.

## 9. Failures

Classify failures by likely source:

- **project-attributable**: missing file, broken import under declared environment, invalid command, incompatible checkpoint/config, runtime bug -> usually FAIL;
- **audit-environment-attributable**: unavailable proprietary data, unsupported required hardware, inaccessible licensed dependency -> UNVERIFIABLE unless the project promised portability that is contradicted;
- **ambiguous**: investigate and report evidence; do not guess.

Capture the first actionable error and relevant traceback/log context.
