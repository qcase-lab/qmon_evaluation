"""STEP 06 - Turn the per-mutant / per-circuit CSVs into the RQ3 tables and a Markdown report
in which every number says which line of code produced it.

    python reproduction/step06_aggregate.py --tag authors_stored   # the authors' stored results
    python reproduction/step06_aggregate.py --tag authors --fa-tag reproduced   # our rerun of seeds 1-5
    python reproduction/step06_aggregate.py --tag ours    --fa-tag reproduced   # our seeds 6-10

Inputs (reproduction/data/):
  rq3_mutants_<tag>.csv          one row per mutant (step 04 or extract_authors_results.py)
  rq3_method_results_<tag>.csv   one row per (non-equivalent mutant, method)
  rq3_false_alarms_<fa_tag>.csv  one row per (correct circuit, method)  (step 05 or extraction)
  rq3_miss_mechanism_<tag>.csv   optional: mechanism of deployment-covered QMON misses
  authors_printed_table3.csv     optional: the authors' printout, used ONLY to fill cells the
                                 per-record data cannot produce, and always labelled as such

Outputs (reproduction/results/<tag>/):
  table3_detection.csv, table_tp_fn_fp_tn.csv, table4_plan_costs.csv, table5_qmon_misses.csv,
  mqt_composition.csv, qmon_miss_breakdown.csv, RQ3_results_<tag>.md

The statistics follow the authors' aggregate() in rq3_realexec_eval.py exactly:
  * a rate is computed per seed, then reported as the unweighted mean and SAMPLE standard
    deviation of those per-seed rates (statistics.stdev; 0.0 if only one seed);
  * the pooled count (numerator/denominator over all seeds) is reported beside it;
  * only non-output-equivalent mutants complete for every method enter the rates;
  * localization precision is averaged over each method's OWN detected mutants;
  * the false-alarm rate is the share of correct circuits with at least one flagged checkpoint.
"""

import argparse
import math
import statistics
from collections import defaultdict
from pathlib import Path

import common
from common import author_ref, our_ref

ME = "step06_aggregate.py"                           # used to cite our own lines

# Published values (paper Tables III-V) used only to show "reproduced? yes/no" for the
# authors' mutant set. They are NOT used in any computation.
PAPER_TABLE3 = {
    "qmon": ("62.4 ± 5.4", 1782, "80.0 ± 3.9", 1774, "0.522 ± 0.126", "0.8", 2),
    "qmon_pernode": ("67.2 ± 4.5", 1921, "86.4 ± 1.6", 1916, "0.496 ± 0.127", "0.8", 2),
    "statistical": ("67.4 ± 4.4", 1928, "86.7 ± 1.6", 1924, "0.494 ± 0.126", "0.0", 0),
    "proq": ("71.1 ± 4.2", 2031, "91.6 ± 1.0", 2031, "0.500 ± 0.130", "0.0", 0),
    "liu": ("71.3 ± 4.4", 2036, "91.9 ± 0.8", 2036, "0.501 ± 0.131", "0.0", 0),
    "mqt": ("59.2 ± 6.2", 1688, "76.1 ± 4.0", 1688, "0.476 ± 0.122", None, None),
}
PAPER_TABLE4 = {"B": (1, 14, 30.0), "K_qmon": (21, 80, 84.3), "K": (21, 89, 92.1)}


# ======================================================================================
# Small statistics helpers (each mirrors a line of the authors' code)
# ======================================================================================
def seed_summary(values_by_seed):
    """Mean and sample SD of per-seed values, as the authors' ms() helper does."""
    values = [v for v in values_by_seed.values() if v is not None]
    if not values:
        return None, None
    mean = statistics.mean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0          # [PROV:seed_sd]
    return mean, sd


def nearest_rank(values, q):
    """Nearest-rank percentile: the ceil(q*n)-th sorted value (authors' _unique_circuit_plan_costs)."""
    ordered = sorted(values)
    return ordered[math.ceil(q * len(ordered)) - 1]


def wilson(k, n, z=1.959963984540054):
    """95% Wilson score interval for k/n (rq3_miss_analysis._wilson_interval)."""
    if n == 0:
        return None, None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def fmt(mean, sd, digits=1, pct=False):
    if mean is None:
        return "n/a"
    return f"{mean:.{digits}f} ± {sd:.{digits}f}" + ("%" if pct else "")


# ======================================================================================
# Loading
# ======================================================================================
def load(tag, fa_tag):
    mutants = common.read_csv(common.DATA / f"rq3_mutants_{tag}.csv")
    results = common.read_csv(common.DATA / f"rq3_method_results_{tag}.csv")
    fa_path = common.DATA / f"rq3_false_alarms_{fa_tag}.csv"
    false_alarms = common.read_csv(fa_path) if fa_path.exists() else []
    mech_path = common.DATA / f"rq3_miss_mechanism_{tag}.csv"
    mechanism = common.read_csv(mech_path) if mech_path.exists() else []
    printed_path = common.DATA / "authors_printed_table3.csv"
    printed = ({r["method"]: r for r in common.read_csv(printed_path)}
               if tag.startswith("authors") and printed_path.exists() else {})
    return mutants, results, false_alarms, mechanism, printed


