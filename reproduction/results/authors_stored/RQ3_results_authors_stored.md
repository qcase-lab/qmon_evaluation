# QMON RQ3 reproduction: results for mutant set `authors_stored`

Every value below is computed by `reproduction/step06_aggregate.py` from CSV files in `reproduction/data/`. Each table is followed by a **provenance chain**: the line of the authors' code that made the per-checkpoint/per-mutant decision, the line that wrote it into a record, the line that copied it into our CSV, and the line in step06 that summarised it. Line numbers are looked up when this report is generated.

## Population

| Quantity | Value | Where it comes from |
|---|---:|---|
| Mutation attempts | 3,570 | 238 circuits × 5 seeds × 3; drawn at src/rq3_manifest.py:337–src/rq3_manifest.py:338, replaced by src/mutation.py:121 |
| Output-equivalent (excluded, not scored) | 710 | L1 < 1e-9 at src/rq3_manifest.py:351; skipped at src/rq3_realexec_eval.py:2792; dropped at reproduction/step06_aggregate.py:114 |
| Non-output-equivalent mutants (= positives) | 2,860 | |
| Complete for every method (rate denominator) | 2,860 | reproduction/step06_aggregate.py:120 |
| Candidate-covered | 2,217 | mutated gate in the cone of ≥1 Algorithm-1 candidate: src/rq3_realexec_eval.py:584; filtered at reproduction/step06_aggregate.py:122 |
| Deployment-covered | 2,206 | same test on deployed checkpoints only |
| Deployment gaps | 11 | candidate-covered but not deployment-covered |
| Correct circuits in the false-alarm arm (= negatives) | 238 | `rq3_false_alarms_authors_stored.csv` |
| Methods with per-record results | qmon, qmon_pernode, statistical, proq, liu, mqt | |

## Table III: detection, localization precision, false alarms

Rates: mean ± sample SD of the per-seed rates; pooled counts in parentheses.

| Method | Detection | Candidate-covered detection | Localization precision | False alarms | Paper (detection / covered / loc / FA) |
|---|---|---|---|---|---|
| QMON (batched) | 62.4 ± 5.4% (1,782/2,860) | 80.0 ± 3.9% (1,774/2,217) | 0.522 ± 0.126 | 0.8% (2/238) | 62.4 ± 5.4% (1,782) / 80.0 ± 3.9% (1,774) / 0.522 ± 0.126 / 0.8% |
| QMON (independent per-checkpoint ablation) | 67.2 ± 4.5% (1,921/2,860) | 86.4 ± 1.6% (1,916/2,217) | 0.496 ± 0.127 | 0.8% (2/238) | 67.2 ± 4.5% (1,921) / 86.4 ± 1.6% (1,916) / 0.496 ± 0.127 / 0.8% |
| Statistical assertion | 67.4 ± 4.4% (1,928/2,860) | 86.7 ± 1.6% (1,924/2,217) | 0.494 ± 0.126 | 0.0% (0/238) | 67.4 ± 4.4% (1,928) / 86.7 ± 1.6% (1,924) / 0.494 ± 0.126 / 0.0% |
| Projection assertion (Proq) | 71.1 ± 4.2% (2,031/2,860) | 91.6 ± 1.0% (2,031/2,217) | 0.500 ± 0.130 | 0.0% (0/238) | 71.1 ± 4.2% (2,031) / 91.6 ± 1.0% (2,031) / 0.500 ± 0.130 / 0.0% |
| Dynamic ancilla (Liu et al.) | 71.3 ± 4.4% (2,036/2,860) | 91.9 ± 0.8% (2,036/2,217) | 0.501 ± 0.131 | 0.0% (0/238) | 71.3 ± 4.4% (2,036) / 91.9 ± 0.8% (2,036) / 0.501 ± 0.131 / 0.0% |
| MQT debugger (combined flag) | 59.2 ± 6.2% (1,688/2,860) | 76.1 ± 4.0% (1,688/2,217) | 0.476 ± 0.122 | not measured | 59.2 ± 6.2% (1,688) / 76.1 ± 4.0% (1,688) / 0.476 ± 0.122 / – |

