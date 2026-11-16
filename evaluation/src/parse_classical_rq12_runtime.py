"""Turn the CSVs written by classical_planning_runtime.py into tables.

Run from the repo root, AFTER classical_planning_runtime.py has finished:

    python evaluation/src/parse_timing_rq12_metrics.py

Reads  (evaluation/results/):
    timing_per_circuit.csv   one row per circuit: seconds per stage, runs per stage, ILP flags
    environment.txt          machine and package versions
Writes (evaluation/results/):
    timing_tables.md         1. setup   2. per-stage distributions (+ exact totals, shares)
                             3. ILP refinement   4. slowest circuits   5. per family
                             6. repeats used     Appendix A. every circuit
    timing_table.tex         the paper's planning-time table (tab:planning), ready to paste

Every number is recomputed from timing_per_circuit.csv, so the totals are exact sums
(not mean x n). timing_rq2_summary.csv is not read: its values are rounded.

No qiskit needed: standard library only.
"""

import csv                           # read the CSV file
import math                          # ceil() for nearest-rank percentiles
import re                            # strip "_indep_qiskit_<n>.qasm" to get the family name
import statistics                    # mean, median
from collections import defaultdict  # group circuits by family
from pathlib import Path             # file paths

RESULTS = Path(__file__).resolve().parents[1] / "results"   # evaluation/results/
MD_FILE = RESULTS / "timing_tables.md"                      # the Markdown file this writes
TEX_FILE = RESULTS / "timing_table.tex"                     # the LaTeX table this writes
QMAX = 24                                                   # qubit budget used for these runs
REPEATS = 5                                                 # runs per stage in the timing script
ILP_CAP_S = 600                                             # ILP time limit (s)
SLOWEST = 10                                                # rows in "slowest circuits"

# (CSV column, label) for every timed stage, in the paper's order.
# "Partition" = FFD + ILP as one call (partition_nodes); total = selection + final reads
# + cone tracing + grouping + partition + construction.
STAGES = [("t_selection_s", "Checkpoint selection (Algorithm 1)"),
          ("t_final_reads_s", "Final-read split"),
          ("t_cone_tracing_s", "Cone tracing (Algorithm 2)"),
          ("t_grouping_s", "Grouping / ancilla accounting"),
          ("t_ffd_s", "FFD packing"),
          ("t_ilp_s", "ILP refinement (circuits where it ran)"),
          ("t_partition_s", "Partition = FFD + ILP"),
          ("t_construction_s", "Batch circuit construction"),
          ("t_planning_total_s", "Total planning time")]
# The stages that add up to the total (FFD and ILP are inside "partition").
PARTS = ["t_selection_s", "t_final_reads_s", "t_cone_tracing_s", "t_grouping_s",
         "t_partition_s", "t_construction_s"]
# Repeat-count column for each stage (how many runs its median is based on).
RUN_COUNTS = [("n_selection", "Checkpoint selection"), ("n_final_reads", "Final-read split"),
              ("n_cone_tracing", "Cone tracing"), ("n_grouping", "Grouping"),
              ("n_ffd", "FFD packing"), ("n_partition", "Partition (FFD + ILP)"),
              ("n_construction", "Construction")]


