#!/usr/bin/env python3
"""E2, partie 2 : trajectoire d'échauffement en CPython, JIT activé ou non par la variable
d'environnement PYTHON_JIT du seul processus. Même protocole que src/c/warm.c."""

import argparse
import array
import struct
import sys
import time

K = 0x9E3779B97F4A7C15
MASK = (1 << 64) - 1


def hash_chain(u, n, h):
    for i in range(n):
        h = ((h ^ u[i]) * K) & MASK
    return h


def dot(a, b, n):
    s = 0.0
    for i in range(n):
        s += a[i] * b[i]
    return s


def allowed_cpus():
    with open("/proc/self/status", encoding="utf-8") as status:
        for line in status:
            if line.startswith("Cpus_allowed_list:"):
                return line.split(":", 1)[1].strip().replace(",", ";")
    return "inconnu"


def main():
    parser = argparse.ArgumentParser()
    for name in ("--input", "--output", "--meta", "--mode"):
        parser.add_argument(name, required=True)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--n-log2", type=int, default=16)
    args = parser.parse_args()
    n = 1 << args.n_log2
    raw = array.array("Q")
    with open(args.input, "rb") as source:
        raw.frombytes(source.read(16 * n))
    u = raw.tolist()
    a = [(u[i] >> 11) * 2.0**-53 for i in range(n)]
    b = [(u[n + i] >> 11) * 2.0**-53 for i in range(n)]

    elapsed, result = [], []
    for _ in range(args.steps):
        t0 = time.perf_counter_ns()
        h = hash_chain(u, n, 0)
        t1 = time.perf_counter_ns()
        d = dot(a, b, n)
        t2 = time.perf_counter_ns()
        elapsed += [t1 - t0, t2 - t1]
        result += [h, struct.unpack("<Q", struct.pack("<d", d))[0]]

    with open(args.output, "w", encoding="utf-8") as target:
        target.write("run_id,mode,step,workload,elements,elapsed_ns,result,cpu\n")
        for s, (e, r) in enumerate(zip(elapsed, result)):
            target.write(f"{args.run_id},{args.mode},{s // 2},{'dot' if s % 2 else 'hash_chain'},{n},{e},{r:016x},-1\n")
    jit = sys._jit.is_enabled() if hasattr(sys, "_jit") else "absent"
    with open(args.meta, "w", encoding="utf-8") as target:
        target.write(f"run_id,mode,runtime,jit,cpus_allowed\n{args.run_id},{args.mode},CPython {sys.version.split()[0]},"
                     f"{'enabled' if jit is True else 'disabled'},{allowed_cpus()}\n")


if __name__ == "__main__":
    main()
