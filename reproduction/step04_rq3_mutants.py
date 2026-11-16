"""STEP 04 - RQ3 bug detection: run QMON and the baselines on every mutant (paper App. B-B).

    # authors' mutants (needs data/mutants_authors.json from step 03)
    python reproduction/step04_rq3_mutants.py --tag authors

    # our mutants
    python reproduction/step04_rq3_mutants.py --tag ours

    # useful options
    --methods qmon qmon_pernode statistical proq liu   (default: all six; mqt is the slowest)
    --circuits ae_indep_qiskit_11 bv_indep_qiskit_5   (subset)  |  --shard 3/8  (split the 238)
    --per-method-timing                                (one evaluator call per method -> runtime per method)
    --budget-seconds 21600                             (authors' per-circuit wall limit; Linux/WSL only)

Environment: the authors' pinned venv, PYTHONPATH not needed (common.py sets it),
QMON_MILP_SOLVER=gurobi for the exact batch plans. Run under WSL/Linux: the per-circuit
budget uses SIGALRM, like the authors' runner.

What happens per circuit (all inside the authors' rq3_realexec_eval.evaluate_circuit):
  1. Oracle(key): Alg. 1 candidates (= the baselines' K checkpoints), expected p1 and expected
     one-qubit state per checkpoint, cone per checkpoint, Qmax=24 plan (B batches, K_qmon checkpoints).
  2. For every mutant slot of this circuit: rebuild the mutant from the manifest
     (apply_manifest_slot); skip it if output-equivalent; otherwise for each method call
     scan_method(): visit checkpoints in gate order, apply the method's flag rule, stop at the
     first flag -> (detected, first flagged checkpoint).
  3. Localization: suspect region = cone of the first flagged checkpoint;
     loc_precision = 1/|cone| if the mutated gate is in it, else 0.

Outputs (reproduction/data/):
  raw/<tag>/<circuit>.pkl              - the evaluator's full records (resume points)
  rq3_mutants_<tag>.csv                - one row per mutant (incl. output-equivalent ones): scope flags
  rq3_method_results_<tag>.csv         - one row per (non-equivalent mutant, method): detected,
                                         first flagged checkpoint, loc_precision, executions
  rq3_timing_<tag>.csv                 - wall-clock seconds per circuit (and per method if requested)
"""

import argparse
import pickle
import signal
import sys
import time

import common
common.use_authors_code()

import rq3_realexec_eval as rq3                      # the authors' RQ3 evaluator
from rq3_manifest import load_manifest
from step03_mutants import load_any_manifest
from records import mutant_row, method_rows, MUTANT_FIELDS, METHOD_FIELDS   # shared flatteners


class Budget(BaseException):
    """Raised by SIGALRM when a circuit exceeds its wall-clock budget (as in run_rq3_keys)."""


def evaluate_one(key, manifest, methods, per_method_timing):
    """Return (records, timing) for one circuit. records = list of the authors' record dicts."""
    seeds = tuple(int(s) for s in manifest["protocol"]["seeds"])  # 1-5 for the authors, 6-10 for ours
    timing = {"circuit": key}
    if not per_method_timing:
        started = time.perf_counter()
        # orig call here: the authors' per-circuit RQ3 evaluation for all requested methods.
        records = rq3.evaluate_circuit(key, seeds=seeds, methods=tuple(methods), manifest=manifest)  # [PROV:evaluate_circuit]
        timing["all_methods_seconds"] = round(time.perf_counter() - started, 3)
        return records, timing
    merged = None                                                  # one call per method, then merge
    for method in methods:
        started = time.perf_counter()
        part = rq3.evaluate_circuit(key, seeds=seeds, methods=(method,), manifest=manifest)
        timing[f"{method}_seconds"] = round(time.perf_counter() - started, 3)
        if merged is None:
            merged = part                                          # keeps scope/plan fields
        else:                                                      # same slots, same order
            for rec, extra in zip(merged, part):
                assert rec["slot_id"] == extra["slot_id"]
                rec["methods"].update(extra["methods"])
    return merged or [], timing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--methods", nargs="+", default=list(common.METHODS))
    parser.add_argument("--circuits", nargs="+")
    parser.add_argument("--shard", help="i/n: process the i-th of n equal slices (1-based)")
    parser.add_argument("--per-method-timing", action="store_true")
    parser.add_argument("--budget-seconds", type=int, default=rq3.MUTANT_CIRCUIT_BUDGET_SECONDS)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    manifest_path = common.DATA / f"mutants_{args.tag}.json"
    manifest = (load_manifest(manifest_path) if args.tag == "authors"
                else load_any_manifest(manifest_path))
    keys = sorted({s["circuit"] for s in manifest["slots"]})        # circuits that have mutants
    if args.circuits:
        wanted = {k if k.endswith(".qasm") else k + ".qasm" for k in args.circuits}
        keys = [k for k in keys if k in wanted]
    if args.shard:
        i, n = (int(x) for x in args.shard.split("/"))
        keys = keys[i - 1::n]                                       # round-robin split

    raw_dir = common.DATA / "raw" / args.tag
    raw_dir.mkdir(parents=True, exist_ok=True)
    use_alarm = hasattr(signal, "SIGALRM") and args.budget_seconds > 0
    if use_alarm:
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(Budget()))
    elif args.budget_seconds > 0:
        print("note: no SIGALRM on this OS; running without the per-circuit budget", file=sys.stderr)

    for index, key in enumerate(keys, start=1):
        raw_path = raw_dir / f"{key}.pkl"
        if raw_path.exists() and not args.no_resume:
            print(f"[{index}/{len(keys)}] {key}: already done")
            continue
        if use_alarm:
            signal.alarm(args.budget_seconds)
        try:
            records, timing = evaluate_one(key, manifest, args.methods, args.per_method_timing)
            status = "complete"
        except Budget:
            records, timing, status = [], {"circuit": key}, "budget-timeout"
        finally:
            if use_alarm:
                signal.alarm(0)
        timing["status"] = status
        with raw_path.open("wb") as handle:
            pickle.dump({"records": records, "timing": timing}, handle)
        print(f"[{index}/{len(keys)}] {key}: {status}, {len(records)} mutant records", flush=True)

    flatten(args.tag)


def flatten(tag):
    """Collect every raw/<tag>/*.pkl into the three CSVs."""
    mutants, methods, timings = [], [], []
    for raw_path in sorted((common.DATA / "raw" / tag).glob("*.pkl")):
        with raw_path.open("rb") as handle:
            blob = pickle.load(handle)
        timings.append(blob["timing"])
        for rec in blob["records"]:
            mutants.append(mutant_row(rec))
            if not rec["equivalent"]:                               # equivalent mutants have no method results
                methods.extend(method_rows(rec))
    if not mutants:
        print("nothing to flatten yet")
        return
    common.write_csv(common.DATA / f"rq3_mutants_{tag}.csv", mutants, MUTANT_FIELDS)
    common.write_csv(common.DATA / f"rq3_method_results_{tag}.csv", methods, METHOD_FIELDS)
    timing_fields = sorted({k for t in timings for k in t}, key=lambda k: (k != "circuit", k))
    common.write_csv(common.DATA / f"rq3_timing_{tag}.csv", timings, timing_fields)
    print(f"flattened {len(mutants)} mutants / {len(methods)} method results for tag={tag}")


if __name__ == "__main__":
    main()
