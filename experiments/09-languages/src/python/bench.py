#!/usr/bin/env python3
"""E1, version Python. Même plan de mesure, mêmes données et mêmes boucles « contrôlées »
que les versions C, Rust et Go (README, section 4).

Les entiers Python ne débordent pas : la réduction modulo 2^64 (« & MASK ») est une
différence inévitable avec les autres langages.
"""

import sys

if len(sys.argv) == 2 and sys.argv[1] == "--noop":
    sys.exit(0)
if len(sys.argv) == 2 and sys.argv[1] == "--noop-numpy":
    import numpy  # noqa: F401
    sys.exit(0)

import argparse  # noqa: E402
import array  # noqa: E402
import collections  # noqa: E402
import ctypes  # noqa: E402
import gc  # noqa: E402
import math  # noqa: E402
import struct  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

K = 0x9E3779B97F4A7C15
MASK = (1 << 64) - 1
TABLE_BITS = 17
TABLE_SIZE = 1 << TABLE_BITS

# ---------------------------------------------------------------- charges contrôlées


def hash_chain(u, h):
    for i in range(len(u)):
        h = ((h ^ u[i]) * K) & MASK
    return h


def dot(a, b):
    s = 0.0
    for i in range(len(a)):
        s += a[i] * b[i]
    return s


def count_table(keys, slot_keys, slot_counts):
    for i in range(len(keys)):
        stored = keys[i] + 1
        slot = ((stored * K) & MASK) >> (64 - TABLE_BITS)
        while slot_keys[slot] != 0 and slot_keys[slot] != stored:
            slot = (slot + 1) & (TABLE_SIZE - 1)
        slot_keys[slot] = stored
        slot_counts[slot] += 1


# ---------------------------------------------------------------- versions idiomatiques


def hash_chain_idiomatic(u, h):
    for x in u:
        h = ((h ^ x) * K) & MASK
    return h


def dot_idiomatic(a, b):
    return math.sumprod(a, b)          # précision étendue : autre arrondi que la boucle


def count_idiomatic(keys):
    return collections.Counter(keys)


def dot_numpy(a, b):
    return float(np.dot(a, b))         # OpenBLAS : autre ordre de sommation


def count_numpy(keys):
    return np.bincount(keys, minlength=1 << 16)


# ---------------------------------------------------------------- outils

LIBC = ctypes.CDLL(None)


def cpu():
    return LIBC.sched_getcpu()


def xorshift(state):
    state ^= state >> 12
    state ^= (state << 25) & MASK
    state ^= state >> 27
    return state, (state * 2685821657736338717) & MASK


def peak_rss_kib():
    with open("/proc/self/status", encoding="utf-8") as status:
        for line in status:
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    return -1


def collections_done():
    return sum(entry["collections"] for entry in gc.get_stats())


