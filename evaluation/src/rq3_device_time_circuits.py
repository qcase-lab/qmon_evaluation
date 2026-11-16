"""Device-time estimates for RQ3 (bug detection) on fake IBM backends. PART 1 of 2.

Nothing is executed or simulated. For every circuit RQ3 would run on a quantum
computer, we transpile it to a fake backend and ask Qiskit how long ONE shot takes:
QuantumCircuit.estimate_duration = longest path through the compiled circuit, using
the backend's calibrated durations for each gate / measure / reset on each qubit.
Part 2 (rq3_device_time_metrics.py) turns these per-shot durations into run times and
joins them with the authors' stored RQ3 results (rq3_mutant.pkl, rq3_falsealarm.pkl).

Circuits timed for each of the 238 RQ3 circuits (built from the ORIGINAL circuit; a
mutant changes one gate, and --mutant-check measures how much that changes D):
  original      the uninstrumented circuit (reference for overhead ratios)
  qmon          every QMON batch at Qmax = 24, from rq3_realexec_eval's Oracle plan
  statistical   prefix up to the checkpoint gate + measure_all          (run_statistical)
  liu           prefix + Liu assertion ancilla, ancilla measured         (run_liu)
  proq          u/cx prefix + pytket ProjectorAssertionBox, boxes decomposed (run_proq)
  MQT is not timed: it is a classical tool and never runs on a quantum computer.

Run from the repo root, venv active, in WSL. Test on 2 circuits first:
    python evaluation/src/rq3_device_time_circuits.py --backends kingston --limit 2
Full run:
    python evaluation/src/rq3_device_time_circuits.py --backends kingston --seeds 1 2 3

Writes:
  evaluation/results/device_time_cache/<backend>/<circuit>.pkl   one per circuit (resume)
  evaluation/results/device_time_circuits_<backend>.csv          one row per compiled circuit
"""

import argparse                      # command-line options
import contextlib                    # redirect_stdout: hide the authors' print() output
import csv                           # write the output table
import io                            # StringIO: where the hidden output goes
import os                            # cpu count, atomic file replace
import pickle                        # per-circuit cache files
import random                        # pick the mutants for --mutant-check
import statistics                    # median
import sys                           # edit the import path
import time                          # perf_counter(): compile time
import traceback                     # full error text for failed circuits
import warnings                      # silence deprecation noise from old snapshots
from multiprocessing import Pool     # one worker process per circuit
from pathlib import Path             # file paths

import numpy as np                   # outer product for the Proq projector

# Repo root = the nearest folder above this file that contains the authors' src/coverage_rq2.py.
REPO = next(p for p in Path(__file__).resolve().parents
            if (p / "src" / "coverage_rq2.py").exists())
sys.path.insert(0, str(REPO / "src"))               # so the authors' modules import
warnings.filterwarnings("ignore")                   # fake-backend snapshots print warnings

from qiskit import QuantumCircuit                             # rebuild compiled circuits
from qiskit.transpiler import generate_preset_pass_manager   # IBM's standard compiler
from qiskit.transpiler.passes import RemoveBarriers          # barriers have no duration
from qiskit_ibm_runtime.fake_provider import (FakeKingston, FakeFez, FakeMarrakesh,
                                              FakeTorino, FakeSherbrooke)
from pytket.circuit import ProjectorAssertionBox             # Proq's official assertion
from pytket.passes import DecomposeBoxes                     # box -> plain gates + measure
from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit

import rq3_realexec_eval as rq3      # Oracle (the RQ3 plan), _prefix, _prefix_ucx, constants
from utilities import generate_monitoring_circuit             # builds one QMON batch circuit
from baseline_liu import classical_assertion, superposition_assertion   # Liu's circuits
from rq3_manifest import apply_manifest_slot, load_manifest   # rebuild a stored mutant
from coverage_rq2 import executable_operation_count, executable_depth   # same counting
                                                              # rules as your resources script

BACKENDS = {"kingston": FakeKingston,     # 156-qubit Heron r2, newest snapshot in 0.48.0
            "fez": FakeFez,               # 156-qubit Heron r2
            "marrakesh": FakeMarrakesh,   # 156-qubit Heron r2
            "torino": FakeTorino,         # 133-qubit Heron r1
            "sherbrooke": FakeSherbrooke} # 127-qubit Eagle (ECR gates)