# ======================================================================================
# The computations
# ======================================================================================
def build(tag, fa_tag):
    mutants, results, false_alarms, mechanism, printed = load(tag, fa_tag)
    by_slot = defaultdict(dict)                                         # slot_id -> method -> row
    for row in results:
        by_slot[row["slot_id"]][row["method"]] = row

    attempted = mutants                                                 # every mutant drawn
    buggy_attempted = [m for m in mutants if not m["output_equivalent"]]   # [PROV:drop_equivalent]
    present = sorted({r["method"] for r in results})
    # A method is "per-record available" if it has a row for every non-equivalent mutant.
    available = [m for m in common.METHODS
                 if all(m in by_slot[x["slot_id"]] for x in buggy_attempted)]
    paired = [m for m in available]                                     # methods used for the common set
    common_set = [x for x in buggy_attempted                            # [PROV:common_complete]
                  if all(by_slot[x["slot_id"]][m]["complete"] for m in paired)]
    covered = [x for x in common_set if x["in_scope_full"]]             # [PROV:candidate_covered]
    seeds = sorted({x["seed"] for x in mutants})

    def det(x, method):
        return bool(by_slot[x["slot_id"]][method]["detected"])

    # ---------------- Table III + TP/FN/FP/TN -------------------------------------------------
    table3, confusion = [], []
    fa_common_circuits = None
    if false_alarms:
        fa_by_circuit = defaultdict(dict)
        for r in false_alarms:
            fa_by_circuit[r["circuit"]][r["method"]] = r
        fa_common_circuits = [c for c, rows in fa_by_circuit.items()      # circuits complete for every method
                              if all(rows.get(m, {}).get("complete") for m in common.METHODS if m in rows)]
    for method in common.METHODS:
        row = {"method": method, "name": common.METHOD_NAMES[method]}
        src = {}
        if method in available:
            per_seed = {s: 100 * statistics.mean([det(x, method) for x in common_set if x["seed"] == s])
                        for s in seeds if any(x["seed"] == s for x in common_set)}       # [PROV:detection_per_seed]
            row["detection_mean"], row["detection_sd"] = seed_summary(per_seed)        # [PROV:detection]
            row["detected"] = sum(det(x, method) for x in common_set)                 # [PROV:detection_pooled]
            row["n_mutants"] = len(common_set)
            per_seed_cov = {s: 100 * statistics.mean([det(x, method) for x in covered if x["seed"] == s])
                            for s in seeds if any(x["seed"] == s for x in covered)}   # [PROV:covered_per_seed]
            row["covered_detection_mean"], row["covered_detection_sd"] = seed_summary(per_seed_cov)
            row["covered_detected"] = sum(det(x, method) for x in covered)
            row["n_covered"] = len(covered)
            # FALSE NEGATIVES = non-equivalent mutants the method did NOT flag.
            per_seed_fn = {s: 100 - v for s, v in per_seed.items()}                    # [PROV:fn_rate]
            row["fn_rate_mean"], row["fn_rate_sd"] = seed_summary(per_seed_fn)
            row["false_negatives"] = row["n_mutants"] - row["detected"]                # [PROV:fn_pooled]
            src["detection"] = src["covered"] = "per-record"
            locs = [by_slot[x["slot_id"]][method].get("loc_precision") for x in common_set]
            if all(v is not None for v in locs):
                per_seed_loc = {}
                for s in seeds:                                                         # [PROV:loc_precision]
                    vals = [by_slot[x["slot_id"]][method]["loc_precision"]
                            for x in common_set if x["seed"] == s and det(x, method)]
                    if vals:
                        per_seed_loc[s] = statistics.mean(vals)
                row["loc_precision_mean"], row["loc_precision_sd"] = seed_summary(per_seed_loc)
                src["loc"] = "per-record"
        if "detection" not in src and method in printed:          # fill from the authors' printout
            p = printed[method]
            for key in ("detection_mean", "detection_sd", "detected", "n_mutants",
                        "covered_detection_mean", "covered_detection_sd", "covered_detected", "n_covered"):
                row[key] = p[key]
            row["fn_rate_mean"], row["fn_rate_sd"] = 100 - p["detection_mean"], p["detection_sd"]
            row["false_negatives"] = p["n_mutants"] - p["detected"]
            src["detection"] = src["covered"] = "printed"
        if "loc" not in src and method in printed:
            row["loc_precision_mean"] = printed[method]["loc_precision_mean"]
            row["loc_precision_sd"] = printed[method]["loc_precision_sd"]
            src["loc"] = "printed"
        # False alarms: share of correct circuits with >= 1 flagged checkpoint.
        if fa_common_circuits is not None:
            flags = [fa_by_circuit[c][method]["false_alarm"] for c in fa_common_circuits
                     if isinstance(fa_by_circuit[c].get(method, {}).get("false_alarm"), bool)]  # [PROV:false_alarm]
            if flags:
                row["false_alarms"] = sum(flags)
                row["fa_circuits"] = len(flags)
                row["false_alarm_percent"] = 100 * statistics.mean(flags)
                src["fa"] = "per-record"
            else:
                src["fa"] = "not-measured"                         # MQT: definition shortcut, no empirical FA
        row["source_detection"] = src.get("detection", "missing")
        row["source_loc_precision"] = src.get("loc", "missing")
        row["source_false_alarm"] = src.get("fa", "missing")
        if tag.startswith("authors") and method in PAPER_TABLE3:
            paper = PAPER_TABLE3[method]
            row["paper_detection"], row["paper_detected"] = paper[0], paper[1]
            row["paper_covered"], row["paper_covered_detected"] = paper[2], paper[3]
            row["paper_loc_precision"], row["paper_false_alarm_percent"] = paper[4], paper[5]
        table3.append(row)

        # Confusion-style counts. Positives = buggy mutants; negatives = correct circuits.
        tp = row.get("detected")
        fn = row.get("false_negatives")
        fp = row.get("false_alarms")
        negatives = row.get("fa_circuits")
        confusion.append({                                                              # [PROV:confusion]
            "method": method, "name": common.METHOD_NAMES[method],
            "TP_detected_mutants": tp, "FN_missed_mutants": fn,
            "positives_non_equivalent_mutants": row.get("n_mutants"),
            "TPR_pooled_percent": 100 * tp / row["n_mutants"] if tp is not None else None,
            "FNR_pooled_percent": 100 * fn / row["n_mutants"] if fn is not None else None,
            "FNR_seed_mean": row.get("fn_rate_mean"), "FNR_seed_sd": row.get("fn_rate_sd"),
            "FP_flagged_correct_circuits": fp,
            "TN_clean_correct_circuits": (negatives - fp) if fp is not None else None,
            "negatives_correct_circuits": negatives,
            "FPR_percent": row.get("false_alarm_percent"),
            "source_positives": row["source_detection"], "source_negatives": row["source_false_alarm"],
        })

    # ---------------- Table IV: planned runs per circuit (unique circuits) ---------------------
    plans = {}
    for x in mutants:                                                   # [PROV:plan_costs]
        plans[x["circuit"]] = (x["K"], x["K_qmon"], x["B"])
    table4 = []
    for field, index, unit in (("B", 2, "batch runs (batched QMON)"),
                               ("K_qmon", 1, "checkpoint reads (independent QMON)"),
                               ("K", 0, "circuit runs (separate-run assertions)")):
        values = [p[index] for p in plans.values()]
        entry = {"plan": field, "unit": unit, "circuits": len(values),
                 "mean": statistics.mean(values), "median": statistics.median(values),
                 "p75_nearest_rank": nearest_rank(values, 0.75), "max": max(values)}
        if field == "B":
            entry["circuits_with_one_batch"] = sum(v == 1 for v in values)          # [PROV:single_batch]
        if tag.startswith("authors"):
            entry["paper_median"], entry["paper_p75"], entry["paper_mean"] = PAPER_TABLE4[field]
        table4.append(entry)

    # ---------------- Table V: QMON misses by stratum ------------------------------------------
    qmon_ok = "qmon" in available
    table5, breakdown = [], []
    if qmon_ok:
        miss = {x["slot_id"]: not det(x, "qmon") for x in common_set}
        total_misses = sum(miss.values())

        def stratum(label, dimension, rows):
            per_seed, represented = {}, 0
            for s in seeds:
                sel = [x for x in rows if x["seed"] == s]
                if sel:
                    represented += 1
                    per_seed[s] = 100 * sum(miss[x["slot_id"]] for x in sel) / len(sel)   # [PROV:miss_strata]
            k = sum(miss[x["slot_id"]] for x in rows)
            mean, sd = seed_summary(per_seed)
            return {"dimension": dimension, "stratum": label, "misses": k, "attempts": len(rows),
                    "pooled_miss_rate": 100 * k / len(rows) if rows else None,
                    "seed_rate_mean": mean, "seed_rate_sd": sd,
                    "sparse": len(rows) < 20 or represented < len(seeds),
                    "share_of_misses": 100 * k / total_misses if total_misses else None}

        overall = stratum("all non-output-equivalent mutants", "overall", common_set)
        lo, hi = wilson(overall["misses"], overall["attempts"])
        overall["wilson95_low"], overall["wilson95_high"] = 100 * lo, 100 * hi
        table5.append(overall)
        groups = defaultdict(list)
        for x in common_set:
            groups[("circuit family", x["family"])].append(x)
            groups[("mutation operation", f"{x['original_op']}->{x['replacement_op']}")].append(x)
            groups[("original gate arity", "two-qubit" if x["original_arity"] == 2 else "one-qubit")].append(x)
            coverage = {"outside-full-scope": "not candidate-covered", "in-scope-qmon": "deployment-covered",
                        "deployment-gap": "deployment gap"}[x["scope_class"]]
            groups[("monitoring coverage", coverage)].append(x)
        rows5 = [stratum(label, dim, rows) for (dim, label), rows in groups.items()]
        for dim, top in (("circuit family", 6), ("mutation operation", 4),
                         ("original gate arity", None), ("monitoring coverage", None)):
            chosen = sorted([r for r in rows5 if r["dimension"] == dim],
                            key=lambda r: (-r["misses"], r["stratum"]))
            table5.extend(chosen[:top] if top else chosen)

        # Miss breakdown exactly like aggregate()'s "QMon miss breakdown" line.
        missed = [x for x in common_set if miss[x["slot_id"]]]
        outside = sum(1 for x in missed if not x["in_scope_full"])                    # [PROV:miss_breakdown]
        gap = sum(1 for x in missed if x["deployment_gap"])
        if all(m in available for m in common.METHODS):
            nobody = sum(1 for x in missed if x["in_scope_full"] and not x["deployment_gap"]
                         and not any(det(x, m) for m in common.METHODS))
            rule = "no method incl. the per-checkpoint ablation flags it (aggregate() rule)"
        elif all("any_reported_baseline" in by_slot[x["slot_id"]] for x in missed):
            nobody = sum(1 for x in missed if x["in_scope_full"] and not x["deployment_gap"]
                         and not by_slot[x["slot_id"]]["any_reported_baseline"]["detected"])
            rule = "none of statistical/proq/liu/mqt flags it (rq3_miss_analysis rule; ablation not available)"
        else:
            nobody, rule = None, "unavailable"
        breakdown = [
            {"category": "outside candidate scope (no affected numerical candidate)", "count": outside},
            {"category": "deployment gap (affected candidate not deployed at Qmax=24)", "count": gap},
            {"category": "deployment-covered, missed by every method", "count": nobody, "rule": rule},
            {"category": "deployment-covered, caught by another method",
             "count": (len(missed) - outside - gap - nobody) if nobody is not None else None, "rule": rule},
            {"category": "total QMON misses", "count": len(missed)},
        ]

    # ---------------- MQT flag composition ----------------------------------------------------
    mqt_rows = []
    if "mqt" in available and all(by_slot[x["slot_id"]]["mqt"].get("mqt_run_fail") is not None
                                  for x in common_set):
        for kind, field in (("evaluated state mismatch", "mqt_run_fail"),
                            ("unevaluable / refusal", "mqt_run_unevaluable")):
            per_seed = {}
            for s in seeds:                                                             # [PROV:mqt_composition]
                sel = [x for x in common_set if x["seed"] == s]
                per_seed[s] = 100 * sum(by_slot[x["slot_id"]]["mqt"][field] for x in sel) / len(sel)
            mean, sd = seed_summary(per_seed)
            mqt_rows.append({"outcome": kind, "count": sum(by_slot[x["slot_id"]]["mqt"][field] for x in common_set),
                             "seed_rate_mean": mean, "seed_rate_sd": sd})
        mqt_det = next(r for r in table3 if r["method"] == "mqt")
        mqt_rows.append({"outcome": "combined flag", "count": mqt_det["detected"],
                         "seed_rate_mean": mqt_det["detection_mean"], "seed_rate_sd": mqt_det["detection_sd"]})

    # ---------------- Mechanism of deployment-covered QMON misses ------------------------------
    mech_rows = []
    if mechanism:
        counts = defaultdict(int)
        for r in mechanism:                                                             # [PROV:mechanism]
            counts[r["mechanism"]] += 1
        for name, k in sorted(counts.items(), key=lambda kv: -kv[1]):
            mech_rows.append({"mechanism": name, "count": k, "share_percent": 100 * k / len(mechanism)})
        erased = [r for r in mechanism if r["mechanism"] == "raw_signal_fully_erased_by_batch_channel"]
        mech_rows.append({"mechanism": "ablation flags (of all deployment-covered misses)",
                          "count": sum(bool(r["pernode_detected"]) for r in mechanism)})
        mech_rows.append({"mechanism": "ablation flags with correct cone",
                          "count": sum(bool(r["pernode_loc_hit"]) for r in mechanism)})
        mech_rows.append({"mechanism": "erased-by-replay misses the ablation catches",
                          "count": sum(bool(r["pernode_detected"]) for r in erased)})

    timing_rows = []
    timing_path = common.DATA / f"rq3_timing_{tag}.csv"
    if timing_path.exists():                                                            # [PROV:timing]
        timing = common.read_csv(timing_path)
        for column in [k for k in timing[0] if k.endswith("_seconds")]:
            vals = [t[column] for t in timing if isinstance(t.get(column), (int, float))]
            if vals:
                timing_rows.append({"column": column, "circuits": len(vals), "mean": statistics.mean(vals),
                                    "median": statistics.median(vals), "max": max(vals),
                                    "total_hours": sum(vals) / 3600})

    population = {
        "attempted": len(attempted), "output_equivalent": len(attempted) - len(buggy_attempted),
        "non_equivalent": len(buggy_attempted), "common_complete": len(common_set),
        "candidate_covered": len(covered),
        "deployment_covered": sum(1 for x in common_set if x["in_scope_qmon"]),
        "deployment_gaps": sum(1 for x in common_set if x["deployment_gap"]),
        "seeds": seeds, "methods_per_record": available,
        "circuits": len({x["circuit"] for x in mutants}),
        "fa_circuits": len(fa_common_circuits or []),
    }
    return {"population": population, "table3": table3, "confusion": confusion, "table4": table4,
            "table5": table5, "breakdown": breakdown, "mqt": mqt_rows, "mechanism": mech_rows,
            "timing": timing_rows}


