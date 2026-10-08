# Audit Checklist

Use this checklist as a coverage guardrail. Add domain-specific checks when the paper requires them.

## Status semantics

- **PASS**: Direct evidence supports the claim at the verification depth required by the selected audit mode. Always report the achieved reproduction tier; PASS does not imply R4 unless R4 was actually achieved.
- **WARNING**: Evidence mostly supports the claim, but a material caveat, ambiguity, fragility, deferred higher-tier check, or undocumented deviation remains.
- **FAIL**: Direct evidence contradicts the claim, a required submitted path fails for a project-attributable reason, a required experiment is absent, or regenerated values materially disagree.
- **UNVERIFIABLE**: The audit cannot determine correctness because indispensable evidence/resources are unavailable. Never treat this as PASS.

Track execution separately as `EXECUTED`, `SUPPORTED_WITHOUT_RERUN`, `DEFERRED_BY_MODE`, or `BLOCKED`.

## 1. Manuscript and version identity

- Identify manuscript title/version/date and supplementary material.
- Check whether source TeX/DOCX and rendered PDF agree on main tables and figures.
- Detect multiple manuscript/result versions and record which one the code appears to target.
- Record arXiv/venue identifiers only if present; do not use external versions as a substitute for the supplied manuscript without saying so.

## 2. Dataset and cohort

- Dataset name, release/version, acquisition source.
- Sample/subject counts at each stage.
- Inclusion/exclusion criteria.
- Label construction and label availability timing.
- Missing-data handling.
- Preprocessing order and fitted parameters.
- Augmentation and whether it is train-only.
- Unit conversion and normalization.
- Dataset-specific hidden conventions.

### Leakage checks

- Exact ID overlap across train/val/test.
- Duplicate-content overlap using hashes or stable features when feasible.
- Subject/patient/session leakage.
- Temporal leakage.
- Family/site/video/frame leakage where applicable.
- Feature extraction or normalization fitted using held-out data.
- Hyperparameter or threshold tuning on final test data.
- Test labels used by model selection, early stopping, or data cleaning.

## 3. Model and training

- Architecture and all material branches/layers.
- Input dimensionality/resolution/modalities.
- Initialization and pretrained weights.
- Frozen/unfrozen modules.
- Objective/loss terms and weights.
- Optimizer, learning rate, scheduler, warmup.
- Batch size, gradient accumulation, clipping.
- Epoch/step count and early stopping.
- Regularization/dropout/weight decay.
- Mixed precision, distributed training, deterministic settings.
- Seed propagation across Python/NumPy/framework/data workers.
- Checkpoint selection criterion.

## 4. Evaluation and metrics

- Exact metric formula and implementation.
- Macro/micro/weighted/sample averaging.
- Per-class vs pooled evaluation.
- Threshold selection and tie handling.
- Positive class definition and score direction.
- Handling of ignored/missing labels.
- Confidence interval/statistical test implementation.
- Unit/scaling/percentage conversion.
- Whether metric libraries changed semantics across versions.

Use controlled synthetic cases when a metric implementation is non-obvious.

## 5. Baselines, ablations, and fairness of comparison

- Every manuscript baseline has a runnable or traceable source.
- Hyperparameter tuning budget is comparable where claimed.
- Same data split and evaluation protocol are used.
- Ablations remove only the described component.
- No hidden extra data/pretraining is used by the proposed method unless disclosed.
- Result rows correspond to unique configs/checkpoints rather than relabeled duplicates.

## 6. Statistical reporting

- Number of runs/seeds matches the paper.
- Individual run values exist and can regenerate aggregate statistics.
- Mean/median/best-run convention matches the paper.
- Standard deviation vs standard error is correctly labeled.
- Confidence intervals and p-values can be recomputed.
- Multiple-comparison correction is implemented when claimed.
- Reported significant digits are supported by run variability.
- No selective omission of failed or low-performing runs without disclosure.

## 7. Result provenance

For every main result, seek a chain:

