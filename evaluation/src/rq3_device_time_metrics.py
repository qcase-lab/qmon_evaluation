"""Device-time metrics for RQ3 (bug detection) on fake IBM backends. PART 2 of 2.

Joins the per-shot durations D from Part 1 (rq3_device_time_circuits.py) with the
authors' stored RQ3 results, and turns them into run times with IBM's job-time formula:

    T_run = O_job + S * (t_rep + t_init + D)          S = 8,192 shots per run
      O_job   fixed overhead per job, swept over JOB_OVERHEADS (seconds)
      t_rep   wait between shots, the backend's default_rep_delay
      t_init  reset at the start of each shot, the backend's median reset duration
      D       per-shot duration of the compiled circuit (median over transpiler seeds)

Detection outcomes are NOT recomputed: which method flags which mutant, and at which
checkpoint, comes from results/rq3/rq3_mutant.pkl (noise-free, matches the paper).
Pure Python: needs no qiskit, only the Part 1 cache files and the two pickles.

Run from the repo root:
    python evaluation/src/rq3_device_time_metrics.py --backend kingston

Writes to evaluation/results/:
  device_time_per_circuit_<backend>.csv     full-check cost per circuit x method x O_job
  device_time_per_mutant_<backend>.csv      time to detection per mutant x method x O_job
  device_time_detection_curve_<backend>.csv share of mutants detected by time t
  device_time_summary_<backend>.csv         the tables printed at the end
  device_time_resources_<backend>.csv       resources BEFORE vs AFTER transpiling, one row
                                            per compiled circuit (QMON batch, checkpoint, ...)
  device_time_resources_summary_<backend>.csv
"""

import argparse                      # command-line options
import csv                           # write the output tables
import math                          # ceil() for nearest-rank percentiles, log spacing
import pickle                        # cache files and the authors' result pickles
import random                        # family-level bootstrap
import statistics                    # mean, median
import sys                           # edit the import path
from collections import defaultdict  # group rows
from pathlib import Path             # file paths

REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "src" / "coverage_rq2.py").exists())
sys.path.insert(0, str(REPO / "src"))
from circuit_families import canonical_family_of       # authors' family labels (bootstrap)

SHOTS = 8192                          # shots per run, as in the paper
JOB_OVERHEADS = [0.0, 2.0, 5.0]       # O_job sweep in seconds (IBM's guide: about 2 s)
BASELINES = ["statistical", "proq", "liu"]            # the hardware-runnable baselines
METHODS = ["qmon"] + BASELINES
BOOT = 2000                           # bootstrap resamples, as in the paper
OUT_DIR = Path(__file__).resolve().parents[1] / "results"
RESOURCES_RQ2_CSV = OUT_DIR / "resources_per_batch.csv"   # your pre-transpile resources
RESOURCE_FIELDS = ["qubits", "operations", "depth", "one_qubit_gates", "two_qubit_gates",
                   "swaps", "measures", "resets"]           # same names as Part 1's columns
KINDS = ["original", "qmon", "statistical", "liu", "proq"]
MUTANT_PKL = REPO / "results" / "rq3" / "rq3_mutant.pkl"
FALSE_ALARM_PKL = REPO / "results" / "rq3" / "rq3_falsealarm.pkl"


# ============================================================================
# Small helpers
# ============================================================================
STAT_COLUMNS = ["n", "Mean", "Min", "P25", "Median", "P75", "IQR", "Max"]


def describe(values):
    """n, mean, min, p25, median, p75, IQR (= p75 - p25), max.
    Percentiles are nearest-rank, as in the paper."""
    v = sorted(x for x in values if x is not None)
    if not v:
        return [0] + [None] * (len(STAT_COLUMNS) - 1)
    n = len(v)
    rank = lambda p: v[max(math.ceil(p * n), 1) - 1]
    p25, p75 = rank(0.25), rank(0.75)
    return [n, statistics.mean(v), v[0], p25, statistics.median(v), p75, p75 - p25, v[-1]]