# ======================================================================================
# Writing: CSVs + Markdown with provenance
# ======================================================================================
def write_tables(out_dir, r):
    def fields(rows):
        seen = []
        for row in rows:
            for k in row:
                if k not in seen:
                    seen.append(k)
        return seen
    for name, key in (("table3_detection", "table3"), ("table_tp_fn_fp_tn", "confusion"),
                      ("table4_plan_costs", "table4"), ("table5_qmon_misses", "table5"),
                      ("qmon_miss_breakdown", "breakdown"), ("mqt_composition", "mqt"),
                      ("qmon_miss_mechanism", "mechanism"), ("timing_summary", "timing")):
        if r[key]:
            common.write_csv(out_dir / f"{name}.csv", r[key], fields(r[key]))


def source_note(kind, tag):
    """Explain where a column's per-record input came from."""
    if kind == "printed":
        return ("copied from results/rq3/rq3_aggregate.txt (the authors' aggregate() printout, "
                f"{author_ref('agg_det')}); the per-record file is not available")
    if tag == "authors_stored":
        return "recomputed from the authors' stored per-record files (see Data lineage)"
    return f"recomputed from records produced by step04/step05 of this framework (tag `{tag}`)"


def extraction_mode(tag):
    """'fallback-json-projections' when the authors' rq3_mutant.pkl was a Git-LFS pointer."""
    path = common.DATA / "authors_extraction_sources.json"
    if tag != "authors_stored" or not path.exists():
        return None
    import json
    with open(path, encoding="utf-8") as handle:
        return json.load(handle).get("mutants", {}).get("mode")


