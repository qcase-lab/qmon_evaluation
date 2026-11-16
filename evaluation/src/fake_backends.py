import warnings
from statistics import median
from qiskit_ibm_runtime.fake_provider import FakeProviderForBackendV2

warnings.filterwarnings("ignore")   # old snapshots print deprecation warnings

#lowkey ignore nighthawk

def med_ns(target, op):
    """Median duration of instruction `op` across all qubits, in nanoseconds."""
    if op not in target.operation_names:                                  # backend doesn't have this instruction
        return None
    durs = [p.duration for p in target[op].values() if p and p.duration]  # one duration per qubit (or pair)
    return round(median(durs) * 1e9) if durs else None                    # seconds -> ns


print(f"{'backend':<18}{'qubits':>7}  {'snapshot':<11}{'2q':<5}{'1q_ns':>7}{'2q_ns':>7}{'meas_ns':>9}{'reset_ns':>9}{'rep_us':>8}")

for b in FakeProviderForBackendV2().backends():                           # every fake backend installed
    t = b.target                                                          # the lookup table of gates, qubits, durations
    props = b.properties()                                                # the calibration snapshot
    date = props.last_update_date.date() if props else None               # day the snapshot was taken
    two_q = next((g for g in ("cz", "ecr", "cx") if g in t.operation_names), None)  # native 2-qubit gate
    rep = getattr(b.configuration(), "default_rep_delay", None)           # wait between shots, in seconds
    rep_us = round(rep * 1e6) if rep else None                            # seconds -> µs

    print(f"{b.name:<18}{b.num_qubits:>7}  {str(date):<11}{str(two_q):<5}"
          f"{str(med_ns(t, 'sx')):>7}{str(med_ns(t, two_q)):>7}"
          f"{str(med_ns(t, 'measure')):>9}{str(med_ns(t, 'reset')):>9}{str(rep_us):>8}")