def fmt(x):
    if x is None:
        return "-"
    return f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.3g}"


def print_table(title, header, rows):
    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = lambda r: "  ".join(str(c).ljust(w) for c, w in zip(r, widths))
    print(f"\n{title}\n\n{line(header)}\n" + "  ".join("-" * w for w in widths))
    for r in rows:
        print(line(r))


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def family_bootstrap_median(values_by_circuit, seed=0):
    """Median of per-circuit values with a 95% CI from resampling circuit FAMILIES
    (the paper's family-level bootstrap): circuits of one family move together."""
    families = defaultdict(list)
    for circuit, value in values_by_circuit.items():
        if value is not None:
            families[canonical_family_of(circuit)].append(value)
    names = list(families)
    if not names:
        return None, None, None
    rng = random.Random(seed)
    meds = []
    for _ in range(BOOT):
        sample = [v for name in rng.choices(names, k=len(names)) for v in families[name]]
        meds.append(statistics.median(sample))
    meds.sort()
    point = statistics.median([v for vs in families.values() for v in vs])
    return point, meds[int(0.025 * BOOT)], meds[int(0.975 * BOOT) - 1]


# ============================================================================
# Per-shot durations -> run times
# ============================================================================
def median_durations(cache):
    """(kind, label) -> D in seconds, median over the transpiler seeds."""
    by_circuit = defaultdict(list)
    for row in cache["rows"]:
        if row["kind"] != "qmon_mutant":                          # recheck rows: see below
            by_circuit[(row["kind"], row["label"])].append(row["duration_s"])
    return {k: statistics.median(v) for k, v in by_circuit.items()}


def run_times(cache, o_job):
    """Per method, the list of T_run for every run of a FULL check, in scan order.
    None marks a run whose circuit could not be built or timed (Part 1 'failures')."""
    D = median_durations(cache)
    b = cache["backend"]
    per_shot_overhead = b["rep_delay_s"] + b["reset_s_median"]   # t_rep + t_init
    T = lambda d: None if d is None else o_job + SHOTS * (per_shot_overhead + d)
    nodes = cache["nodes"]                                        # ascending (gate, qubit)
    runs = {
        "qmon": [T(D.get(("qmon", i))) for i in range(cache["B"] or 0)],     # FFD order
        "statistical": [T(D.get(("statistical", g))) for g, _ in nodes],     # one per node
        "liu": [T(D.get(("liu", n))) for n in nodes],
        "proq": [T(D.get(("proq", n))) for n in nodes],
    }
    gate_s = {                                                    # S x D summed over runs
        "qmon": [D.get(("qmon", i)) for i in range(cache["B"] or 0)],
        "statistical": [D.get(("statistical", g)) for g, _ in nodes],
        "liu": [D.get(("liu", n)) for n in nodes],
        "proq": [D.get(("proq", n)) for n in nodes],
    }
    return runs, gate_s, D, per_shot_overhead


def total(values):
    """Sum, or None if any run is missing (an incomplete method is not compared)."""
    return None if any(v is None for v in values) else sum(values)


# ============================================================================
# Metrics
# ============================================================================
def per_circuit_rows(cache, fa_record, o_job):
    """Full-check cost of one circuit for every method (Metrics: full-check time,
    breakdown, one-job packing, overhead ratio, clean-check false alarms)."""
    runs, gate_s, D, per_shot = run_times(cache, o_job)
    d_orig = D.get(("original", None))
    batch_ratios = [D[("qmon", i)] / d_orig for i in range(cache["B"] or 0)
                    if ("qmon", i) in D and d_orig]
    rows = []
    for m in METHODS:
        n = len(runs[m])                                          # runs in a full check
        full = total(runs[m])
        gate = None if total(gate_s[m]) is None else SHOTS * total(gate_s[m])
        fa = fa_record["methods"].get(m, {}) if fa_record else {}
        rows.append({
            "job_overhead_s": o_job, "circuit": cache["circuit"],
            "family": canonical_family_of(cache["circuit"]), "method": m,
            "runs": n,                                            # B for QMON, K for baselines
            "full_check_s": full,                                 # one job per run
            "gate_time_s": gate,                                  # S x sum(D)
            "shot_overhead_s": SHOTS * per_shot * n,              # S x (t_rep + t_init) x runs
            "job_overhead_total_s": o_job * n,                    # O_job x runs
            "one_job_s": None if gate is None else o_job + gate + SHOTS * per_shot * n,
            "original_D_s": d_orig,
            "max_batch_D_ratio": max(batch_ratios) if m == "qmon" and batch_ratios else None,
            "false_alarm": fa.get("false_alarm") if fa.get("complete") else None,
        })
    return rows


