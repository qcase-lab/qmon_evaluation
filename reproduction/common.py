"""Shared paths, settings and helpers for the QMON reproduction framework.

Every stepXX_*.py script imports this file first. It does three jobs:

  1. finds the authors' repository (the folder that holds src/rq3_realexec_eval.py)
     and puts the authors' src/ folder on the import path, so we call THEIR functions;
  2. defines where our outputs go (reproduction/data and reproduction/results);
  3. provides small helpers: CSV read/write, the authors' family label, and a
     "provenance" resolver that looks up the CURRENT line number of a piece of
     the authors' code (or ours) so the results report can say
     "this value was decided at rq3_realexec_eval.py:2357".

Nothing in this file runs a simulation; it only needs the Python standard library.
"""

import csv                                   # read/write the CSV tables
import json                                  # read/write JSON side files
import os                                    # environment variables (QMON_REPO override)
import re                                    # regex search used by the provenance resolver
import sys                                   # edit the import path
from pathlib import Path                     # file paths that work on Windows and Linux

# --------------------------------------------------------------------------------------
# 1. Locate the authors' repository
# --------------------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent       # .../quantum_monitoring-main/reproduction


def _find_repo():
    """Return the repo root = first folder (this one or a parent) containing the
    authors' src/rq3_realexec_eval.py. QMON_REPO (env var) overrides the search."""
    override = os.environ.get("QMON_REPO")                       # optional manual path
    if override:                                                 # user forced a location
        return Path(override).resolve()
    for folder in [HERE, *HERE.parents]:                         # walk upward from reproduction/
        if (folder / "src" / "rq3_realexec_eval.py").exists():   # the authors' RQ3 evaluator
            return folder                                        # found the repo root
    raise SystemExit("Cannot find the authors' repo (src/rq3_realexec_eval.py). "
                     "Put reproduction/ inside the repo or set QMON_REPO.")


REPO = _find_repo()                          # authors' project root (has src/, inputs/, results/)
SRC = REPO / "src"                           # authors' code
CIRCUIT_DIR = REPO / "quantum_circuits"      # the 310 MQT Bench QASM files
INPUTS = REPO / "inputs"                     # circuit lists + fixed mutation manifest
AUTHORS_RESULTS = REPO / "results"           # the authors' stored result files

ALL_CIRCUITS_LIST = INPUTS / "certified_circuits.txt"          # 310 names (RQ1/RQ2), no ".qasm"
RQ3_CIRCUITS_LIST = INPUTS / "rq3_circuits.txt"                # 238 names (RQ3), no ".qasm"
CANONICAL_MANIFEST = INPUTS / "rq3_single_error_manifest.json"  # authors' 3,570 mutants (seeds 1-5)

DATA = HERE / "data"                         # per-circuit / per-mutant CSVs written by the steps
RESULTS = HERE / "results"                   # summary tables + the markdown report


def use_authors_code():
    """Put the authors' src/ on sys.path so `import rq3_realexec_eval` etc. work.
    Their modules use sibling imports (e.g. `from utilities import ...`), which is
    why the folder itself (not the repo root) must be on the path."""
    if str(SRC) not in sys.path:             # avoid adding it twice
        sys.path.insert(0, str(SRC))         # first on the path = their modules win


# --------------------------------------------------------------------------------------
# 2. Experiment settings (the paper's values; the authors' code enforces most of them)
# --------------------------------------------------------------------------------------
QMAX = 24                                    # qubit budget per instrumented run (paper Sec. IV-F)
AUTHOR_SEEDS = (1, 2, 3, 4, 5)               # mutation seeds used in the paper
OUR_SEEDS = (6, 7, 8, 9, 10)                 # our own mutant set (new seeds, same procedure)
METHODS = ("qmon", "qmon_pernode", "statistical", "proq", "liu", "mqt")  # order = Table III rows
REPORTED_BASELINES = ("statistical", "proq", "liu", "mqt")              # the four published baselines
METHOD_NAMES = {                             # display names used in the paper's Table III
    "qmon": "QMON (batched)",
    "qmon_pernode": "QMON (independent per-checkpoint ablation)",
    "statistical": "Statistical assertion",
    "proq": "Projection assertion (Proq)",
    "liu": "Dynamic ancilla (Liu et al.)",
    "mqt": "MQT debugger (combined flag)",
}


def read_names(path):
    """Read a circuit list file and return names WITH the '.qasm' suffix
    (the authors' functions key circuits by file name)."""
    names = []
    for line in Path(path).read_text().splitlines():             # one circuit per line
        line = line.strip()                                      # drop spaces / newline
        if line:                                                 # skip blank lines
            names.append(line if line.endswith(".qasm") else line + ".qasm")
    return names