def u64_of_float(value):
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def main():
    parser = argparse.ArgumentParser()
    for name in ("--input", "--output", "--meta", "--build"):
        parser.add_argument(name, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20260922)
    parser.add_argument("--rounds", type=int, default=11)
    parser.add_argument("--warmup-rounds", type=int, default=1)
    parser.add_argument("--scale-log2", type=int, default=0)
    args = parser.parse_args()
    assert args.run_id > 0 and args.warmup_rounds < args.rounds and 0 <= args.scale_log2 <= 12

    n_hash = 1 << (20 - args.scale_log2)
    n_dot, n_count = n_hash, 1 << (22 - args.scale_log2)
    n_total = max(n_count, 2 * n_dot)
    raw = array.array("Q")
    with open(args.input, "rb") as source:
        raw.frombytes(source.read(8 * n_total))
    assert sys.byteorder == "little"
    u = raw.tolist()
    a = [(u[i] >> 11) * 2.0**-53 for i in range(n_dot)]
    b = [(u[n_dot + i] >> 11) * 2.0**-53 for i in range(n_dot)]
    keys = [((x >> 48) * ((x >> 32) & 0xFFFF)) >> 16 for x in u[:n_count]]
    keys_sum = sum(keys)
    hash_data = u[:n_hash]
    a_np, b_np = np.array(a, dtype=np.float64), np.array(b, dtype=np.float64)
    keys_np = np.array(keys, dtype=np.int64)

    measures = [
        ("hash_chain", "control", 1),
        ("hash_chain", "control_bis", 1),
        ("hash_chain", "control_double", 2),
        ("hash_chain", "idiomatic", 1),
        ("dot", "control", 1),
        ("dot", "idiomatic", 1),
        ("dot", "numpy", 1),
        ("count", "control", 1),
        ("count", "idiomatic", 1),
        ("count", "idiomatic_bis", 1),
        ("count", "numpy", 1),
    ]
    m = len(measures)
    state = args.seed ^ ((args.run_id * K) & MASK)
    state = state or 1
    order = []
    for _ in range(args.rounds):
        chunk = list(range(m))
        for j in range(m, 1, -1):
            state, value = xorshift(state)
            other = value % j
            chunk[j - 1], chunk[other] = chunk[other], chunk[j - 1]
        order.extend(chunk)

    rows = []
    first_cpu = cpu()
    gc_start = collections_done()
    for index in order:
        workload, variant, passes = measures[index]
        slot_keys = slot_counts = None
        if (workload, variant) == ("count", "control"):
            slot_keys, slot_counts = [0] * TABLE_SIZE, [0] * TABLE_SIZE
        gc.collect()                    # déchets précédents collectés hors chronométrage
        gc_before = collections_done()
        before = cpu()
        t0 = time.perf_counter_ns()
        output = None
        if workload == "hash_chain":
            if variant == "idiomatic":
                output = hash_chain_idiomatic(hash_data, 0)
            else:
                output = hash_chain(hash_data, 0)
                if passes == 2:
                    output = hash_chain(hash_data, output)
        elif workload == "dot":
            output = {"control": dot, "idiomatic": dot_idiomatic, "numpy": dot_numpy}[variant](
                *((a_np, b_np) if variant == "numpy" else (a, b)))
        elif variant == "control":
            count_table(keys, slot_keys, slot_counts)
        elif variant == "numpy":
            output = count_numpy(keys_np)
        else:
            output = count_idiomatic(keys)
        elapsed = time.perf_counter_ns() - t0
        after = cpu()
        gc_delta = collections_done() - gc_before
        if workload == "hash_chain":
            result = output
        elif workload == "dot":
            result = u64_of_float(output)
        elif variant == "control":
            result = sum(c * ((k * K) & MASK) for k, c in zip(slot_keys, slot_counts) if k) & MASK
        elif variant == "numpy":
            result = sum(int(c) * (((k + 1) * K) & MASK) for k, c in enumerate(output.tolist()) if c) & MASK
        else:
            result = sum(c * (((k + 1) * K) & MASK) for k, c in output.items()) & MASK
        rows.append((index, elapsed, result, gc_delta, before, after))
        del output
    gc_total = collections_done() - gc_start - len(order)   # sans les collectes forcées

    with open(args.output, "w", encoding="utf-8") as target:
        target.write("run_id,build,seed,sample,round,phase,position,workload,variant,elements,passes,elapsed_ns,"
                     "result,gc_delta,cpu_before,cpu_after\n")
        for s, (index, elapsed, result, gc_delta, before, after) in enumerate(rows):
            workload, variant, passes = measures[index]
            elements = {"hash_chain": n_hash, "dot": n_dot, "count": n_count}[workload]
            phase = "warmup" if s // m < args.warmup_rounds else "measure"
            target.write(f"{args.run_id},{args.build},{args.seed},{s},{s // m},{phase},{s % m},{workload},{variant},"
                         f"{elements},{passes},{elapsed},{result:016x},{gc_delta},{before},{after}\n")
    jit = sys._jit.is_enabled() if hasattr(sys, "_jit") else "absent"
    gil = sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else "absent"
    with open(args.meta, "w", encoding="utf-8") as target:
        target.write("run_id,build,runtime,first_cpu,peak_rss_kib,keys_sum,gc_total,jit,gil\n")
        target.write(f"{args.run_id},{args.build},CPython {sys.version.split()[0]} numpy {np.__version__},"
                     f"{first_cpu},{peak_rss_kib()},{keys_sum},{gc_total},{jit},{gil}\n")


if __name__ == "__main__":
    main()