# ============================================================================
# Reading
# ============================================================================
def read_circuits():
    """timing_per_circuit.csv -> list of dicts with real numbers / booleans."""
    with (RESULTS / "timing_per_circuit.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))                      # first line = column names
    out = []
    for r in rows:
        c = {"circuit": r["circuit"],
             "rq3": r["rq3"] == "True",                     # CSV stores booleans as text
             "num_qubits": int(r["num_qubits"]),
             "gates": int(r["gates"]),
             "ffd_batches": int(r["ffd_batches"]),          # batches after FFD alone
             "batches": int(r["batches"]),                  # batches after FFD + ILP
             "ilp_triggered": r["ilp_triggered"] == "True",
             "ilp_hit_cap": r["ilp_hit_cap"] == "True",     # "" when not triggered -> False
             "ilp_saved_batch": r["ilp_saved_batch"] == "True"}
        for col, _ in STAGES:                               # seconds; "" (ILP not run) -> None
            c[col] = float(r[col]) if r[col] != "" else None
        for col, _ in RUN_COUNTS:                           # runs behind each median
            c[col] = int(r[col])
        out.append(c)
    return out


def read_environment():
    """environment.txt -> list of its lines (empty list if the file is missing)."""
    path = RESULTS / "environment.txt"
    return path.read_text().splitlines() if path.exists() else []


# ============================================================================
# Statistics and formatting
# ============================================================================
def describe(values):
    """mean, min, p25, median, p75, max (nearest-rank, same as the timing script)."""
    v = sorted(values)
    n = len(v)
    rank = lambda p: v[max(math.ceil(p * n), 1) - 1]       # nearest-rank percentile
    return [statistics.mean(v), v[0], rank(0.25), statistics.median(v), rank(0.75), v[-1]]


def fmt_s(x):
    """Seconds for Markdown: scientific below 0.01 s, else 3 decimals with separators."""
    return f"{x:.2e}" if x < 0.01 else f"{x:,.3f}"


def tex_s(x):
    """Seconds for the paper table: <0.001, 3 decimals below 1 s, 3 significant digits
    below 100 s, whole seconds with separators above."""
    if x < 0.001:
        return "$<$0.001"
    if x < 1:
        return f"{x:.3f}"
    if x < 100:
        return f"{x:.3g}"
    return f"{x:,.0f}"


def pct(part, whole):
    return f"{100 * part / whole:.1f}%" if whole else ""


def md_table(header, rows, align=None):
    """A Markdown table; first column left, the rest right (numbers) unless align is given."""
    align = align or ["---"] + ["--:"] * (len(header) - 1)
    lines = ["| " + " | ".join(header) + " |",
             "|" + "|".join(align) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def family(circuit):
    """'qft_indep_qiskit_10.qasm' -> 'qft' (benchmark family, size removed)."""
    return re.sub(r"_indep_qiskit_\d+\.qasm$", "", circuit)


def short_name(circuit):
    """'qft_indep_qiskit_10.qasm' -> 'qft_10' (keeps tables narrow)."""
    return circuit.replace("_indep_qiskit", "").removesuffix(".qasm")


def scopes(circuits):
    """The two scopes every table is reported for."""
    return [("All 310", circuits), ("RQ3 238", [c for c in circuits if c["rq3"]])]


# ============================================================================
# Sections
# ============================================================================
def section_setup(env, circuits):
    """1. Machine, versions and timing protocol."""
    out = ["## 1. Setup\n",
           f"{len(circuits)} circuits, Qmax = {QMAX}. Each stage ran up to {REPEATS} times "
           "per circuit and its median is the circuit's value; fewer runs when a stage's runs "
           "passed 60 s, when the ILP was triggered (once) and for construction (always once). "
           "Only QMON's core functions are timed; the authors' verification checks are not. "
           "ILP times include creating a Gurobi environment per solve.\n"]
    out += [f"- {line}" for line in env] or ["- environment.txt not found"]
    return "\n".join(out)


def section_distributions(circuits):
    """2. Per-stage distribution per scope, with exact total and share of total time."""
    header = ["Stage", "n", "Mean (s)", "Min (s)", "P25 (s)", "Median (s)", "P75 (s)",
              "Max (s)", "Total (s)", "Share of total"]
    out = ["## 2. Planning time per stage\n",
           "One value per circuit. Total = exact sum over circuits. Share = stage total / "
           "total planning time. FFD and ILP are shown on their own and inside Partition; "
           "the stages that add up to 100% are selection, final-read split, cone tracing, "
           "grouping, partition and construction.\n"]
    for letter, (scope, subset) in zip("ab", scopes(circuits)):
        grand = sum(c["t_planning_total_s"] for c in subset)   # all planning time in scope
        rows = []
        for col, label in STAGES:
            values = [c[col] for c in subset if c[col] is not None]   # ILP: where it ran
            if not values:
                continue
            total = sum(values)
            rows.append([label, len(values)] + [fmt_s(s) for s in describe(values)]
                        + [f"{total:,.2f}", pct(total, grand)])
        check = sum(sum(c[p] for c in subset) for p in PARTS)   # parts must add up to total
        out += [f"### 2{letter}. {scope}\n", md_table(header, rows),
                f"\nSum of the six parts: {check:,.2f} s (total planning time: {grand:,.2f} s, "
                f"{grand / 60:,.1f} min).\n"]
    return "\n".join(out)


def section_ilp(circuits):
    """3. When the ILP ran, and what it did."""
    header = ["Scope", "Circuits", "ILP triggered", f"Hit {ILP_CAP_S} s cap",
              "Saved a batch", "ILP time, total (s)", "ILP share of planning"]
    rows = []
    for scope, subset in scopes(circuits):
        ran = [c for c in subset if c["ilp_triggered"]]
        ilp_total = sum(c["t_ilp_s"] for c in ran)
        grand = sum(c["t_planning_total_s"] for c in subset)
        rows.append([scope, len(subset), len(ran), sum(c["ilp_hit_cap"] for c in ran),
                     sum(c["ilp_saved_batch"] for c in ran), f"{ilp_total:,.2f}",
                     pct(ilp_total, grand)])
    # Circuits where the ILP mattered: hit the cap or removed a batch.
    detail_header = ["Circuit", "Qubits", "Gates", "FFD batches", "Final batches",
                     "ILP time (s)", "Hit cap", "Saved a batch"]
    detail = [[short_name(c["circuit"]), c["num_qubits"], f"{c['gates']:,}",
               c["ffd_batches"], c["batches"], f"{c['t_ilp_s']:,.3f}",
               "yes" if c["ilp_hit_cap"] else "", "yes" if c["ilp_saved_batch"] else ""]
              for c in sorted(circuits, key=lambda c: -(c["t_ilp_s"] or 0))
              if c["ilp_triggered"] and (c["ilp_hit_cap"] or c["ilp_saved_batch"])]
    out = ["## 3. ILP refinement\n",
           "Triggered when FFD gives more than one batch and at most 120 groups fit the "
           f"budget. Hit cap = ILP time ≥ {ILP_CAP_S} s.\n",
           md_table(header, rows), "",
           "### Circuits where the ILP hit the cap or removed a batch\n",
           md_table(detail_header, detail) if detail else "None."]
    return "\n".join(out)


def section_slowest(circuits):
    """4. The circuits with the longest total planning time, stage by stage."""
    header = ["Circuit", "RQ3", "Qubits", "Gates", "Batches", "Selection", "Cone tracing",
              "Grouping", "Partition", "Construction", "Total (s)", "Largest stage"]
    names = {"t_selection_s": "selection", "t_final_reads_s": "final reads",
             "t_cone_tracing_s": "cone tracing", "t_grouping_s": "grouping",
             "t_partition_s": "partition", "t_construction_s": "construction"}
    rows = []
    for c in sorted(circuits, key=lambda c: -c["t_planning_total_s"])[:SLOWEST]:
        biggest = max(PARTS, key=lambda p: c[p])            # stage with the most time
        rows.append([short_name(c["circuit"]), "✓" if c["rq3"] else "", c["num_qubits"],
                     f"{c['gates']:,}", c["batches"],
                     fmt_s(c["t_selection_s"]), fmt_s(c["t_cone_tracing_s"]),
                     fmt_s(c["t_grouping_s"]), fmt_s(c["t_partition_s"]),
                     fmt_s(c["t_construction_s"]), f"{c['t_planning_total_s']:,.3f}",
                     names[biggest]])
    top = sum(c["t_planning_total_s"] for c in sorted(circuits,
              key=lambda c: -c["t_planning_total_s"])[:SLOWEST])
    grand = sum(c["t_planning_total_s"] for c in circuits)
    out = [f"## 4. The {SLOWEST} slowest circuits\n",
           f"Seconds per stage. These {SLOWEST} circuits take {top:,.1f} s, "
           f"{pct(top, grand)} of all planning time.\n",
           md_table(header, rows)]
    return "\n".join(out)


def section_families(circuits):
    """5. Planning time per benchmark family."""
    groups = defaultdict(list)                              # family -> its circuits
    for c in circuits:
        groups[family(c["circuit"])].append(c)
    header = ["Family", "Circuits", "RQ3", "Qubits", "Median total (s)", "Mean total (s)",
              "Max total (s)", "Family total (s)", "Largest stage (family total)"]
    names = {"t_selection_s": "selection", "t_final_reads_s": "final reads",
             "t_cone_tracing_s": "cone tracing", "t_grouping_s": "grouping",
             "t_partition_s": "partition", "t_construction_s": "construction"}
    rows = []
    for name in sorted(groups):
        g = groups[name]
        q = [c["num_qubits"] for c in g]
        totals = [c["t_planning_total_s"] for c in g]
        biggest = max(PARTS, key=lambda p: sum(c[p] for c in g))
        rows.append([name, len(g), sum(c["rq3"] for c in g),
                     f"{min(q)}–{max(q)}" if min(q) != max(q) else str(q[0]),
                     fmt_s(statistics.median(totals)), fmt_s(statistics.mean(totals)),
                     fmt_s(max(totals)), f"{sum(totals):,.2f}", names[biggest]])
    out = [f"## 5. Per-family summary (all {len(circuits)} circuits)\n", md_table(header, rows)]
    return "\n".join(out)


def section_repeats(circuits):
    """6. How many runs each median is based on."""
    header = ["Stage", f"{REPEATS} runs", "Fewer runs", "Min runs"]
    rows = []
    for col, label in RUN_COUNTS:
        n = [c[col] for c in circuits]
        rows.append([label, sum(x == REPEATS for x in n), sum(x < REPEATS for x in n), min(n)])
    out = ["## 6. Repeats behind each median\n",
           f"Circuits whose value is the median of all {REPEATS} runs, and circuits with "
           "fewer (60 s budget reached, ILP triggered, or construction, which always runs "
           "once).\n",
           md_table(header, rows)]
    return "\n".join(out)


def section_appendix(circuits):
    """Appendix A. Every circuit, seconds per stage."""
    header = ["Circuit", "RQ3", "Qubits", "Gates", "Batches", "Selection", "Final reads",
              "Cone tracing", "Grouping", "FFD", "ILP", "Construction", "Total"]
    rows = [[short_name(c["circuit"]), "✓" if c["rq3"] else "", c["num_qubits"],
             f"{c['gates']:,}", c["batches"], fmt_s(c["t_selection_s"]),
             fmt_s(c["t_final_reads_s"]), fmt_s(c["t_cone_tracing_s"]),
             fmt_s(c["t_grouping_s"]), fmt_s(c["t_ffd_s"]),
             fmt_s(c["t_ilp_s"]) if c["t_ilp_s"] is not None else "",
             fmt_s(c["t_construction_s"]), fmt_s(c["t_planning_total_s"])]
            for c in circuits]
    out = ["## Appendix A. Every circuit (seconds)\n", md_table(header, rows)]
    return "\n".join(out)


# ============================================================================
# LaTeX table for the paper (tab:planning)
# ============================================================================
def latex_table(circuits):
    """Same rows and columns as the paper's planning-time table, with exact totals."""
    rows = [("t_selection_s", "Checkpoint selection"),
            ("t_final_reads_s", "Final-read split"),
            ("t_cone_tracing_s", "Cone tracing"),
            ("t_grouping_s", "Ancilla accounting"),
            ("t_ffd_s", "FFD packing"),
            ("t_ilp_s", "ILP refinement"),
            ("t_construction_s", "Circuit construction")]
    n_ilp = sum(c["ilp_triggered"] for c in circuits)
    lines = [r"\begin{table}[!t]",
             rf"\caption{{Planning time per circuit in seconds ({len(circuits)} circuits; "
             rf"ILP: the {n_ilp} circuits where it is triggered)}}",
             r"\label{tab:planning}",
             r"\centering",
             r"\footnotesize",
             r"\begin{tabular}{lrrrrr}",
             r"\hline",
             r"Stage & Median & P75 & Mean & Max & Total \\",
             r"\hline"]

    def row(label, values):
        mean, _, _, median, p75, mx = describe(values)
        cells = [tex_s(median), tex_s(p75), tex_s(mean), tex_s(mx), tex_s(sum(values))]
        return f"{label} & " + " & ".join(cells) + r" \\"

    for col, label in rows:
        lines.append(row(label, [c[col] for c in circuits if c[col] is not None]))
    lines += [r"\hline",
              row("Total", [c["t_planning_total_s"] for c in circuits]),
              r"\hline",
              r"\end{tabular}",
              r"\end{table}"]
    return "\n".join(lines) + "\n"


def main():
    circuits = read_circuits()
    env = read_environment()
    sections = [f"# QMON classical planning time (Qmax = {QMAX})\n\n"
                "Generated by `evaluation/src/parse_timing_rq12_metrics.py` from "
                "`timing_per_circuit.csv` (written by `classical_planning_runtime.py`).",
                section_setup(env, circuits),
                section_distributions(circuits),
                section_ilp(circuits),
                section_slowest(circuits),
                section_families(circuits),
                section_repeats(circuits),
                section_appendix(circuits)]
    MD_FILE.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    TEX_FILE.write_text(latex_table(circuits), encoding="utf-8")
    print(f"wrote {MD_FILE}")
    print(f"wrote {TEX_FILE}")


if __name__ == "__main__":
    main()