def per_mutant_rows(cache, record, o_job):
    """Time to detection for one mutant (Metrics: TTD for baselines, QMON all batches,
    QMON early stop, time spent on misses)."""
    runs, _, _, _ = run_times(cache, o_job)
    nodes = cache["nodes"]
    row = {"job_overhead_s": o_job, "circuit": record["circuit"],
           "slot_id": record["slot_id"], "scope_class": record.get("scope_class"),
           "in_scope_qmon": record.get("in_scope_qmon")}
    for m in METHODS:
        res = record["methods"].get(m)
        if not res or not res.get("complete"):                    # incomplete in the pkl
            row.update({f"{m}_detected": None, f"{m}_runs": None, f"{m}_time_s": None})
            continue
        detected = bool(res["detected"])
        if m == "qmon":
            # The paper's protocol: QMON decides after running ALL B batches.
            row["qmon_detected"] = detected
            row["qmon_runs"] = len(runs["qmon"])
            row["qmon_time_s"] = total(runs["qmon"])
            # Early stop: stop after the batch holding the first flagged checkpoint.
            # The pkl stores the first flag in GATE order; any flag in an earlier
            # batch would stop sooner, so this is an UPPER BOUND on early-stop time.
            if detected:
                first = tuple(res["first_node"])
                b = 0 if first in set(cache["lastgate"]) else cache["batch_of"][first[0]]
                row["qmon_es_runs_ub"] = b + 1
                row["qmon_es_time_s_ub"] = total(runs["qmon"][:b + 1])
            else:                                                 # a miss costs everything
                row["qmon_es_runs_ub"] = len(runs["qmon"])
                row["qmon_es_time_s_ub"] = total(runs["qmon"])
        else:
            # Baselines scan checkpoints in ascending order and stop at the first flag.
            idx = nodes.index(tuple(res["first_node"])) if detected else len(nodes) - 1
            row[f"{m}_detected"] = detected
            row[f"{m}_runs"] = idx + 1
            row[f"{m}_time_s"] = total(runs[m][:idx + 1])
    return row


def ratio(a, b):
    return a / b if a is not None and b else None


def resource_rows(cache):
    """Transpilation overhead (Metrics: resources before vs after transpiling).
    One row per compiled circuit: the counts as QMON / the baseline builds it (before)
    and on the device after IBM's compiler (after: native gates, routing SWAPs),
    median over transpiler seeds. Also each circuit relative to the ORIGINAL circuit,
    before and after, to see whether transpiling makes QMON's overhead bigger."""
    groups = defaultdict(list)
    for r in cache["rows"]:
        if r["kind"] != "qmon_mutant":
            groups[(r["kind"], r["label"])].append(r)
    med = lambda rs, f: statistics.median(r[f] for r in rs)
    orig = groups.get(("original", None))                         # reference circuit
    out = []
    for (kind, label), rs in groups.items():
        row = {"circuit": cache["circuit"], "kind": kind, "label": repr(label),
               "seeds": len(rs), "duration_s": med(rs, "duration_s")}
        for f in RESOURCE_FIELDS:
            row[f"before_{f}"] = rs[0][f"before_{f}"]             # same for every seed
            row[f"after_{f}"] = med(rs, f"after_{f}")             # depends on the seed
        row["routing_swaps"] = med(rs, "routing_swaps")           # SWAPs routing inserted
        row["routing_swaps_range"] = (max(r["routing_swaps"] for r in rs)
                                      - min(r["routing_swaps"] for r in rs))   # seed spread
        # Growth from transpiling (after / before) for this circuit.
        for f in ("operations", "depth", "two_qubit_gates"):
            row[f"{f}_growth"] = ratio(row[f"after_{f}"], row[f"before_{f}"])
        # Overhead vs the original circuit, before and after transpiling.
        if orig:
            for f in ("operations", "depth", "two_qubit_gates"):
                row[f"{f}_vs_original_before"] = ratio(row[f"before_{f}"], orig[0][f"before_{f}"])
                row[f"{f}_vs_original_after"] = ratio(row[f"after_{f}"], med(orig, f"after_{f}"))
        out.append(row)
    return out


