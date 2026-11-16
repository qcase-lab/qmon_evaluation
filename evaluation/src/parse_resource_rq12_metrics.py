"""Turn the four CSVs written by resources_rq2_metrics.py into one Markdown file.

Run from the repo root, AFTER resources_rq2_metrics.py has finished:

    python evaluation/src/resources_tables_md.py

Reads  (evaluation/results/):
    resources_planned_runs.csv    QMON runs B vs assertion-baseline runs K (paper Table IV)
    resources_rq2_summary.csv     distributions per batch / per circuit, All 310 and RQ3 238
    resources_per_circuit.csv     one row per circuit (310 rows)
    resources_per_batch.csv       one row per batch circuit (7,215 rows; only counted here,
                                  its distributions are already in resources_rq2_summary.csv)
Writes (evaluation/results/):
    resources_tables.md           1. planned runs   2. distributions   3. per family
                                  Appendix A. every circuit

No qiskit needed: standard library only.
"""

import csv                           # read the four CSV files
import re                            # strip "_indep_qiskit_<n>.qasm" to get the family name
import statistics                    # mean, median for the per-family table
from collections import defaultdict  # group circuits by family
from pathlib import Path             # file paths

RESULTS = Path(__file__).resolve().parents[1] / "results"   # evaluation/results/ (same as OUT_DIR
                                                            # in resources_rq2_metrics.py)
OUT_FILE = RESULTS / "resources_tables.md"                  # the Markdown file this script writes
QMAX = 24                                                   # qubit budget used for these results
SHOTS = 8192                                                # shots per batch, as in the paper


# ============================================================================
# Helpers
# ============================================================================
def read_csv(name):
    """All rows of evaluation/results/<name> as a list of dicts (column name -> text)."""
    with (RESULTS / name).open(newline="") as f:           # newline="" is what csv expects
        return list(csv.DictReader(f))                      # first line = column names


def num(text):
    """CSV text -> int or float. '1,626' -> 1626 (summary files use thousands separators)."""
    value = float(text.replace(",", ""))                    # drop separators, parse
    return int(value) if value.is_integer() else value      # keep whole numbers as int


def fmt(x):
    """Same style as resources_rq2_metrics.fmt: integers with separators, else 2 decimals."""
    if isinstance(x, bool):                                 # rq3 flag: tick or blank
        return "✓" if x else ""
    if isinstance(x, str):                                  # already formatted / a label
        return f"{int(x):,}" if x.isdigit() else x          # '7215' -> '7,215' (n column)
    return f"{x:,.0f}" if float(x).is_integer() else f"{x:,.2f}"


def md_table(header, rows, align=None):
    """A Markdown table. align: one of '---' (left), ':-:' (centre), '--:' (right) per column;
    default = first column left, all others right (numbers)."""
    align = align or ["---"] + ["--:"] * (len(header) - 1)
    lines = ["| " + " | ".join(header) + " |",              # header row
             "|" + "|".join(align) + "|"]                   # alignment row
    for row in rows:                                        # one line per data row
        lines.append("| " + " | ".join(fmt(c) for c in row) + " |")
    return "\n".join(lines)


def family(circuit):
    """'qft_indep_qiskit_10.qasm' -> 'qft' (the benchmark family, size removed)."""
    return re.sub(r"_indep_qiskit_\d+\.qasm$", "", circuit)


def short_name(circuit):
    """'qft_indep_qiskit_10.qasm' -> 'qft_10' (keeps the appendix table narrow)."""
    return circuit.replace("_indep_qiskit", "").removesuffix(".qasm")


# ============================================================================
# Sections
# ============================================================================
def section_planned_runs(rows):
    """1. QMON batches B vs baseline runs K for the RQ3 circuits (paper Table IV)."""
    header = list(rows[0])                                  # columns exactly as in the CSV
    out = ["## 1. Planned runs per full scan: QMON vs assertion baselines (RQ3)\n",
           "QMON executes one run per batch (B); an assertion baseline executes one run per "
           "checkpoint (K). The last column is what the paper reports (mean / median / P75).\n",
           md_table(header, [[r[c] for c in header] for r in rows])]
    return "\n".join(out)


def section_distributions(rows):
    """2. One table per scope of resources_rq2_summary.csv (Scope column dropped)."""
    header = [c for c in rows[0] if c != "Scope"]           # Metric, n, Mean, ..., Max
    scopes = list(dict.fromkeys(r["Scope"] for r in rows))  # scopes in file order, no repeats
    out = ["## 2. Resource distributions (before transpilation)\n",
           "Per batch = one value per batch circuit. Per circuit = one value per source "
           "circuit (totals or maxima over its batches). Ratios are batch circuit / original "
           "circuit. Percentiles are nearest-rank. "
           "µop (Eq. 9) = (B·m + G_replay + 2·E_deploy) / m.\n"]
    for letter, scope in zip("abcdefgh", scopes):           # 2a, 2b, ... one per scope
        table_rows = [[r[c] for c in header] for r in rows if r["Scope"] == scope]
        out += [f"### 2{letter}. {scope}\n", md_table(header, table_rows), ""]
    return "\n".join(out)