**Differences from the published Table III:** none.

**Differences from the authors' printed summary (results/rq3/rq3_aggregate.txt):** QMON (independent per-checkpoint ablation): candidate-covered detected = 1,916 here vs 1,915 in rq3_aggregate.txt.

**Provenance chain, column by column**

- **Detection.** For one mutant and one method, `scan_method` (src/rq3_realexec_eval.py:2415) visits the method's checkpoints in gate order and returns at the first flag (src/rq3_realexec_eval.py:2549). The flag rule per method: QMON reads come from the instrumented batch simulation (src/rq3_realexec_eval.py:1948) and are tested by `qmon_count_flag` (src/rq3_realexec_eval.py:2347): any contrary shot for a deterministic expectation (src/rq3_realexec_eval.py:2354), otherwise exact binomial p < α/K_qmon (src/rq3_realexec_eval.py:2359, Bonferroni at src/rq3_realexec_eval.py:2468). Independent QMON samples the raw mutant marginal instead (src/rq3_realexec_eval.py:2476). Statistical: `run_statistical` (src/rq3_realexec_eval.py:1624; unaffected checkpoints src/rq3_realexec_eval.py:2394). Projection: `run_proq` (src/rq3_realexec_eval.py:1652). Dynamic ancilla: `run_liu` (src/rq3_realexec_eval.py:1678). MQT: mismatch or refusal flags (src/rq3_realexec_eval.py:2540). Unaffected checkpoints use the evaluation-only shortcut decided at src/rq3_realexec_eval.py:2458. The boolean is stored as `detected` at src/rq3_realexec_eval.py:2814, copied to column `detected` of `rq3_method_results_authors_stored.csv` at reproduction/records.py:64 (rows read from results/rq3/rq3_mutant.pkl at reproduction/extract_authors_results.py:125), averaged per seed at reproduction/step06_aggregate.py:142 and summarised at reproduction/step06_aggregate.py:143 (SD at reproduction/step06_aggregate.py:62); pooled count at reproduction/step06_aggregate.py:144. Authors' equivalent: src/rq3_realexec_eval.py:3309 with ms() at src/rq3_realexec_eval.py:3251.
- **Candidate-covered detection.** Same `detected` values restricted to `in_scope_full` (src/rq3_realexec_eval.py:584 → reproduction/records.py:45) at reproduction/step06_aggregate.py:147. Authors: src/rq3_realexec_eval.py:3312.
- **Localization precision.** The suspect region is the cone of the first flagged checkpoint (src/rq3_realexec_eval.py:2805; cones from src/rq3_realexec_eval.py:1462); precision = 1/|cone| if the mutated gate is in it else 0 (src/rq3_realexec_eval.py:2817); CSV column `loc_precision` (reproduction/records.py:68); per-seed mean over detected mutants at reproduction/step06_aggregate.py:159. Authors: src/rq3_realexec_eval.py:3317.
- **False alarms.** `false_alarm_circuit` (src/rq3_realexec_eval.py:2839) scans every checkpoint of the correct circuit, counts flags (src/rq3_realexec_eval.py:2919) and sets `false_alarm = n_flagged > 0` (src/rq3_realexec_eval.py:2958); MQT is not evaluated (src/rq3_realexec_eval.py:2915). CSV column `false_alarm` (reproduction/records.py:90); share of circuits at reproduction/step06_aggregate.py:181. Authors: src/rq3_realexec_eval.py:3325.

## False negatives and false positives

Positives are the non-output-equivalent mutants (a bug is present); negatives are the 238 unmutated circuits (no bug). The two populations come from separate experiments, so a precision value (TP/(TP+FP)) would mix them and is not reported. Output-equivalent mutants are neither positives nor negatives: they are dropped.