def markdown(tag, fa_tag, r):
    P = r["population"]
    fallback = extraction_mode(tag) == "fallback-json-projections"
    lines = []
    add = lines.append
    add(f"# QMON RQ3 reproduction: results for mutant set `{tag}`\n")
    add("Every value below is computed by `reproduction/step06_aggregate.py` from CSV files in "
        "`reproduction/data/`. Each table is followed by a **provenance chain**: the line of the "
        "authors' code that made the per-checkpoint/per-mutant decision, the line that wrote it into "
        "a record, the line that copied it into our CSV, and the line in step06 that summarised it. "
        "Line numbers are looked up when this report is generated.\n")

    add("## Population\n")
    add("| Quantity | Value | Where it comes from |\n|---|---:|---|")
    add(f"| Mutation attempts | {P['attempted']:,} | {P['circuits']} circuits × {len(P['seeds'])} seeds × 3; "
        f"drawn at {author_ref('mut_seed')}–{author_ref('mut_sample')}, replaced by {author_ref('mut_replace')} |")
    add(f"| Output-equivalent (excluded, not scored) | {P['output_equivalent']:,} | L1 < 1e-9 at "
        f"{author_ref('mut_equivalent')}; skipped at {author_ref('skip_equivalent')}; dropped at "
        f"{our_ref(ME, 'drop_equivalent')} |")
    add(f"| Non-output-equivalent mutants (= positives) | {P['non_equivalent']:,} | |")
    add(f"| Complete for every method (rate denominator) | {P['common_complete']:,} | "
        f"{our_ref(ME, 'common_complete')} |")
    add(f"| Candidate-covered | {P['candidate_covered']:,} | mutated gate in the cone of ≥1 Algorithm-1 "
        f"candidate: {author_ref('scope')}; filtered at {our_ref(ME, 'candidate_covered')} |")
    add(f"| Deployment-covered | {P['deployment_covered']:,} | same test on deployed checkpoints only |")
    add(f"| Deployment gaps | {P['deployment_gaps']:,} | candidate-covered but not deployment-covered |")
    add(f"| Correct circuits in the false-alarm arm (= negatives) | {P['fa_circuits']} | "
        f"`rq3_false_alarms_{fa_tag}.csv` |")
    add(f"| Methods with per-record results | {', '.join(P['methods_per_record']) or 'none'} | |\n")

    # ---------------- Table III --------------------------------------------------------------
    add("## Table III: detection, localization precision, false alarms\n")
    add("Rates: mean ± sample SD of the per-seed rates; pooled counts in parentheses.\n")
    has_paper = any("paper_detection" in row for row in r["table3"])
    head = "| Method | Detection | Candidate-covered detection | Localization precision | False alarms |"
    sep = "|---|---|---|---|---|"
    if has_paper:
        head += " Paper (detection / covered / loc / FA) |"
        sep += "---|"
    add(head)
    add(sep)
    for row in r["table3"]:
        d = (f"{fmt(row.get('detection_mean'), row.get('detection_sd'), pct=True)} "
             f"({row.get('detected', 'n/a'):,}/{row.get('n_mutants', 0):,})" if row.get("detected") is not None else "n/a")
        c = (f"{fmt(row.get('covered_detection_mean'), row.get('covered_detection_sd'), pct=True)} "
             f"({row.get('covered_detected'):,}/{row.get('n_covered'):,})" if row.get("covered_detected") is not None else "n/a")
        loc = fmt(row.get("loc_precision_mean"), row.get("loc_precision_sd"), digits=3)
        fa = (f"{row['false_alarm_percent']:.1f}% ({row['false_alarms']}/{row['fa_circuits']})"
              if row.get("false_alarm_percent") is not None else "not measured")
        marks = []
        if row["source_detection"] == "printed":
            marks.append("ᴾ")
        line = f"| {row['name']}{''.join(marks)} | {d} | {c} | {loc}{'ᴾ' if row['source_loc_precision'] == 'printed' else ''} | {fa} |"
        if has_paper:
            fa_paper = f"{row['paper_false_alarm_percent']}%" if row.get("paper_false_alarm_percent") else "–"
            line += (f" {row['paper_detection']}% ({row['paper_detected']:,}) / {row['paper_covered']}% "
                     f"({row['paper_covered_detected']:,}) / {row['paper_loc_precision']} / {fa_paper} |")
        add(line)
    if any(row["source_detection"] == "printed" or row["source_loc_precision"] == "printed" for row in r["table3"]):
        add("\nᴾ = " + source_note("printed", tag) + ".")
    if has_paper:
        diffs = []
        for row in r["table3"]:
            for ours, paper, label in (("detected", "paper_detected", "detected"),
                                       ("covered_detected", "paper_covered_detected", "candidate-covered detected")):
                if row.get(ours) is not None and row.get(paper) is not None and row[ours] != row[paper]:
                    diffs.append(f"{row['name']}: {label} = {row[ours]:,} here vs {row[paper]:,} in the paper")
        add("\n**Differences from the published Table III:** " + ("; ".join(diffs) if diffs else "none") + ".")
    printed = {}
    printed_path = common.DATA / "authors_printed_table3.csv"
    if tag.startswith("authors") and printed_path.exists():
        printed = {p["method"]: p for p in common.read_csv(printed_path)}
    pdiffs = []
    for row in r["table3"]:
        p = printed.get(row["method"])
        if p and row["source_detection"] == "per-record":
            for key, label in (("detected", "detected"), ("covered_detected", "candidate-covered detected")):
                if row.get(key) is not None and row[key] != p[key]:
                    pdiffs.append(f"{row['name']}: {label} = {row[key]:,} here vs {p[key]:,} in rq3_aggregate.txt")
    if printed:
        add("\n**Differences from the authors' printed summary (results/rq3/rq3_aggregate.txt):** "
            + ("; ".join(pdiffs) if pdiffs else "none") + ".")
    add("")
    add("**Provenance chain, column by column**\n")
    add(f"- **Detection.** For one mutant and one method, `scan_method` ({author_ref('scan')}) visits the "
        f"method's checkpoints in gate order and returns at the first flag ({author_ref('scan_first_flag')}). "
        "The flag rule per method: "
        f"QMON reads come from the instrumented batch simulation ({author_ref('qmon_batch_sim')}) and are "
        f"tested by `qmon_count_flag` ({author_ref('qmon_decision')}): any contrary shot for a deterministic "
        f"expectation ({author_ref('qmon_deterministic')}), otherwise exact binomial p < α/K_qmon "
        f"({author_ref('qmon_binomial')}, Bonferroni at {author_ref('qmon_bonferroni')}). "
        f"Independent QMON samples the raw mutant marginal instead ({author_ref('pernode_read')}). "
        f"Statistical: `run_statistical` ({author_ref('stat_run')}; unaffected checkpoints {author_ref('stat_null')}). "
        f"Projection: `run_proq` ({author_ref('proq_run')}). Dynamic ancilla: `run_liu` ({author_ref('liu_run')}). "
        f"MQT: mismatch or refusal flags ({author_ref('mqt_flag')}). Unaffected checkpoints use the "
        f"evaluation-only shortcut decided at {author_ref('no_effect_shortcut')}. "
        f"The boolean is stored as `detected` at {author_ref('rec_detected')}, copied to column `detected` of "
        f"`rq3_method_results_{tag}.csv` at {our_ref('records.py', 'csv_detected')}"
        + (f" (here, because rq3_mutant.pkl is a Git-LFS pointer: QMON's `detected` is read at "
           f"{our_ref('extract_authors_results.py', 'x_qmon_detected')} from rq3_miss_analysis.json, where the "
           f"authors copied it out of rq3_mutant.pkl at {author_ref('miss_qmon_detected')}; MQT's at "
           f"{our_ref('extract_authors_results.py', 'x_mqt')} from mqt_diagnostics.json, built by "
           f"{author_ref('mqt_diag_result')})" if fallback else "")
        + (f" (rows read from results/rq3/rq3_mutant.pkl at {our_ref('extract_authors_results.py', 'x_full')})"
           if extraction_mode(tag) == "full-per-record" else "")
        + f", averaged per seed at {our_ref(ME, 'detection_per_seed')} and summarised at "
        f"{our_ref(ME, 'detection')} (SD at {our_ref(ME, 'seed_sd')}); pooled count at "
        f"{our_ref(ME, 'detection_pooled')}. Authors' equivalent: {author_ref('agg_det')} with ms() at "
        f"{author_ref('agg_ms')}.")
    add(f"- **Candidate-covered detection.** Same `detected` values restricted to `in_scope_full` "
        f"({author_ref('scope')} → {our_ref('records.py', 'csv_scope')}) at {our_ref(ME, 'covered_per_seed')}. "
        f"Authors: {author_ref('agg_dets')}.")
    add(f"- **Localization precision.** The suspect region is the cone of the first flagged checkpoint "
        f"({author_ref('rec_suspect')}; cones from {author_ref('oracle_cone')}); precision = 1/|cone| if the "
        f"mutated gate is in it else 0 ({author_ref('rec_loc_precision')}); CSV column `loc_precision` "
        f"({our_ref('records.py', 'csv_loc')}); per-seed mean over detected mutants at "
        f"{our_ref(ME, 'loc_precision')}. Authors: {author_ref('agg_prec')}.")
    add(f"- **False alarms.** `false_alarm_circuit` ({author_ref('fa_function')}) scans every checkpoint of "
        f"the correct circuit, counts flags ({author_ref('fa_count')}) and sets `false_alarm = n_flagged > 0` "
        f"({author_ref('fa_flag')}); MQT is not evaluated ({author_ref('fa_mqt_none')}). CSV column "
        f"`false_alarm` ({our_ref('records.py', 'csv_false_alarm')}); share of circuits at "
        f"{our_ref(ME, 'false_alarm')}. Authors: {author_ref('agg_fa')}.\n")

    # ---------------- TP / FN / FP / TN --------------------------------------------------------
    add("## False negatives and false positives\n")
    add("Positives are the non-output-equivalent mutants (a bug is present); negatives are the 238 "
        "unmutated circuits (no bug). The two populations come from separate experiments, so a "
        "precision value (TP/(TP+FP)) would mix them and is not reported. Output-equivalent mutants are "
        "neither positives nor negatives: they are dropped.\n")
    add("| Method | TP (detected) | FN (missed) | FN rate, pooled | FN rate, seed mean ± SD | FP (flagged correct circuits) | TN | FP rate |")
    add("|---|---:|---:|---:|---:|---:|---:|---:|")
    for c in r["confusion"]:
        cell = lambda v, f="{:,}": f.format(v) if v is not None else "n/a"
        add(f"| {c['name']} | {cell(c['TP_detected_mutants'])} | {cell(c['FN_missed_mutants'])} | "
            f"{cell(c['FNR_pooled_percent'], '{:.1f}%')} | {fmt(c['FNR_seed_mean'], c['FNR_seed_sd'], pct=True)} | "
            f"{cell(c['FP_flagged_correct_circuits'])} | {cell(c['TN_clean_correct_circuits'])} | "
            f"{cell(c['FPR_percent'], '{:.1f}%')} |")
    add("")
    add(f"Provenance: FN = mutants with `detected = false` ({our_ref(ME, 'fn_pooled')}); the seed-level FN "
        f"rate is 100 − the per-seed detection rate ({our_ref(ME, 'fn_rate')}), so its SD equals the "
        f"detection SD. FP/TN come from the false-alarm column above. Table assembled at "
        f"{our_ref(ME, 'confusion')}.\n")

    # ---------------- Table IV ----------------------------------------------------------------
    add("## Table IV: planned runs for a complete checkpoint scan (per circuit)\n")
    has_paper4 = any("paper_mean" in t for t in r["table4"])
    add("| Plan | Unit | Median | 75th pct (nearest rank) | Mean | Max |" + (" Paper (median / P75 / mean) |" if has_paper4 else ""))
    add("|---|---|---:|---:|---:|---:|" + ("---|" if has_paper4 else ""))
    for t in r["table4"]:
        line = f"| {t['plan']} | {t['unit']} | {t['median']:g} | {t['p75_nearest_rank']} | {t['mean']:.1f} | {t['max']:,} |"
        if has_paper4:
            line += f" {t['paper_median']} / {t['paper_p75']} / {t['paper_mean']} |"
        add(line)
    one = next(t for t in r["table4"] if t["plan"] == "B").get("circuits_with_one_batch")
    add(f"\nCircuits whose QMON plan is a single batch: **{one} / {r['table4'][0]['circuits']}** "
        f"({our_ref(ME, 'single_batch')}).\n")
    add(f"Provenance: B = number of batches from FFD + conditional ILP ({author_ref('batching')}) stored at "
        f"{author_ref('oracle_B')}; K_qmon = deployed checkpoints incl. free final reads ({author_ref('oracle_Kqmon')}); "
        f"K = all Algorithm-1 candidates ({author_ref('oracle_K')}, selector {author_ref('alg1_selector')}). "
        f"Copied per mutant at {our_ref('records.py', 'csv_plan')}"
        + (f" (fallback: from the false-alarm records, {our_ref('extract_authors_results.py', 'x_plan')})" if fallback else "")
        + f"; one value per unique circuit at {our_ref(ME, 'plan_costs')}. Authors: {author_ref('agg_costs')}.\n")

    # ---------------- Table V + breakdown -----------------------------------------------------
    if r["table5"]:
        add("## Table V: where QMON misses come from\n")
        add("| Dimension | Stratum | Misses / attempts | Pooled rate | Seed rate (mean ± SD) | Share of misses |")
        add("|---|---|---:|---:|---:|---:|")
        for t in r["table5"]:
            extra = (f" (Wilson 95%: {t['wilson95_low']:.1f}–{t['wilson95_high']:.1f}%)" if "wilson95_low" in t else "")
            add(f"| {t['dimension']} | {t['stratum']} | {t['misses']:,}/{t['attempts']:,} | "
                f"{t['pooled_miss_rate']:.1f}%{extra} | {fmt(t['seed_rate_mean'], t['seed_rate_sd'], pct=True)}"
                f"{'†' if t['sparse'] else ''} | {t['share_of_misses']:.1f}% |")
        add("\n† sparse: fewer than 20 attempts or not represented in every seed (rq3_miss_analysis rule).\n")
        add(f"Provenance: a miss is `detected = false` for QMON; strata rates at {our_ref(ME, 'miss_strata')}; "
            f"authors' version {author_ref('miss_rows')} and {author_ref('miss_rate')}.\n")
    if r["breakdown"]:
        add("### QMON miss breakdown\n")
        add("| Category | Count |\n|---|---:|")
        for b in r["breakdown"]:
            add(f"| {b['category']} | {b['count'] if b['count'] is not None else 'n/a'} |")
        rule = next((b.get("rule") for b in r["breakdown"] if b.get("rule")), "")
        add(f"\nRule for 'missed by every method': {rule}. Computed at {our_ref(ME, 'miss_breakdown')}.\n")
    if r["mechanism"]:
        add("### Why deployment-covered misses happen (authors' exact-probability diagnosis)\n")
        add("| Mechanism | Count | Share |\n|---|---:|---:|")
        for m in r["mechanism"]:
            share = f"{m['share_percent']:.1f}%" if m.get("share_percent") is not None else ""
            add(f"| {m['mechanism']} | {m['count']} | {share} |")
        add(f"\nProvenance: categories assigned at {our_ref('extract_authors_results.py', 'x_mechanism')} "
            f"from results/rq3/rq3_deployed_miss_diagnosis.json; counted at {our_ref(ME, 'mechanism')}. The "
            "script that produced that JSON is not in the authors' package.\n")

    # ---------------- MQT -----------------------------------------------------------------------
    if r["mqt"]:
        add("## MQT combined-flag composition\n")
        add("| Outcome | Count | Seed rate (mean ± SD) |\n|---|---:|---:|")
        for m in r["mqt"]:
            add(f"| {m['outcome']} | {m['count']:,} | {fmt(m['seed_rate_mean'], m['seed_rate_sd'], pct=True)} |")
        add(f"\nProvenance: per-mutant counters `run_fail` / `run_unevaluable` from the MQT scan "
            f"({author_ref('mqt_flag')}) → {our_ref('records.py', 'csv_mqt')}; per-seed rates at "
            f"{our_ref(ME, 'mqt_composition')}. Authors: {author_ref('mqt_diag')}.\n")

    if r.get("timing"):
        add("## Wall-clock time of the evaluation (this machine)\n")
        add("| Column in rq3_timing csv | Circuits | Mean s | Median s | Max s | Total h |\n|---|---:|---:|---:|---:|---:|")
        for t in r["timing"]:
            add(f"| {t['column']} | {t['circuits']} | {t['mean']:.2f} | {t['median']:.2f} | {t['max']:.2f} | {t['total_hours']:.2f} |")
        add(f"\nThese are simulator wall-clock times of step04 ({our_ref('step04_rq3_mutants.py', 'evaluate_circuit')}), "
            "not quantum-hardware runtimes.\n")

    add("## Data lineage\n")
    add("```")
    add("quantum_circuits/*.qasm ── step01 (load) ── step02 (Alg.1 candidates, Alg.2 cones, Qmax=24 plan)")
    add("inputs/rq3_single_error_manifest.json ── step03 (mutants; seeds 1-5, or new seeds)")
    add("step04: rq3_realexec_eval.evaluate_circuit per circuit ──> data/rq3_mutants_<tag>.csv")
    add("                                                       └─> data/rq3_method_results_<tag>.csv")
    add("step05: rq3_realexec_eval.false_alarm_circuit per circuit ─> data/rq3_false_alarms_<tag>.csv")
    add("extract_authors_results.py: results/rq3/* ──> the same CSVs with tag authors_stored")
    add("step06 (this report) ──> results/<tag>/*.csv + this file")
    add("```")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--fa-tag", help="false-alarm CSV tag (default: same as --tag if present, else 'reproduced')")
    args = parser.parse_args()
    fa_tag = args.fa_tag or (args.tag if (common.DATA / f"rq3_false_alarms_{args.tag}.csv").exists()
                             else "reproduced")
    result = build(args.tag, fa_tag)
    out_dir = common.RESULTS / args.tag
    write_tables(out_dir, result)
    report = out_dir / f"RQ3_results_{args.tag}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(markdown(args.tag, fa_tag, result), encoding="utf-8")
    print(f"wrote {report}")


if __name__ == "__main__":
    main()