OPT_LEVEL = 2                             # Qiskit's default preset optimization level
WORKERS = min(4, os.cpu_count() or 1)     # parallel circuits (laptop: 4 cores)
OUT_DIR = Path(__file__).resolve().parents[1] / "results"     # evaluation/results/
RQ3_LIST = REPO / "inputs" / "rq3_circuits.txt"               # the 238 RQ3 circuits
FALSE_ALARM_PKL = REPO / "results" / "rq3" / "rq3_falsealarm.pkl"   # one record per circuit

_BACKEND = None                           # set once per worker process (see init_worker)
_PASS_MANAGERS = {}                       # seed -> compiled pass manager, reused per worker


def quiet(fn, *args, **kwargs):
    """Call fn and throw away what it prints (the authors' helpers print a lot)."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def init_worker(backend_name):
    """Runs once in each worker: build the fake backend there (it is not picklable)."""
    global _BACKEND
    _BACKEND = BACKENDS[backend_name]()   # e.g. FakeKingston(): coupling map + calibration


def pass_manager(seed):
    """IBM preset compiler for this backend; ALAP scheduling so durations are defined."""
    if seed not in _PASS_MANAGERS:
        _PASS_MANAGERS[seed] = generate_preset_pass_manager(
            optimization_level=OPT_LEVEL,         # same level for every method (fairness)
            backend=_BACKEND,                     # native gates, connectivity, durations
            seed_transpiler=seed,                 # layout/routing are random: fix the seed
            scheduling_method="alap")             # schedule; estimate_duration reads it
    return _PASS_MANAGERS[seed]


def backend_info(backend):
    """Per-backend constants Part 2 needs for the job-time formula (stored in each cache)."""
    t = backend.target
    resets = [p.duration for p in t["reset"].values() if p and p.duration]   # per qubit
    measures = [p.duration for p in t["measure"].values() if p and p.duration]
    props = backend.properties()                                  # calibration snapshot
    return {
        "name": backend.name,
        "num_qubits": backend.num_qubits,
        "snapshot": str(props.last_update_date.date()) if props else None,
        "rep_delay_s": getattr(backend.configuration(), "default_rep_delay", None),  # t_rep
        "reset_s_median": statistics.median(resets) if resets else None,           # t_init
        "measure_s_median": statistics.median(measures) if measures else None,
    }


# ============================================================================
# Time one circuit: transpile, then estimate_duration           -> D per shot
# ============================================================================
ROUTING_PASSES = ("SabreLayout", "SabreSwap", "BasicSwap", "LookaheadSwap",
                  "StochasticSwap")       # passes that insert SWAPs for unconnected qubits


def resource_stats(circ):
    """Resource counts with the SAME definitions as resources_rq2_metrics.py
    (operations and depth via the authors' executable_* helpers: barriers and delays
    ignored, measure/reset counted). Used on the circuit before AND after transpiling."""
    ops = circ.count_ops()
    gates = [inst for inst in circ.data if inst.operation.name not in
             ("barrier", "delay", "measure", "reset", "snapshot")]   # unitary gates only
    return {
        "qubits": circ.num_qubits,
        "operations": executable_operation_count(circ),           # gates + measure + reset
        "depth": executable_depth(circ),                          # layers, measure/reset incl.
        "one_qubit_gates": sum(1 for g in gates if g.operation.num_qubits == 1),
        "two_qubit_gates": sum(1 for g in gates if g.operation.num_qubits == 2),
        "swaps": ops.get("swap", 0),                              # SWAP gates as written
        "measures": ops.get("measure", 0),                        # mid-circuit + terminal
        "resets": ops.get("reset", 0),                            # QMON: one per checkpoint
    }


def compile_and_time(circuit, seed):
    """Transpile `circuit` to the fake backend; return its per-shot duration D and its
    resources BEFORE and AFTER transpiling (Part 2: device time + transpilation overhead)."""
    before = resource_stats(circuit)                              # as QMON / the baseline builds it
    routing = {"swaps_added": 0, "last": before["swaps"]}         # filled by the callback

    def watch(pass_, dag, **_):
        """Called after every compiler pass: count the SWAPs that routing inserts.
        Later the translation stage turns each SWAP into 3 CZ, so they must be
        counted here, while they are still SWAP gates."""
        now = dag.count_ops().get("swap", 0)
        if pass_.name() in ROUTING_PASSES and now > routing["last"]:
            routing["swaps_added"] += now - routing["last"]       # new SWAPs from routing
        routing["last"] = now

    start = time.perf_counter()
    compiled = pass_manager(seed).run(circuit, callback=watch)    # native gates, routed
    compile_s = time.perf_counter() - start                       # classical compile cost
    compiled = RemoveBarriers()(compiled)     # barriers take no time; drop them so
                                              # estimate_duration never needs a duration for one
    duration = compiled.estimate_duration(_BACKEND.target, unit="s")   # D (one shot)

    # The compiled circuit spans all device qubits and is padded with delays by the
    # scheduler; keep only the real operations on the qubits actually used.
    real = [inst for inst in compiled.data if inst.operation.name != "delay"]
    used = sorted({compiled.find_bit(q).index for inst in real for q in inst.qubits})
    slim = QuantumCircuit(len(used), compiled.num_clbits)         # same ops, used qubits only
    index = {q: i for i, q in enumerate(used)}
    for inst in real:
        slim.append(inst.operation, [index[compiled.find_bit(q).index] for q in inst.qubits],
                    [compiled.find_bit(c).index for c in inst.clbits])
    after = resource_stats(slim)                                  # native gates on the device

    return {
        "duration_s": duration,                                   # D (one shot)
        **{f"before_{k}": v for k, v in before.items()},          # logical circuit
        **{f"after_{k}": v for k, v in after.items()},            # compiled circuit
        "routing_swaps": routing["swaps_added"],                  # SWAPs added by routing
        "compile_s": compile_s,
    }

#Baseline + QMON Building
# ============================================================================
# Build the circuits RQ3 would run on hardware (one circuit = one run of 8,192 shots)
# ============================================================================
def qmon_batches(qc, key, oracle, batches):
    """QMON: one instrumented circuit per batch, exactly as make_qmon_joint_ctx builds it.
    `batches` = the STORED plan's batches, so the circuits are the ones behind the pkl."""
    out = []
    for b_id, batch in enumerate(batches):                       # batches in FFD order
        circ = quiet(generate_monitoring_circuit, qc, key, oracle.op_list,
                     rq3.INSTRUMENTATION_INTERNAL_QUBIT_LIMIT,
                     {"picked_nodes": set(batch["nodes"])})       # same call as the evaluator
        assert circ.num_qubits <= oracle.qmax, (key, b_id, circ.num_qubits)   # <= 24 qubits
        out.append((b_id, circ))
    return out