| Method | TP (detected) | FN (missed) | FN rate, pooled | FN rate, seed mean ± SD | FP (flagged correct circuits) | TN | FP rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| QMON (batched) | 1,782 | 1,078 | 37.7% | 37.6 ± 5.4% | 2 | 236 | 0.8% |
| QMON (independent per-checkpoint ablation) | 1,921 | 939 | 32.8% | 32.8 ± 4.5% | 2 | 236 | 0.8% |
| Statistical assertion | 1,928 | 932 | 32.6% | 32.6 ± 4.4% | 0 | 238 | 0.0% |
| Projection assertion (Proq) | 2,031 | 829 | 29.0% | 28.9 ± 4.2% | 0 | 238 | 0.0% |
| Dynamic ancilla (Liu et al.) | 2,036 | 824 | 28.8% | 28.7 ± 4.4% | 0 | 238 | 0.0% |
| MQT debugger (combined flag) | 1,688 | 1,172 | 41.0% | 40.8 ± 6.2% | n/a | n/a | n/a |

Provenance: FN = mutants with `detected = false` (reproduction/step06_aggregate.py:154); the seed-level FN rate is 100 − the per-seed detection rate (reproduction/step06_aggregate.py:152), so its SD equals the detection SD. FP/TN come from the false-alarm column above. Table assembled at reproduction/step06_aggregate.py:204.

## Table IV: planned runs for a complete checkpoint scan (per circuit)

| Plan | Unit | Median | 75th pct (nearest rank) | Mean | Max | Paper (median / P75 / mean) |
|---|---|---:|---:|---:|---:|---|
| B | batch runs (batched QMON) | 1 | 14 | 30.0 | 853 | 1 / 14 / 30.0 |
| K_qmon | checkpoint reads (independent QMON) | 21 | 80 | 84.3 | 1,626 | 21 / 80 / 84.3 |
| K | circuit runs (separate-run assertions) | 21 | 89 | 92.1 | 1,626 | 21 / 89 / 92.1 |

Circuits whose QMON plan is a single batch: **125 / 238** (reproduction/step06_aggregate.py:231).

Provenance: B = number of batches from FFD + conditional ILP (src/batch_partition.py:439) stored at src/rq3_realexec_eval.py:1501; K_qmon = deployed checkpoints incl. free final reads (src/rq3_realexec_eval.py:1531); K = all Algorithm-1 candidates (src/rq3_realexec_eval.py:1451, selector src/fast_analysis.py:11). Copied per mutant at reproduction/records.py:44; one value per unique circuit at reproduction/step06_aggregate.py:220. Authors: src/rq3_realexec_eval.py:3198.

## Table V: where QMON misses come from

| Dimension | Stratum | Misses / attempts | Pooled rate | Seed rate (mean ± SD) | Share of misses |
|---|---|---:|---:|---:|---:|
| overall | all non-output-equivalent mutants | 1,078/2,860 | 37.7% (Wilson 95%: 35.9–39.5%) | 37.6 ± 5.4% | 100.0% |
| circuit family | qnn | 104/120 | 86.7% | 86.7 ± 8.0% | 9.6% |
| circuit family | portfolioqaoa | 95/120 | 79.2% | 79.2 ± 11.0% | 8.8% |
| circuit family | su2random | 81/120 | 67.5% | 67.5 ± 17.8% | 7.5% |
| circuit family | portfoliovqe | 80/120 | 66.7% | 66.7 ± 17.7% | 7.4% |
| circuit family | twolocalrandom | 80/120 | 66.7% | 66.7 ± 17.7% | 7.4% |
| circuit family | realamprandom | 79/120 | 65.8% | 65.8 ± 18.7% | 7.3% |
| mutation operation | cx->rzx | 140/237 | 59.1% | 62.4 ± 13.7%† | 13.0% |
| mutation operation | cx->cp | 127/144 | 88.2% | 92.7 ± 8.5% | 11.8% |
| mutation operation | cx->cz | 110/124 | 88.7% | 87.2 ± 11.0% | 10.2% |
| mutation operation | cx->rzz | 87/108 | 80.6% | 77.9 ± 7.5%† | 8.1% |
| original gate arity | two-qubit | 886/1,250 | 70.9% | 72.6 ± 8.9% | 82.2% |
| original gate arity | one-qubit | 192/1,610 | 11.9% | 11.9 ± 4.2% | 17.8% |
| monitoring coverage | not candidate-covered | 635/643 | 98.8% | 98.8 ± 1.0% | 58.9% |
| monitoring coverage | deployment-covered | 432/2,206 | 19.6% | 19.6 ± 3.9% | 40.1% |
| monitoring coverage | deployment gap | 11/11 | 100.0% | 100.0 ± 0.0%† | 1.0% |

