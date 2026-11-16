"""Turn the authors' STORED RQ3 result files into the same CSVs our own pipeline writes.

    python reproduction/extract_authors_results.py

No simulation, no qiskit: only the Python standard library (+ numpy, which the pickles need).
After this, `python reproduction/step06_aggregate.py --tag authors_stored` builds the tables.

Sources (all under results/rq3/ and inputs/ in the authors' repo):
  rq3_mutant.pkl                    every mutant x method record (detected, first flag, loc_precision)
                                    -> only usable if it is the REAL 199 MB file. In the zip download it
                                       is a 134-byte Git-LFS pointer; fetch it with `git lfs pull`.
  rq3_falsealarm.pkl                every correct circuit x method record (n_flagged, false_alarm)
  rq3_miss_analysis.json            per-mutant QMON detected / any-baseline detected / scope class
                                    (written by src/rq3_miss_analysis.py from rq3_mutant.pkl)
  mqt_diagnostics.json              per-mutant MQT flag + mismatch/refusal counters
                                    (written by src/mqt_diagnostics.py from rq3_mutant.pkl)
  rq3_deployed_miss_diagnosis.json  the 432 deployment-covered QMON misses and their mechanism
  rq3_aggregate.txt                 the authors' printed Table III (output of aggregate())
  inputs/rq3_single_error_manifest.json   the 3,570 mutants

Outputs (reproduction/data/), tag = authors_stored:
  rq3_mutants_authors_stored.csv          one row per mutant (3,570)
  rq3_method_results_authors_stored.csv   one row per (non-equivalent mutant, method)
  rq3_false_alarms_authors_stored.csv     one row per (correct circuit, method)
  rq3_miss_mechanism_authors_stored.csv   the 432 deployment-covered QMON misses
  authors_printed_table3.csv              Table III exactly as printed in rq3_aggregate.txt
  authors_extraction_sources.json         which file each CSV came from, with SHA-256 checksums
"""

import hashlib
import json
import pickle
import re

import common
from records import (mutant_row, method_rows, false_alarm_rows,
                     MUTANT_FIELDS, METHOD_FIELDS, FALSE_ALARM_FIELDS)

TAG = "authors_stored"
RQ3 = common.AUTHORS_RESULTS / "rq3"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_real_pickle(path):
    """True for an actual pickle; False for a missing file or a Git-LFS pointer."""
    if not path.exists() or path.stat().st_size < 1024:
        return False
    with open(path, "rb") as handle:
        return handle.read(1) == b"\x80"                          # pickle protocol marker


def load_json(name):
    with open(RQ3 / name, encoding="utf-8") as handle:
        return json.load(handle)


def parse_printed_table3():
    """Read Table III from rq3_aggregate.txt (the authors' aggregate() printout)."""
    names = {"Batched QMon": "qmon", "Independent-checkpoint QMon": "qmon_pernode",
             "Statistical assertion": "statistical", "Projection assertion": "proq",
             "Dynamic ancilla": "liu", "MQT debugger (combined flag)": "mqt"}
    lines = (RQ3 / "rq3_aggregate.txt").read_text(encoding="utf-8").splitlines()
    rows = []
    for index, line in enumerate(lines):
        for label, method in names.items():
            if not line.startswith(label):
                continue
            pm = re.findall(r"([\d.]+) \+/- ([\d.]+)", line)       # value +/- sd pairs
            if len(pm) < 3:                                        # same label in another section
                continue
            fa = re.search(r"([\d.]+)% \((\d+)/(\d+)\)\s*$", line)  # false alarms "0.8% (2/238)"
            counts = re.findall(r"\(([\d,]+)/([\d,]+)\)", lines[index + 1])  # next line: pooled counts
            to_int = lambda text: int(text.replace(",", ""))
            rows.append({
                "method": method,
                "detection_mean": float(pm[0][0]), "detection_sd": float(pm[0][1]),
                "detected": to_int(counts[0][0]), "n_mutants": to_int(counts[0][1]),
                "covered_detection_mean": float(pm[1][0]), "covered_detection_sd": float(pm[1][1]),
                "covered_detected": to_int(counts[1][0]), "n_covered": to_int(counts[1][1]),
                "loc_precision_mean": float(pm[2][0]), "loc_precision_sd": float(pm[2][1]),
                "false_alarm_percent": float(fa.group(1)) if fa else None,
                "false_alarms": int(fa.group(2)) if fa else None,
                "fa_circuits": int(fa.group(3)) if fa else None,
            })
    return rows


