#!/usr/bin/env python3
"""E2, partie 3 : allocation continue à ensemble vivant fixe en CPython. Même protocole
que src/c/churn.c. Le ramasse-miettes des cycles est actif ou désactivé (--no-gc) pour
ce seul processus ; les collectes sont chronométrées par gc.callbacks."""

import argparse
import gc
import time


class Obj:
    __slots__ = ("key", "a", "b")

    def __init__(self, i):
        self.key = i
        self.a = 2 * i + 1
        self.b = 3 * i + 2


def peak_rss_kib():
    with open("/proc/self/status", encoding="utf-8") as status:
        for line in status:
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    return -1


def allowed_cpus():
    with open("/proc/self/status", encoding="utf-8") as status:
        for line in status:
            if line.startswith("Cpus_allowed_list:"):
                return line.split(":", 1)[1].strip().replace(",", ";")
    return "inconnu"


def main():
    parser = argparse.ArgumentParser()
    for name in ("--output", "--meta", "--mode", "--run-id"):
        parser.add_argument(name, required=True)
    parser.add_argument("--live-log2", type=int, default=20)
    parser.add_argument("--batch-log2", type=int, default=13)
    parser.add_argument("--batches", type=int, default=1024)
    parser.add_argument("--no-gc", action="store_true")
    args = parser.parse_args()
    live, batch = 1 << args.live_log2, 1 << args.batch_log2

    stats = {"count": 0, "ns": 0, "start": 0, "on": False}

    def callback(phase, _info):
        if not stats["on"]:
            return
        if phase == "start":
            stats["start"] = time.perf_counter_ns()
        else:
            stats["count"] += 1
            stats["ns"] += time.perf_counter_ns() - stats["start"]

    gc.callbacks.append(callback)
    if args.no_gc:
        gc.disable()
    ring = [None] * live
    i = 0
    while i < live:
        ring[i] = Obj(i)
        i += 1
    elapsed = []
    mask = live - 1
    stats["on"] = True
    start = time.perf_counter_ns()
    for _ in range(args.batches):
        t0 = time.perf_counter_ns()
        for _ in range(batch):
            ring[i & mask] = Obj(i)
            i += 1
        elapsed.append(time.perf_counter_ns() - t0)
    total = time.perf_counter_ns() - start
    stats["on"] = False
    checksum = sum(o.key + o.a + o.b for o in ring) & ((1 << 64) - 1)

    with open(args.output, "w", encoding="utf-8") as target:
        target.write("run_id,mode,batch,operations,elapsed_ns\n")
        for k, e in enumerate(elapsed):
            target.write(f"{args.run_id},{args.mode},{k},{batch},{e}\n")
    with open(args.meta, "w", encoding="utf-8") as target:
        target.write("run_id,mode,runtime,total_ns,operations,checksum,gc_count,gc_pause_ns,peak_rss_kib,cpus_allowed\n")
        target.write(f"{args.run_id},{args.mode},CPython gc={'off' if args.no_gc else 'on'},{total},"
                     f"{args.batches * batch},{checksum},{stats['count']},{stats['ns']},{peak_rss_kib()},{allowed_cpus()}\n")


if __name__ == "__main__":
    main()