† sparse: fewer than 20 attempts or not represented in every seed (rq3_miss_analysis rule).

Provenance: a miss is `detected = false` for QMON; strata rates at reproduction/step06_aggregate.py:249; authors' version src/rq3_miss_analysis.py:169 and src/rq3_miss_analysis.py:242.

### QMON miss breakdown

| Category | Count |
|---|---:|
| outside candidate scope (no affected numerical candidate) | 635 |
| deployment gap (affected candidate not deployed at Qmax=24) | 11 |
| deployment-covered, missed by every method | 87 |
| deployment-covered, caught by another method | 345 |
| total QMON misses | 1078 |

Rule for 'missed by every method': no method incl. the per-checkpoint ablation flags it (aggregate() rule). Computed at reproduction/step06_aggregate.py:279.

### Why deployment-covered misses happen (authors' exact-probability diagnosis)

| Mechanism | Count | Share |
|---|---:|---:|
| no_raw_deployed_z_signal | 262 | 60.6% |
| raw_signal_fully_erased_by_batch_channel | 138 | 31.9% |
| batch_signal_present_but_realized_test_missed | 32 | 7.4% |
| ablation flags (of all deployment-covered misses) | 143 |  |
| ablation flags with correct cone | 141 |  |
| erased-by-replay misses the ablation catches | 136 |  |

Provenance: categories assigned at reproduction/extract_authors_results.py:183 from results/rq3/rq3_deployed_miss_diagnosis.json; counted at reproduction/step06_aggregate.py:321. The script that produced that JSON is not in the authors' package.

## MQT combined-flag composition

| Outcome | Count | Seed rate (mean ± SD) |
|---|---:|---:|
| evaluated state mismatch | 534 | 18.7 ± 6.8% |
| unevaluable / refusal | 1,154 | 40.4 ± 6.6% |
| combined flag | 1,688 | 59.2 ± 6.2% |

Provenance: per-mutant counters `run_fail` / `run_unevaluable` from the MQT scan (src/rq3_realexec_eval.py:2540) → reproduction/records.py:71; per-seed rates at reproduction/step06_aggregate.py:307. Authors: src/mqt_diagnostics.py:74.

## Data lineage

```
quantum_circuits/*.qasm ── step01 (load) ── step02 (Alg.1 candidates, Alg.2 cones, Qmax=24 plan)
inputs/rq3_single_error_manifest.json ── step03 (mutants; seeds 1-5, or new seeds)
step04: rq3_realexec_eval.evaluate_circuit per circuit ──> data/rq3_mutants_<tag>.csv
                                                       └─> data/rq3_method_results_<tag>.csv
step05: rq3_realexec_eval.false_alarm_circuit per circuit ─> data/rq3_false_alarms_<tag>.csv
extract_authors_results.py: results/rq3/* ──> the same CSVs with tag authors_stored
step06 (this report) ──> results/<tag>/*.csv + this file
```