def section_families(circuits):
    """3. Per-family aggregates computed from resources_per_circuit.csv."""
    groups = defaultdict(list)                              # family -> its circuit rows
    for r in circuits:
        groups[family(r["circuit"])].append(r)
    header = ["Family", "Circuits", "RQ3", "Qubits", "Mean B", "Max B",
              "Mean K_qmon", "Mean K (baseline)", "Dropped groups",
              "Max depth ratio", "Median µop"]
    rows = []
    for name in sorted(groups):                             # families alphabetically
        g = groups[name]
        q = [r["num_qubits"] for r in g]                    # circuit sizes in this family
        rows.append([
            name,
            len(g),                                                   # circuits in family
            sum(r["rq3"] for r in g),                                 # of which in RQ3 238
            f"{min(q)}–{max(q)}" if min(q) != max(q) else str(q[0]),  # qubit range
            statistics.mean(r["batches_B"] for r in g),               # runs per full scan
            max(r["batches_B"] for r in g),
            statistics.mean(r["qmon_checkpoints_Kqmon"] for r in g),  # QMON checkpoints
            statistics.mean(r["baseline_runs_K"] for r in g),         # baseline runs
            sum(r["dropped_groups"] for r in g),                      # groups > Qmax budget
            max(r["depth_ratio_max"] for r in g),                     # worst batch depth
            statistics.median(r["mu_op"] for r in g),                 # Eq. 9 multiplier
        ])
    out = [f"## 3. Per-family summary (all {len(circuits)} circuits)\n",
           "Aggregated from resources_per_circuit.csv. Dropped groups = monitor groups whose "
           f"ancilla demand exceeds Qmax − Qbase, so they fit in no batch.\n",
           md_table(header, rows)]
    return "\n".join(out)


def section_appendix(circuits):
    """Appendix A. Every row of resources_per_circuit.csv, with short column names."""
    columns = [                                             # (Markdown header, CSV column)
        ("Circuit", "circuit"), ("RQ3", "rq3"), ("Q", "num_qubits"), ("m", "gates_m"),
        ("B", "batches_B"), ("Shots", "shots"), ("K_qmon", "qmon_checkpoints_Kqmon"),
        ("Mid", "mid_circuit_checkpoints"), ("Final", "final_reads"),
        ("Drop", "dropped_groups"), ("K_base", "baseline_runs_K"),
        ("Max Q/batch", "max_qubits_per_batch"), ("Max anc/batch", "max_ancillas_per_batch"),
        ("Replay", "replay_gates_total"), ("+2q", "two_qubit_gates_added_total"),
        ("Depth×", "depth_ratio_max"), ("Ops", "operations_full_scan"), ("µop", "mu_op")]
    header = [h for h, _ in columns]
    rows = [[short_name(r["circuit"])] + [r[c] for _, c in columns[1:]] for r in circuits]
    out = [f"## Appendix A. Per-circuit resources (all {len(circuits)} circuits)\n",
           "Q = qubits, m = unitary gates, B = batches, Shots = B × 8,192, "
           "K_qmon = QMON checkpoints (Mid + Final), Mid = mid-circuit checkpoints, "
           "Final = final reads (free), Drop = dropped groups, K_base = baseline runs, "
           "Replay = replay gates (full scan), +2q = 2-qubit gates added (full scan), "
           "Depth× = max depth ratio, Ops = operations (full scan), µop = Eq. 9. "
           "✓ = in the RQ3 238 set.\n",
           md_table(header, rows, ["---", ":-:"] + ["--:"] * (len(header) - 2))]
    return "\n".join(out)


# ============================================================================
# Main
# ============================================================================
def main():
    planned = read_csv("resources_planned_runs.csv")        # already formatted text
    summary = read_csv("resources_rq2_summary.csv")         # already formatted text
    circuits = read_csv("resources_per_circuit.csv")        # raw numbers as text
    batches = read_csv("resources_per_batch.csv")           # only counted below

    for r in circuits:                                      # text -> Python values
        for column, value in r.items():
            if column == "circuit":
                continue                                    # keep the file name as text
            elif column == "rq3":
                r[column] = value == "True"                 # CSV wrote True / False
            else:
                r[column] = num(value)                      # every other column is a number

    n_rq3 = sum(r["rq3"] for r in circuits)                 # 238 expected
    n_batches = sum(r["batches_B"] for r in circuits)       # must equal per-batch rows
    assert n_batches == len(batches), (                     # the two files must agree
        f"per-circuit B sums to {n_batches}, per-batch file has {len(batches)} rows")

    parts = [
        f"# QMON resource metrics (Qmax = {QMAX}, before transpilation)\n",
        f"Generated by `evaluation/src/resources_tables_md.py` from the CSVs written by "
        f"`resources_rq2_metrics.py`. {len(circuits)} circuits (RQ2 set), {n_rq3} of them in "
        f"the RQ3 set; {len(batches):,} batch circuits in total; {SHOTS:,} shots per batch. "
        f"The per-batch file is too long for a table; its distributions are in 2a and 2c.\n",
        section_planned_runs(planned), "",
        section_distributions(summary),
        section_families(circuits), "",
        section_appendix(circuits), "",
    ]
    OUT_FILE.write_text("\n".join(parts), encoding="utf-8")   # utf-8: the file uses µ, ✓, ×
    print(f"wrote {OUT_FILE}")


if __name__ == "__main__":
    main()