def statistical_circuit(qc, gate):
    """Huang-Martonosi: prefix up to and including `gate`, then measure every qubit.
    Depends only on the gate index, so checkpoints at the same gate share it."""
    pre = rq3._prefix(qc, gate)                                   # same helper as run_statistical
    pre.measure_all()
    return pre


def liu_circuit(qc, node, oracle):
    """Liu-Byrd-Zhou: prefix + assertion ancilla on the checked qubit (as run_liu)."""
    gate, qubit = node
    pre = rq3._prefix(qc, gate)
    if oracle.deterministic(node):                                # expected |0> or |1>
        classical_assertion(pre, [pre.qubits[qubit]], 0 if oracle.p1e[node] < 0.5 else 1)
    else:                                                         # expected superposition
        theta, phi = oracle.liu_params(node)
        superposition_assertion(pre, [pre.qubits[qubit]],
                                {pre.qubits[qubit]: (theta, phi)}, 1)
    return pre


def proq_circuit(qc, node, oracle):
    """Proq: u/cx prefix + pytket ProjectorAssertionBox (as run_proq), converted back to
    Qiskit so the IBM compiler can time it. DecomposeBoxes turns the box into the gates and
    measurement pytket would run."""
    gate, qubit = node
    amps = oracle.amps[node]                                      # expected pure state
    projector = np.outer(amps, amps.conj())                       # P = |psi><psi|
    tkc = qiskit_to_tk(rq3._prefix_ucx(qc, gate))                 # same prefix as run_proq
    tkc.add_assertion(ProjectorAssertionBox(projector), [qubit], name=f"n{gate}_q{qubit}")
    DecomposeBoxes().apply(tkc)                                   # plain gates + measure
    return tk_to_qiskit(tkc)


# ============================================================================
# One circuit, in a worker process
# ============================================================================
def cache_file(backend_name, key):
    return OUT_DIR / "device_time_cache" / backend_name / (key + ".pkl")