def family_of(circuit):
    """The authors' circuit-family label (circuit_families.canonical_family_of):
    strip '.qasm', cut at '_indep_qiskit_', map aliases (bv_alt -> bv)."""
    use_authors_code()
    from circuit_families import canonical_family_of             # pure Python, no qiskit
    return canonical_family_of(circuit)


# --------------------------------------------------------------------------------------
# 3. CSV / JSON helpers
# --------------------------------------------------------------------------------------
def write_csv(path, rows, fieldnames):
    """Write a list of dicts to CSV (creates the folder). Missing keys -> empty cell."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)               # make data/ or results/
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()                                     # first row = column names
        for row in rows:
            writer.writerow({k: _cell(row.get(k)) for k in fieldnames})
    return path


def _cell(value):
    """CSV formatting: booleans as true/false, None as empty, lists as JSON."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value)
    return value


def read_csv(path):
    """Read a CSV written by write_csv back into a list of dicts with light typing:
    'true'/'false' -> bool, '' -> None, ints and floats parsed."""
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append({k: _parse(v) for k, v in raw.items()})
    return rows


def _parse(text):
    if text is None or text == "":
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


# --------------------------------------------------------------------------------------
# 4. Provenance: find the current line number of a code anchor
# --------------------------------------------------------------------------------------
# Each anchor = (file relative to the repo root, regex of the line, optional regex that
# must appear BEFORE it, used to pick the right occurrence inside a given function).
# The report resolves these at the moment it is generated, so line numbers stay right
# even if a file is edited later.
AUTHOR_ANCHORS = {
    # --- Algorithm 1 / 2 / batching (what defines checkpoints, cones, batches) -------------
    "alg1_selector": ("src/fast_analysis.py", r"^def analyze_per_gate_nolock", None),
    "alg1_test": ("src/fast_analysis.py", r"ent, _, _ = _single_vs_rest_entangled", None),
    "final_read_rule": ("src/circuits_selection.py", r"^def standard_final_read_nodes", None),
    "alg2_dfs": ("src/circuits_selection.py", r"^def dfs_quantum_circuit", None),
    "cone_set": ("src/mps_analysis.py", r"^def causal_cone", None),
    "batching": ("src/batch_partition.py", r"^def partition_nodes", None),
    "oracle_nodes": ("src/rq3_realexec_eval.py", r"self\.nodes = sorted\(monitored_nodes\(qc\)\)", None),
    "oracle_p1e": ("src/rq3_realexec_eval.py", r"self\.p1e\[nd\] = float\(rho\[1, 1\]\.real\)", None),
    "oracle_cone": ("src/rq3_realexec_eval.py", r"self\.cone = \{nd: causal_cone", None),
    "oracle_B": ("src/rq3_realexec_eval.py", r"self\.B = len\(self\.batches\)", None),
    "oracle_Kqmon": ("src/rq3_realexec_eval.py", r"self\.K_qmon = len\(self\.qmon_nodes\)", None),
    "oracle_K": ("src/rq3_realexec_eval.py", r"self\.K = len\(self\.nodes\)", None),
    "oracle_eligible": ("src/rq3_realexec_eval.py", r"def eligible\(self\)", None),
    # --- Mutation generation ----------------------------------------------------------------
    "mut_candidates": ("src/rq3_manifest.py", r"gate for gate in unitary_gate_indices\(qc\) if gate <= last_node", None),
    "mut_seed": ("src/rq3_manifest.py", r"^\s+random\.seed\(seed\)\s*$", None),
    "mut_sample": ("src/rq3_manifest.py", r"gates = random\.sample\(candidates, SLOTS_PER_SEED\)", None),
    "mut_replace": ("src/mutation.py", r"^def mutate_circuit", None),
    "mut_l1": ("src/rq3_manifest.py", r"float\(np\.abs\(base_probs - mutant_probs\)\.sum\(\)\)", None),
    "mut_equivalent": ("src/rq3_manifest.py", r"equivalent = bool\(l1 is not None and l1 < OUTPUT_EQ_L1\)", None),
    # --- Per-checkpoint decisions ----------------------------------------------------------
    "qmon_decision": ("src/rq3_realexec_eval.py", r"^def qmon_count_flag", None),
    "qmon_deterministic": ("src/rq3_realexec_eval.py", r"wrong = k if p1 < 0\.5 else shots - k", None),
    "qmon_binomial": ("src/rq3_realexec_eval.py", r"return bool\(pvalue < alpha_node\)", r"^def qmon_count_flag"),
    "qmon_batch_sim": ("src/rq3_realexec_eval.py", r"^def sample_joint_trajectory", None),
    "qmon_bonferroni": ("src/rq3_realexec_eval.py", r"alpha_node=ALPHA / max\(oracle\.K_qmon, 1\)", r"^def scan_method"),
    "pernode_read": ("src/rq3_realexec_eval.py", r"p1_read = \(qmon_ctx\[\"raw_p1\"\]\[nd\] if affected", None),
    "stat_run": ("src/rq3_realexec_eval.py", r"^def run_statistical", None),
    "stat_null": ("src/rq3_realexec_eval.py", r"^def _null_statistical_flag", None),
    "proq_run": ("src/rq3_realexec_eval.py", r"^def run_proq", None),
    "liu_run": ("src/rq3_realexec_eval.py", r"^def run_liu", None),
    "mqt_flag": ("src/rq3_realexec_eval.py", r"f = status in \(\"fail\", \"unevaluable\"\)", None),
    "no_effect_shortcut": ("src/rq3_realexec_eval.py", r"affected = g in oracle\.cone\[nd\]", r"^def scan_method"),
    # --- Scan / detection / localisation (per mutant) ---------------------------------------
    "scan": ("src/rq3_realexec_eval.py", r"^def scan_method", None),
    "scan_first_flag": ("src/rq3_realexec_eval.py", r"return True, nd, stats", None),
    "skip_equivalent": ("src/rq3_realexec_eval.py", r"if not equivalent:", r"^def evaluate_circuit"),
    "rec_detected": ("src/rq3_realexec_eval.py", r"\"detected\": detected,", r"^def evaluate_circuit"),
    "rec_suspect": ("src/rq3_realexec_eval.py", r"suspect = oracle\.cone\[first\] if first else set\(\)", None),
    "rec_loc_precision": ("src/rq3_realexec_eval.py", r"\"loc_precision\": \(1\.0 / len\(suspect\)", None),
    "scope": ("src/rq3_realexec_eval.py", r"in_scope_full = any\(", None),
    # --- False-alarm arm ----------------------------------------------------------------------
    "fa_function": ("src/rq3_realexec_eval.py", r"^def false_alarm_circuit", None),
    "fa_count": ("src/rq3_realexec_eval.py", r"n_flag \+= 1", r"^def false_alarm_circuit"),
    "fa_flag": ("src/rq3_realexec_eval.py", r"None if m == \"mqt\" or not complete else n_flag > 0", None),
    "fa_mqt_none": ("src/rq3_realexec_eval.py", r"# This is a conditional definition shortcut", None),
    # --- The authors' own aggregation (what printed rq3_aggregate.txt) ----------------------
    "agg_det": ("src/rq3_realexec_eval.py", r"det\.append\(100 \* np\.mean", None),
    "agg_dets": ("src/rq3_realexec_eval.py", r"dets\.append\(100 \* np\.mean", None),
    "agg_prec": ("src/rq3_realexec_eval.py", r"prec\.append\(np\.mean\(pv\)\)", None),
    "agg_fa": ("src/rq3_realexec_eval.py", r"fa = f\"\{100 \* np\.mean\(fam\):\.1f\}\"", None),
    "agg_costs": ("src/rq3_realexec_eval.py", r"^def _unique_circuit_plan_costs", None),
    "agg_ms": ("src/rq3_realexec_eval.py", r"sd = statistics\.stdev\(vals\) if len\(vals\) > 1 else 0\.0", None),
    "miss_rows": ("src/rq3_miss_analysis.py", r"^def _derive_attempt_rows", None),
    "miss_qmon_detected": ("src/rq3_miss_analysis.py", r"qmon_detected = _method_boolean\(record, \"qmon\", \"detected\"\)", None),
    "miss_baseline_any": ("src/rq3_miss_analysis.py", r"baseline_detected = any\(", None),
    "mqt_diag_result": ("src/mqt_diagnostics.py", r"^def _mqt_result", None),
    "miss_rate": ("src/rq3_miss_analysis.py", r"^def _rate_summary", None),
    "mqt_diag": ("src/mqt_diagnostics.py", r"^def summarize", None),
}


def find_line(relpath, pattern, after=None, root=None):
    """Return the 1-based line number of the first line matching `pattern` in
    root/relpath (after the first line matching `after`, if given); None if absent."""
    path = Path(root or REPO) / relpath
    if not path.exists():
        return None
    started = after is None                                      # no 'after' => search from top
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not started and re.search(after, line):               # reached the enclosing function
            started = True
            continue
        if started and re.search(pattern, line):
            return number
    return None


def author_ref(anchor):
    """'src/rq3_realexec_eval.py:2357' for a named anchor (or '...:?' if not found)."""
    relpath, pattern, after = AUTHOR_ANCHORS[anchor]
    line = find_line(relpath, pattern, after)
    return f"{relpath}:{line if line else '?'}"


def our_ref(script, marker):
    """Line of the comment '# [PROV:<marker>]' inside one of OUR scripts, as
    'reproduction/<script>:<line>'. Our scripts tag every computed table value this way."""
    line = find_line(script, re.escape(f"[PROV:{marker}]"), root=HERE)
    return f"reproduction/{script}:{line if line else '?'}"
