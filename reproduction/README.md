# QMON reproduction framework

This folder sits inside the authors' repository (`quantum_monitoring-main/reproduction/`). Every
script calls the authors' own functions from `src/` and writes plain CSV files. `step06` turns
those CSVs into the RQ3 tables and a Markdown report. Every number in that report names the line
of code that decided it, the line that saved it to a CSV, and the line that summarised it.

## Files

| File | Paper | What it does | Writes |
|---|---|---|---|
| `common.py` | – | Finds the repo, puts `src/` on the import path, CSV helpers, line-number lookup for provenance | – |
| `step01_load_circuits.py` | Sec. V-A | Loads the 310 MQT Bench QASM files and counts qubits, gates, locations, depth | `data/step01_circuits.csv` |
| `step02_alg1_alg2.py` | Alg. 1, Alg. 2, Alg. 3 | Algorithm 1 candidates, final-read exclusion, backward causal cones, Qmax=24 plan (K, K_qmon, B), RQ3 eligibility, per-stage timings | `data/step02_locations.csv`, `data/step02_plans.csv` |
| `step03_mutants.py` | Sec. VI-C-2, App. B-B(a,b) | The authors' 3,570 mutants (`--tag authors`) or new ones from the same generator (`--tag ours --seeds 6 7 8 9 10`) | `data/mutants_<tag>.json/.csv` |
| `step04_rq3_mutants.py` | App. B-A, B-B(c-h) | Runs QMON, the per-checkpoint ablation and the four baselines on every mutant (`rq3_realexec_eval.evaluate_circuit`) | `data/rq3_mutants_<tag>.csv`, `data/rq3_method_results_<tag>.csv`, `data/rq3_timing_<tag>.csv` |
| `step05_rq3_false_alarms.py` | App. B-B(i) | Runs every method on the 238 correct circuits (`false_alarm_circuit`) | `data/rq3_false_alarms_<tag>.csv` |
| `records.py` | – | Flattens the authors' record dicts into CSV rows (shared by steps 04/05 and the extractor) | – |
| `extract_authors_results.py` | – | Reads the authors' stored `results/rq3/*` files into the same CSV format (tag `authors_stored`) | `data/*_authors_stored.csv` |
| `step06_aggregate.py` | Tables III, IV, V, App. B-C | Detection, candidate-covered detection, localization precision, false alarms, TP/FN/FP/TN, planned runs, miss analysis, MQT composition | `results/<tag>/*.csv`, `results/<tag>/RQ3_results_<tag>.md` |

## Running it

Use WSL/Linux with the authors' pinned environment (`pip install -r requirements.txt`, Python 3.12).
Set `QMON_MILP_SOLVER=gurobi` to get the stored batch plans exactly. All commands run from the repo root.

```bash
export QMON_MILP_SOLVER=gurobi

python reproduction/step01_load_circuits.py
python reproduction/step02_alg1_alg2.py                 # all 310 circuits

# Reproduce the paper (seeds 1-5)
python reproduction/step03_mutants.py --tag authors
python reproduction/step04_rq3_mutants.py --tag authors          # long: hours to days; resumable
python reproduction/step05_rq3_false_alarms.py --tag reproduced
python reproduction/step06_aggregate.py --tag authors --fa-tag reproduced

# Our own mutants (same generator, new seeds)
python reproduction/step03_mutants.py --tag ours --seeds 6 7 8 9 10
python reproduction/step04_rq3_mutants.py --tag ours
python reproduction/step06_aggregate.py --tag ours --fa-tag reproduced

# The authors' stored results, without simulating anything (stdlib + numpy only)
python reproduction/extract_authors_results.py
python reproduction/step06_aggregate.py --tag authors_stored
```

Useful options for `step04`: `--methods qmon qmon_pernode statistical proq liu` (leave MQT for a
separate pass, as the authors did), `--shard 2/8` (split the 238 circuits across machines),
`--circuits <names>`, `--per-method-timing` (one evaluator call per method, giving wall-clock
time per method for the runtime contribution). It saves one file per circuit under `data/raw/<tag>/`
and skips finished circuits on restart.

## Notes

- **Seeds for our mutants.** The default is 6-10, giving five new seeds with no overlap. Seed 5 is
  one of the authors' seeds, so a 5-10 range would repeat 3 x 238 of their mutants.
- **`results/rq3/rq3_mutant.pkl` is a Git-LFS pointer** (134 bytes) in the zip download. Until the
  real 199 MB file is in place (`git lfs pull`, or download it from the GitHub file page), the
  extractor rebuilds QMON and MQT per-mutant results from the authors' JSON side files.
  The other columns (the ablation, the three assertion baselines, and every localization
  precision) are then copied from `rq3_aggregate.txt` and marked ᴾ in the report. Once the real
  file is there, rerun the two `authors_stored` commands: every cell is then recomputed from
  per-record data.
- **False alarms** use one fixed shot seed per circuit (the authors' function refuses any other), so
  the false-alarm arm is the same for every mutant set.
- **Our own mutant set.** The authors' artifact validators (`run_rq3_keys`, `--aggregate`) only
  accept the canonical manifest. That is why step04 calls `evaluate_circuit` directly and
  step06 re-implements `aggregate()` (with line references to the original). For seeds 1-5 the
  two routes give the same per-record results.