def load_cached(backend_name, key):
    """The cached result of one circuit, or None if it is missing or failed."""
    path = cache_file(backend_name, key)
    if not path.exists():
        return None
    with path.open("rb") as f:
        result = pickle.load(f)
    return None if "error" in result else result
_MUTATION_LIST = None


def mutation_list():
    """The authors' fixed list of 3,570 mutations, loaded once per worker.
    verify_runtime=False: the list stores checksums of the authors' exact package
    versions, and any difference (e.g. a patch version) rejects the whole file.
    Every mutant is still checked one by one: apply_manifest_slot compares the
    rebuilt mutant's hash with the stored one and raises on any mismatch."""
    global _MUTATION_LIST
    if _MUTATION_LIST is None:
        _MUTATION_LIST = load_manifest(verify_runtime=False)
    return _MUTATION_LIST
DESCRIPTION_FIELDS = {"grouped_monitor_channel", "final_read_policy", "coverage_scope"}
# ^ plain-English descriptions stored inside the plan. The authors reworded one of them
#   ("production selector" -> "the implemented selector") after the stored run, so the
#   plan hash differs for every circuit even though the plan itself is identical.


def same_plan(stored, recomputed, key):
    """Check the recomputed RQ3 plan against the stored one, ignoring description text.
    Same rules as the authors' _check_plan_equivalent: every substantive field must
    agree, and the batches may differ only as an equally good regrouping of the same
    checkpoints (the ILP can return an alternative optimum). Returns True if regrouped."""
    ignore = DESCRIPTION_FIELDS | {"batches", "plan_sha256"}
    for field in sorted((set(stored) | set(recomputed)) - ignore):
        if stored.get(field) != recomputed.get(field):            # a real plan difference
            raise ValueError(f"{key}: plan field {field!r} differs from the stored plan")
    s, r = stored["batches"], recomputed["batches"]
    if s == r:
        return False                                              # identical plan
    if len(s) != len(r) or (sorted(g for b in s for g in b["nodes"])
                            != sorted(g for b in r for g in b["nodes"])):
        raise ValueError(f"{key}: different batch count or checkpoint set than stored")
    return True                                                   # same checkpoints, regrouped