def check_against_rq2_resources(rows, caches):
    """Sanity check: our BEFORE counts for QMON batches should equal your
    resources_per_batch.csv (same circuit, same batch), where the RQ3 plan is the
    RQ2 plan. Returns (matches, compared, examples of mismatches)."""
    if not RESOURCES_RQ2_CSV.exists():
        return None
    theirs = {}
    with RESOURCES_RQ2_CSV.open() as f:
        for r in csv.DictReader(f):
            theirs[(r["circuit"], r["batch"])] = r
    pairs = [("before_qubits", "qubits"), ("before_operations", "operations"),
             ("before_depth", "depth"), ("before_two_qubit_gates", "two_qubit_gates")]
    matches, compared, bad = 0, 0, []
    for row in rows:
        if row["kind"] != "qmon" or caches[row["circuit"]].get("plan_regrouped"):
            continue                                              # regrouped: batches differ
        other = theirs.get((row["circuit"], row["label"]))
        if other is None:
            continue
        compared += 1
        if all(int(row[a]) == int(other[b]) for a, b in pairs):
            matches += 1
        elif len(bad) < 5:
            bad.append((row["circuit"], row["label"],
                        {b: (row[a], other[b]) for a, b in pairs}))
    return matches, compared, bad


def detection_curve(mutant_rows, o_job, points=60):
    """Share of the non-equivalent mutants each method has detected by time t."""
    rows_o = [r for r in mutant_rows if r["job_overhead_s"] == o_job]
    series = {"qmon (all batches)": ("qmon_detected", "qmon_time_s"),
              "qmon (early stop, upper bound)": ("qmon_detected", "qmon_es_time_s_ub")}
    series.update({m: (f"{m}_detected", f"{m}_time_s") for m in BASELINES})
    times = [r[t] for r in rows_o for _, t in series.values() if r.get(t)]
    if not times:
        return []
    lo, hi = math.log10(min(times)), math.log10(max(times))
    grid = [10 ** (lo + (hi - lo) * i / (points - 1)) for i in range(points)]
    out = []
    for name, (det, t) in series.items():
        n = len(rows_o)                                           # denominator: all of them
        hits = sorted(r[t] for r in rows_o if r.get(det) and r.get(t) is not None)
        for g in grid:
            out.append({"job_overhead_s": o_job, "method": name, "time_s": g,
                        "detected_share": sum(1 for h in hits if h <= g) / n})
    return out