def main():
    sources = {}
    manifest_path = common.CANONICAL_MANIFEST
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    sources["manifest"] = {"file": str(manifest_path.relative_to(common.REPO)), "sha256": sha256(manifest_path)}

    # ---------------- False-alarm arm: always available (real 17.5 MB pickle) -----------------
    fa_path = RQ3 / "rq3_falsealarm.pkl"
    with open(fa_path, "rb") as handle:
        fa_artifact = pickle.load(handle)
    fa_rows, plans = [], {}
    for record in fa_artifact["records"]:
        fa_rows.extend(false_alarm_rows(record))                    # same flattener as step 05  [PROV:x_fa]
        plans[record["circuit"]] = {"K": record["K"], "K_qmon": record["K_qmon"], "B": record["B"],  # [PROV:x_plan]
                                    "plan_sha256": record["qmon_plan"]["plan_sha256"]}
    common.write_csv(common.DATA / f"rq3_false_alarms_{TAG}.csv", fa_rows, FALSE_ALARM_FIELDS)
    sources["false_alarms"] = {"file": "results/rq3/rq3_falsealarm.pkl", "sha256": sha256(fa_path),
                               "records": len(fa_artifact["records"])}

    # ---------------- Mutant arm ---------------------------------------------------------------
    mutant_pkl = RQ3 / "rq3_mutant.pkl"
    if is_real_pickle(mutant_pkl):
        # FULL path: identical to what step 04 writes from our own runs.
        with open(mutant_pkl, "rb") as handle:
            artifact = pickle.load(handle)
        mutants, methods = [], []
        for rec in artifact["records"]:
            mutants.append(mutant_row(rec))
            if not rec["equivalent"]:
                methods.extend(method_rows(rec))  # [PROV:x_full]
        sources["mutants"] = {"mode": "full-per-record", "file": "results/rq3/rq3_mutant.pkl",
                              "sha256": sha256(mutant_pkl), "records": len(artifact["records"])}
    else:
        # FALLBACK path: rq3_mutant.pkl is a Git-LFS pointer. Rebuild what we can from the
        # authors' JSON projections of that same pickle.
        attempts = {row["slot_id"]: row for row in load_json("rq3_miss_analysis.json")["attempts"]}
        mqt = {row["slot_id"]: row for row in load_json("mqt_diagnostics.json")["records"]}
        mutants, methods = [], []
        for slot in manifest["slots"]:
            attempt = attempts.get(slot["slot_id"])               # only non-equivalent mutants have one
            scope = attempt["scope_class"] if attempt else None
            plan = plans[slot["circuit"]]                          # same plan as in the false-alarm arm
            mutants.append({
                "slot_id": slot["slot_id"], "circuit": slot["circuit"],
                "family": common.family_of(slot["circuit"]),
                "seed": slot["seed"], "ordinal": slot["ordinal"], "mut_gate": slot["gate"],
                "original_op": slot["original"]["name"], "replacement_op": slot["replacement"]["name"],
                "original_arity": slot["original"]["num_qubits"],
                "replacement_arity": slot["replacement"]["num_qubits"],
                "output_l1": slot["output_l1"], "output_equivalent": slot["output_equivalent"],
                "K": plan["K"], "K_qmon": plan["K_qmon"], "B": plan["B"],
                "in_scope_full": None if scope is None else scope != "outside-full-scope",  # [PROV:x_scope]
                "in_scope_qmon": None if scope is None else scope == "in-scope-qmon",
                "deployment_gap": None if scope is None else scope == "deployment-gap",
                "scope_class": scope, "plan_sha256": plan["plan_sha256"],
            })
            if attempt is None:
                continue
            base = {"slot_id": slot["slot_id"], "circuit": slot["circuit"], "seed": slot["seed"]}
            methods.append({**base, "method": "qmon", "complete": attempt["common_complete"],  # [PROV:x_qmon_detected]
                            "detected": attempt["qmon_detected"]})
            # pseudo-method: "statistical OR proq OR liu OR mqt flagged" (rq3_miss_analysis.py)
            methods.append({**base, "method": "any_reported_baseline",  # [PROV:x_any_baseline]
                            "complete": attempt["common_complete"],
                            "detected": attempt["baseline_detected"]})
            m = mqt[slot["slot_id"]]["methods"]["mqt"]
            methods.append({**base, "method": "mqt", "complete": m["complete"], "detected": m["detected"],  # [PROV:x_mqt]
                            "mqt_run_fail": m["stats"].get("run_fail", 0),
                            "mqt_run_unevaluable": m["stats"].get("run_unevaluable", 0),
                            "mqt_n_affected": m["stats"].get("n_affected"),
                            "mqt_n_applicable": m["stats"].get("n_applicable")})
        sources["mutants"] = {
            "mode": "fallback-json-projections",
            "why": "results/rq3/rq3_mutant.pkl is a Git-LFS pointer, not the data file",
            "files": {name: sha256(RQ3 / name) for name in
                      ("rq3_miss_analysis.json", "mqt_diagnostics.json")},
            "available_methods": ["qmon (detected only)", "mqt", "any_reported_baseline"],
            "missing": "qmon_pernode, statistical, proq, liu per-record results; loc_precision for all",
        }
    common.write_csv(common.DATA / f"rq3_mutants_{TAG}.csv", mutants, MUTANT_FIELDS)
    common.write_csv(common.DATA / f"rq3_method_results_{TAG}.csv", methods, METHOD_FIELDS)

    # ---------------- Mechanism of the 432 deployment-covered QMON misses -----------------------
    diag = load_json("rq3_deployed_miss_diagnosis.json")
    tolerance = diag["protocol"]["delta_zero_tolerance"]          # 1e-12
    mech_rows = []
    for r in diag["records"]:
        if not r["raw_z_visible"]:  # [PROV:x_mechanism]
            mechanism = "no_raw_deployed_z_signal"                 # mutant leaves every deployed 0/1 marginal unchanged
        elif (r["max_batch_absolute_delta"] or 0.0) <= tolerance:
            mechanism = "raw_signal_fully_erased_by_batch_channel" # measure-reset-replay maps it back
        else:
            mechanism = "batch_signal_present_but_realized_test_missed"  # signal too weak for 8,192 shots
        mech_rows.append({"slot_id": r["slot_id"], "circuit": r["circuit"], "seed": r["seed"],
                          "mut_gate": r["mut_gate"], "mechanism": mechanism,
                          "max_raw_absolute_delta": r["max_raw_absolute_delta"],
                          "max_batch_absolute_delta": r["max_batch_absolute_delta"],
                          "best_raw_node_power": r["best_raw_node_power"],
                          "best_batch_node_power": r["best_batch_node_power"],
                          "pernode_detected": r["observed_pernode_detected"],
                          "pernode_loc_hit": r["observed_pernode_loc_hit"]})
    common.write_csv(common.DATA / f"rq3_miss_mechanism_{TAG}.csv", mech_rows, list(mech_rows[0].keys()))
    sources["miss_mechanism"] = {"file": "results/rq3/rq3_deployed_miss_diagnosis.json",
                                 "sha256": sha256(RQ3 / "rq3_deployed_miss_diagnosis.json"),
                                 "summary_in_file": diag["summary"]["mechanism_partition"]}

    # ---------------- The authors' printed Table III -------------------------------------------
    printed = parse_printed_table3()  # [PROV:x_printed]
    common.write_csv(common.DATA / "authors_printed_table3.csv", printed, list(printed[0].keys()))
    sources["printed_table3"] = {"file": "results/rq3/rq3_aggregate.txt",
                                 "sha256": sha256(RQ3 / "rq3_aggregate.txt")}

    with open(common.DATA / "authors_extraction_sources.json", "w", encoding="utf-8") as handle:
        json.dump(sources, handle, indent=2)
    print(json.dumps({k: v.get("mode", v.get("file")) for k, v in sources.items()}, indent=2))


if __name__ == "__main__":
    main()