`manuscript claim -> final table/figure cell -> aggregation script -> raw metrics/log -> checkpoint/config -> training/evaluation command -> data/split`

Flag broken links in this chain.

Strong evidence includes newly generated raw outputs, deterministic aggregation, hashes/IDs, and matching configs. Weak evidence includes README prose, screenshots, manually copied spreadsheets, or a final PDF figure with no source data.

## 8. Hard-coding and manual injection

Inspect especially files named with `result`, `metric`, `table`, `figure`, `plot`, `report`, or `paper`.

Potential concerns:

- literal arrays/dicts of headline numbers;
- code paths that bypass evaluation and load expected values;
- final tables copied from constants;
- scripts that overwrite computed metrics with manuscript values;
- plotting from hand-entered arrays when raw logs should exist;
- precomputed files bundled without generation provenance.

Do not flag legitimate constants such as hyperparameters or axis ticks as result fabrication. Confirm semantic use.

## 9. Notebooks

- Execution counts are monotonic if relevant.
- Outputs correspond to current cell code.
- Hidden variables from earlier sessions are not required.
- Relative paths resolve in a clean kernel.
- Results are not manually embedded markdown values disconnected from computation.
- Restart-and-run-all succeeds when feasible.

## 10. Environment and dependency integrity

- Declared environment is complete enough to create.
- Lockfile and requirements do not materially disagree.
- Local editable/private dependencies are disclosed.
- Code does not silently depend on user-home files.
- CUDA/cuDNN/framework versions are compatible with claimed behavior.
- Random/deterministic backend settings are recorded.
- External model/data downloads are versioned or hashed where feasible.

## 11. Execution coverage

Track separately:

- selected audit mode and any user execution budget;
- import/parse success;
- smoke-test success;
- training success and whether it was targeted or exhaustive;
- evaluation success;
- aggregation success;
- final table/figure regeneration;
- numeric reproduction;
- execution disposition for each major claim;
- intentionally deferred expensive runs.

A later stage cannot retroactively prove an earlier stage. Example: successful plotting from bundled CSV does not prove training or evaluation.

## 12. Artifact consistency

- Checkpoint architecture keys/shapes match claimed model.
- Config embedded in checkpoint/log agrees with launch config.
- Multiple conditions do not point to the same checkpoint unexpectedly.
- Raw result sample counts match dataset split counts.
- Figure/table generators read the expected fresh artifacts.
- Duplicate hashes across purportedly different outputs are explained.
- Timestamps are used only as weak supporting evidence.

## 13. Missing and unreachable components

Flag:

- referenced scripts/configs/data absent from project;
- README commands that no longer exist;
- dead entrypoints;
- hard-coded absolute paths;
- unavailable private data or credentials;
- missing checkpoints needed for claimed evaluation;
- manuscript experiments with no corresponding config/result path.

## 14. Domain-specific extensions

Add checks appropriate to the paper, for example:

- medical imaging: patient-level splits, scanner/site confounding, preprocessing leakage;
- video/facial behavior: identity/video/subject leakage, frame-level duplicates;
- federated learning: client partitioning, aggregation weights, communication rounds, client sampling;
- semi-supervised learning: labeled/unlabeled contamination and pseudo-label generation;
- tracking: sequence protocol, detector source, public/private detections;
- NLP/LLMs: prompt templates, decoding parameters, contamination, API/model version;
- human studies: mapping between analysis code and reported participant exclusions/statistics.

## 15. Overall risk rating

Use judgment based on centrality:

- **LOW**: central claims are strongly supported at the selected audit depth; executed checks agree, provenance is coherent, and only minor documentation or portability issues remain. This rating does not by itself imply full R4 reproduction.
- **MODERATE**: main conclusions remain supported but notable gaps/deviations exist.
- **HIGH**: one or more central claims fail or cannot be traced/reproduced; serious leakage/provenance concerns may exist.
- **CRITICAL**: central results are contradicted by executable evidence, depend on undisclosed manual result injection, or the project systematically cannot support its headline claims.

Always list the specific findings that justify the rating.