def process_circuit(job):
    """Build and time every circuit RQ3 runs for one benchmark circuit; save to cache."""
    key, backend_name, seeds, stored_plan, mutant_fraction = job
    rows, failures = [], []

    def time_it(kind, label, circuit, seed_list):
        for seed in seed_list:                                    # one row per seed
            try:
                rows.append({"kind": kind, "label": label, "seed": seed,
                             **compile_and_time(circuit, seed)})
            except Exception as error:                            # keep going, report later
                failures.append({"kind": kind, "label": label, "seed": seed,
                                 "error": f"{type(error).__name__}: {error}"[:300]})

    try:
        oracle = quiet(rq3.Oracle, key)                           # RQ3 plan, Qmax = 24
        qc = oracle.qc
                # The stored RQ3 run is the reference: time the plan the pkl ran.
        regrouped = same_plan(stored_plan, oracle.qmon_plan, key)  # raises if truly different
        batches = stored_plan["batches"]                          # time what the pkl ran
        batch_of = {g: b["batch"] for b in batches for g in b["nodes"]}   # gate -> batch
        time_it("original", None, qc, seeds)                      # overhead reference
        for b_id, circ in qmon_batches(qc, key, oracle, batches): # QMON runs (B of them)
            time_it("qmon", b_id, circ, seeds)
        for gate in sorted({g for g, _ in oracle.nodes}):         # statistical: one per gate
            time_it("statistical", gate, statistical_circuit(qc, gate), seeds)
        for node in oracle.nodes:                                 # Liu and Proq: one per node
            time_it("liu", node, liu_circuit(qc, node, oracle), seeds)
            try:
                circ = proq_circuit(qc, node, oracle)
            except Exception as error:                            # pytket conversion failed
                failures.append({"kind": "proq", "label": node, "seed": None,
                                 "error": f"build: {type(error).__name__}: {error}"[:300]})
                continue
            time_it("proq", node, circ, seeds)

        # Optional: does building on the mutant change D? QMON batches, first seed only.
        # Optional: does building on the mutant change D? QMON batches, first seed only.
        # A failure here is logged but never throws away the circuit's other timings.
        try:
            rng = random.Random(key)                              # same picks on every rerun
            for slot in rq3.canonical_mutation_slots(key, mutation_list()):
                if slot["output_equivalent"] or rng.random() >= mutant_fraction:
                    continue
                mqc = apply_manifest_slot(qc, slot)               # hash-checked mutant
                for b_id, circ in qmon_batches(mqc, key, oracle, batches):
                    time_it("qmon_mutant", (slot["slot_id"], b_id), circ, seeds[:1])
        except Exception as error:
            failures.append({"kind": "qmon_mutant", "label": None, "seed": None,
                             "error": f"{type(error).__name__}: {error}"[:300]})

        result = {
            "circuit": key, "backend": backend_info(_BACKEND), "seeds": list(seeds),
            "opt_level": OPT_LEVEL,
            "K": oracle.K, "K_qmon": oracle.K_qmon, "B": oracle.B,
            "nodes": [tuple(n) for n in oracle.nodes],            # baselines' scan order
            "lastgate": [tuple(n) for n in oracle.lastgate],      # QMON final reads (batch 0)
            "batch_nodes": [list(b["nodes"]) for b in batches],
            "batch_of": batch_of,                                 # gate -> batch (stored plan)
            "plan_sha256": stored_plan["plan_sha256"],            # the plan that was timed
            "plan_regrouped": regrouped,                          # recomputed plan differed
                                                                  # (equivalent; stored one used)
            "rows": rows, "failures": failures,
        }
    except Exception as error:                                    # whole circuit failed
        result = {"error": f"{type(error).__name__}: {error}",
                  "traceback": traceback.format_exc()}
    path = cache_file(backend_name, key)
    tmp = path.with_suffix(".tmp")                                # write, then rename
    with tmp.open("wb") as f:
        pickle.dump(result, f)
    os.replace(tmp, path)
    return key, "error" in result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backends", nargs="+", default=["kingston"], choices=list(BACKENDS))
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])   # transpiler seeds
    parser.add_argument("--limit", type=int, default=None)   # first N circuits (testing)
    parser.add_argument("--mutant-check", type=float, default=0.05)  # share of mutants rechecked
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args()

    keys = [line.strip() + ".qasm" for line in RQ3_LIST.read_text().splitlines()
            if line.strip()]                                      # the 238 RQ3 circuits
    keys = keys[:args.limit] if args.limit else keys
    with FALSE_ALARM_PKL.open("rb") as f:                         # stored QMON plan per circuit
        stored_plans = {r["circuit"]: r["qmon_plan"] for r in pickle.load(f)["records"]}

    for backend_name in args.backends:
        (OUT_DIR / "device_time_cache" / backend_name).mkdir(parents=True, exist_ok=True)
        todo = [k for k in keys if load_cached(backend_name, k) is None]   # resume
        print(f"{backend_name}: {len(keys) - len(todo)} done, {len(todo)} to go, "
              f"{args.workers} workers", flush=True)
        jobs = [(k, backend_name, args.seeds, stored_plans[k], args.mutant_check)
                for k in todo]
        with Pool(args.workers, initializer=init_worker, initargs=(backend_name,),
                  maxtasksperchild=10) as pool:                   # fresh workers now and then
            for n, (key, failed) in enumerate(pool.imap_unordered(process_circuit, jobs), 1):
                print(f"[{n}/{len(todo)}] {key}{'  ERROR' if failed else ''}", flush=True)

        # ---- One CSV row per compiled circuit -----------------------------------
        out_rows, n_fail, broken = [], 0, []
        for key in keys:
            result = load_cached(backend_name, key)
            if result is None:
                broken.append(key)
                continue
            n_fail += len(result["failures"])
            for row in result["rows"]:
                out_rows.append({"backend": backend_name, "circuit": key,
                                 **{**row, "label": repr(row["label"])}})
        if out_rows:
            path = OUT_DIR / f"device_time_circuits_{backend_name}.csv"
            with path.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(out_rows[0]))
                writer.writeheader()
                writer.writerows(out_rows)
            print(f"wrote {len(out_rows)} rows to {path}")
        print(f"{n_fail} circuit builds/compiles failed (listed in each cache's 'failures')")
        if broken:
            print(f"{len(broken)} circuits failed entirely; rerun to retry: {broken[:5]} ...")


if __name__ == "__main__":
    main()