# ============================================================================
# Main
# ============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="kingston")
    args = parser.parse_args()

    cache_dir = OUT_DIR / "device_time_cache" / args.backend
    caches = {}
    for path in sorted(cache_dir.glob("*.pkl")):
        with path.open("rb") as f:
            c = pickle.load(f)
        if "error" not in c:
            caches[c["circuit"]] = c
    print(f"{len(caches)} circuits timed on {args.backend}")
    with MUTANT_PKL.open("rb") as f:
        mutants = pickle.load(f)["records"]
    with FALSE_ALARM_PKL.open("rb") as f:
        false_alarms = {r["circuit"]: r for r in pickle.load(f)["records"]}

    # ---- Consistency with the stored run ---------------------------------------
    for key, c in caches.items():
        fa = false_alarms[key]
        assert c["plan_sha256"] == fa["qmon_plan"]["plan_sha256"], key   # same QMON plan
        assert (c["K"], c["K_qmon"], c["B"]) == (fa["K"], fa["K_qmon"], fa["B"]), key

    circuit_rows, mutant_rows, curve_rows = [], [], []
    for o_job in JOB_OVERHEADS:
        for key, c in caches.items():
            circuit_rows += per_circuit_rows(c, false_alarms.get(key), o_job)
        for record in mutants:
            if record["equivalent"] or record["circuit"] not in caches:
                continue                                          # the 710 are never run
            mutant_rows.append(per_mutant_rows(caches[record["circuit"]], record, o_job))
        curve_rows += detection_curve(mutant_rows, o_job)

    tag = args.backend
    write_csv(OUT_DIR / f"device_time_per_circuit_{tag}.csv", circuit_rows)
    write_csv(OUT_DIR / f"device_time_per_mutant_{tag}.csv", mutant_rows)
    write_csv(OUT_DIR / f"device_time_detection_curve_{tag}.csv", curve_rows)

    # ---- Summary tables ----------------------------------------------------------
    header = ["O_job (s)", "Metric", "Method"] + STAT_COLUMNS
    summary = []
    for o_job in JOB_OVERHEADS:
        cr = [r for r in circuit_rows if r["job_overhead_s"] == o_job]
        mr = [r for r in mutant_rows if r["job_overhead_s"] == o_job]
        for m in METHODS:
            summary.append([o_job, "Full-check time per circuit (s)", m]
                           + describe(r["full_check_s"] for r in cr if r["method"] == m))
        for m in METHODS:
            summary.append([o_job, "Full-check time, one job (s)", m]
                           + describe(r["one_job_s"] for r in cr if r["method"] == m))
        for m in METHODS:
            summary.append([o_job, "Time to detection, detected mutants (s)", m]
                           + describe(r[f"{m}_time_s"] for r in mr if r.get(f"{m}_detected")))
        summary.append([o_job, "Time to detection, detected mutants (s)", "qmon early stop (UB)"]
                       + describe(r["qmon_es_time_s_ub"] for r in mr if r.get("qmon_detected")))
        for m in METHODS:
            summary.append([o_job, "Time spent on missed mutants (s)", m]
                           + describe(r[f"{m}_time_s"] for r in mr
                                      if r.get(f"{m}_detected") is False))
    rows = [[o, metric, m] + [fmt(x) for x in stats]
            for o, metric, m, *stats in summary]
    print_table(f"RQ3 device-time estimates on {args.backend} ({SHOTS:,} shots per run)",
                header, rows)

    # QMON / baseline full-check ratio per circuit, family-level bootstrap CI.
    ratio_header = ["O_job (s)", "QMON / baseline", "Median ratio", "95% CI (family bootstrap)",
                    "Mean ratio", "P25", "P75", "IQR", "Circuits where QMON is faster"]
    ratio_rows = []
    for o_job in JOB_OVERHEADS:
        cr = [r for r in circuit_rows if r["job_overhead_s"] == o_job]
        full = {(r["circuit"], r["method"]): r["full_check_s"] for r in cr}
        for m in BASELINES:
            ratios = {k: (full[(k, "qmon")] / full[(k, m)]
                          if full.get((k, "qmon")) and full.get((k, m)) else None)
                      for k in caches}
            point, lo, hi = family_bootstrap_median(ratios)
            valid = [v for v in ratios.values() if v is not None]
            _, mean_r, _, p25_r, _, p75_r, iqr_r, _ = describe(valid)
            ratio_rows.append([o_job, m, fmt(point), f"[{fmt(lo)}, {fmt(hi)}]",
                               fmt(mean_r), fmt(p25_r), fmt(p75_r), fmt(iqr_r),
                               f"{sum(1 for v in valid if v < 1)} / {len(valid)}"])
    print_table("Full-check time ratio per circuit (below 1 = QMON faster)",
                ratio_header, ratio_rows)

    # Robustness: building batches on the mutant instead of the original.
    rel = []
    for c in caches.values():
        first_seed = c["seeds"][0]
        base = {r["label"]: r["duration_s"] for r in c["rows"]
                if r["kind"] == "qmon" and r["seed"] == first_seed}
        for r in c["rows"]:
            if r["kind"] == "qmon_mutant" and base.get(r["label"][1]):
                rel.append(abs(r["duration_s"] - base[r["label"][1]]) / base[r["label"][1]])
    if rel:
        print(f"\nMutant recheck: {len(rel)} batches, relative change in D: "
              f"median {statistics.median(rel):.2%}, max {max(rel):.2%}")

    with (OUT_DIR / f"device_time_summary_{tag}.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
        w.writerow([])
        w.writerow(ratio_header)
        w.writerows(ratio_rows)

    # ---- Transpilation overhead: before vs after --------------------------------
    res_rows = [row for c in caches.values() for row in resource_rows(c)]
    write_csv(OUT_DIR / f"device_time_resources_{tag}.csv", res_rows)
    res_header = ["Circuit kind", "Metric"] + STAT_COLUMNS
    res_metrics = [("Qubits, before", "before_qubits"),
                   ("Physical qubits, after", "after_qubits"),
                   ("2-qubit gates, before", "before_two_qubit_gates"),
                   ("2-qubit gates (CZ), after", "after_two_qubit_gates"),
                   ("Routing SWAPs added", "routing_swaps"),
                   ("1-qubit gates, before", "before_one_qubit_gates"),
                   ("1-qubit gates, after", "after_one_qubit_gates"),
                   ("Operations, before", "before_operations"),
                   ("Operations, after", "after_operations"),
                   ("Depth, before", "before_depth"),
                   ("Depth, after", "after_depth"),
                   ("2-qubit growth (after / before)", "two_qubit_gates_growth"),
                   ("Depth growth (after / before)", "depth_growth"),
                   ("2-qubit gates vs original, before", "two_qubit_gates_vs_original_before"),
                   ("2-qubit gates vs original, after", "two_qubit_gates_vs_original_after"),
                   ("Depth vs original, before", "depth_vs_original_before"),
                   ("Depth vs original, after", "depth_vs_original_after"),
                   ("Measures, after (check = before)", "after_measures"),
                   ("Resets, after (check = before)", "after_resets")]
    res_summary = []
    for kind in KINDS:
        rk = [r for r in res_rows if r["kind"] == kind]
        for label, field in res_metrics:
            stats = describe(r.get(field) for r in rk)
            res_summary.append([kind, label] + [fmt(x) for x in stats])
    print_table(f"Resources before vs after transpiling to {args.backend} "
                "(one value per compiled circuit; median over seeds)",
                res_header, res_summary)
    with (OUT_DIR / f"device_time_resources_summary_{tag}.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(res_header)
        w.writerows(res_summary)

    # Did the compiler keep every mid-circuit measurement and reset?
    lost = [(r["circuit"], r["kind"], r["label"]) for r in res_rows
            if r["after_measures"] < r["before_measures"] or r["after_resets"] < r["before_resets"]]
    print(f"\nCircuits where transpiling removed a measure or reset: {len(lost)} {lost[:5]}")
    check = check_against_rq2_resources(res_rows, caches)
    if check:
        matches, compared, bad = check
        print(f"QMON batches matching resources_per_batch.csv (qubits, ops, depth, 2q): "
              f"{matches} / {compared}" + (f"; first mismatches: {bad}" if bad else ""))


if __name__ == "__main__":
    main()