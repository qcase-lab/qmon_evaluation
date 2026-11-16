"""STEP 05 - RQ3 false alarms: run every method on the 238 CORRECT circuits (paper App. B-B(i)).

    python reproduction/step05_rq3_false_alarms.py --tag reproduced
    python reproduction/step05_rq3_false_alarms.py --circuits bv_indep_qiskit_3 --methods qmon

The mutants do not matter here, so the same output serves both the authors' and our own
mutant sets. The authors fix the shot seed (FALSE_ALARM_SHOT_SEED = 1) and one trial per
circuit; false_alarm_circuit() refuses any other seed, so this is a single fixed trial.

Per circuit and method (rq3_realexec_eval.false_alarm_circuit):
  * scan ALL checkpoints (no early exit) of the correct circuit;
  * apply the same flag rule as in the mutant arm (QMON: exact binomial at alpha/K_qmon,
    any contrary shot for deterministic checkpoints; statistical: chi2/binomial at alpha/K;
    proq/liu: any failed shot);
  * n_flagged = number of flagged checkpoints; false_alarm = (n_flagged > 0).
  * Baselines with K > 200 use the exact null shortcut instead of executing (recorded as
    execution_class = 'exact-null'); MQT is not evaluated (false_alarm = None) because its
    applicability rule already requires a pass on the correct circuit.

Output: reproduction/data/rq3_false_alarms_<tag>.csv - one row per (circuit, method)
        reproduction/data/raw/false_alarm_<tag>/<circuit>.pkl - full records (resume points)
"""

import argparse
import pickle
import signal
import time

import common
common.use_authors_code()

import rq3_realexec_eval as rq3
from records import false_alarm_rows, FALSE_ALARM_FIELDS     # shared flattener


class Budget(BaseException):
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="reproduced", help="label for this run's output files")
    parser.add_argument("--methods", nargs="+", default=list(common.METHODS))
    parser.add_argument("--circuits", nargs="+")
    parser.add_argument("--budget-seconds", type=int, default=rq3.FALSE_ALARM_CIRCUIT_BUDGET_SECONDS)
    args = parser.parse_args()

    keys = common.read_names(common.RQ3_CIRCUITS_LIST)            # the same 238 circuits
    if args.circuits:
        wanted = {k if k.endswith(".qasm") else k + ".qasm" for k in args.circuits}
        keys = [k for k in keys if k in wanted]
    raw_dir = common.DATA / "raw" / f"false_alarm_{args.tag}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    use_alarm = hasattr(signal, "SIGALRM") and args.budget_seconds > 0
    if use_alarm:
        signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(Budget()))

    for index, key in enumerate(keys, start=1):
        raw_path = raw_dir / f"{key}.pkl"
        if raw_path.exists():
            continue
        if use_alarm:
            signal.alarm(args.budget_seconds)
        started = time.perf_counter()
        try:
            record = rq3.false_alarm_circuit(key, methods=tuple(args.methods))   # [PROV:false_alarm_call]
            status = "complete"
        except Budget:
            record, status = None, "budget-timeout"
        finally:
            if use_alarm:
                signal.alarm(0)
        seconds = round(time.perf_counter() - started, 3)
        with raw_path.open("wb") as handle:
            pickle.dump({"record": record, "seconds": seconds, "status": status}, handle)
        print(f"[{index}/{len(keys)}] {key}: {status} in {seconds}s", flush=True)

    rows = []
    for raw_path in sorted(raw_dir.glob("*.pkl")):
        with raw_path.open("rb") as handle:
            blob = pickle.load(handle)
        if blob["record"]:
            rows.extend(false_alarm_rows(blob["record"], blob["seconds"]))
    common.write_csv(common.DATA / f"rq3_false_alarms_{args.tag}.csv", rows, FALSE_ALARM_FIELDS)
    print(f"wrote {len(rows)} (circuit, method) rows")


if __name__ == "__main__":
    main()
