import inspect
import warnings
from statistics import median

import qiskit_ibm_runtime.fake_provider.backends as fake_backends       # module holding every fake class
from qiskit_ibm_runtime.fake_provider.fake_backend import FakeBackendV2  # their common base class

warnings.filterwarnings("ignore")   # old snapshots print deprecation warnings


def med_ns(target, op):
    """Median duration of instruction `op` across all qubits, in nanoseconds."""
    if op is None or op not in target.operation_names:                    # backend doesn't have this instruction
        return None
    durs = [p.duration for p in target[op].values() if p and p.duration]  # one duration per qubit (or pair)
    return round(median(durs) * 1e9) if durs else None                    # seconds -> ns


# FakeProviderForBackendV2().backends() is a hard-coded list that skips some backends
# (FakeKingston among them), so collect every fake backend class in the package instead.
classes = [cls for _, cls in inspect.getmembers(fake_backends, inspect.isclass)
           if issubclass(cls, FakeBackendV2) and cls is not FakeBackendV2]

rows, failed = [], []
for cls in classes:
    try:
        b = cls()                                                         # load the snapshot
        t = b.target                                                      # gates, qubits, durations
        props = b.properties()                                            # the calibration snapshot
    except Exception as error:                                            # a broken snapshot: report, skip
        failed.append((cls.__name__, f"{type(error).__name__}: {error}"[:80]))
        continue
    date = props.last_update_date.date() if props else None               # day the snapshot was taken
    two_q = next((g for g in ("cz", "ecr", "cx") if g in t.operation_names), None)  # native 2-qubit gate
    rep = getattr(b.configuration(), "default_rep_delay", None)           # wait between shots, in seconds
    rows.append({
        "name": b.name, "qubits": b.num_qubits, "date": date, "two_q": two_q,
        "sx": med_ns(t, "sx"), "2q": med_ns(t, two_q),
        "meas": med_ns(t, "measure"), "reset": med_ns(t, "reset"),
        "rep_us": round(rep * 1e6) if rep else None,                      # seconds -> µs
    })

# Newest calibration first; backends without a snapshot date go last.
rows = (sorted([r for r in rows if r["date"] is not None],
               key=lambda r: r["date"], reverse=True)                     # newest -> oldest
        + sorted([r for r in rows if r["date"] is None], key=lambda r: r["name"]))

print(f"{'backend':<24}{'qubits':>7}  {'snapshot':<11}{'2q':<5}{'1q_ns':>7}{'2q_ns':>7}"
      f"{'measure_ns':>9}{'reset_ns':>9}{'reset_delay_us':>8}")
for r in rows:
    print(f"{r['name']:<24}{r['qubits']:>7}  {str(r['date']):<11}{str(r['two_q']):<5}"
          f"{str(r['sx']):>7}{str(r['2q']):>7}{str(r['meas']):>9}{str(r['reset']):>9}"
          f"{str(r['rep_us']):>8}")

print(f"\n{len(rows)} fake backends listed (from {len(classes)} classes)")
for name, error in failed:
    print(f"  could not load {name}: {error}")