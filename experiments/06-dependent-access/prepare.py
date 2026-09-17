#!/usr/bin/env python3
"""Prépare une campagne C2 : topologie des caches et plan complet des processus.

Facteurs croisés : type de cœur (P, LP-E) et taille de page demandée au noyau par
le seul processus (4 Kio, 2 Mio). Les CPU sont choisis avant la mesure (le plus
grand numéro de chaque type, comme en C1) et l'ordre des processus est tiré au
hasard avec une graine fixe.
"""

import argparse
import csv
import random
from pathlib import Path

BASE_SEED = 20260919
CORES = ("P", "LP-E")
PAGES = ("4k", "2m")

SETTINGS = {
    "check": {"runs": 1, "rounds": 2, "warmup_rounds": 1, "min_log2": 12, "max_log2": 14,
              "accesses_log2": 10, "chase_accesses_log2": 8, "fault_small_log2": 21, "fault_large_log2": 22},
    "quick": {"runs": 1, "rounds": 2, "warmup_rounds": 1, "min_log2": 12, "max_log2": 24,
              "accesses_log2": 16, "chase_accesses_log2": 14, "fault_small_log2": 22, "fault_large_log2": 24},
    "campaign": {"runs": 8, "rounds": 11, "warmup_rounds": 1, "min_log2": 12, "max_log2": 28,
                 "accesses_log2": 20, "chase_accesses_log2": 18, "fault_small_log2": 24, "fault_large_log2": 28},
}

PLAN_FIELDS = ["run_id", "core", "cpu", "pages", "seed", "rounds", "warmup_rounds", "min_log2", "max_log2",
               "accesses_log2", "chase_accesses_log2", "fault_small_log2", "fault_large_log2"]


def parse_cpu_list(text):
    cpus = []
    for part in text.strip().split(","):
        if "-" in part:
            first, last = part.split("-")
            cpus.extend(range(int(first), int(last) + 1))
        elif part:
            cpus.append(int(part))
    return cpus


def read_topology():
    root = Path("/sys/devices/system/cpu")
    core = Path("/sys/devices/cpu_core/cpus")
    atom = Path("/sys/devices/cpu_atom/cpus")
    performance = set(parse_cpu_list(core.read_text())) if core.exists() else set()
    efficient = set(parse_cpu_list(atom.read_text())) if atom.exists() else set()
    rows = []
    for cpu in parse_cpu_list((root / "online").read_text()):
        caches = {}
        for index in sorted((root / f"cpu{cpu}" / "cache").glob("index*")):
            if (index / "type").read_text().strip() in ("Data", "Unified"):
                level = (index / "level").read_text().strip()
                caches[f"l{level}_kib"] = (index / "size").read_text().strip().removesuffix("K")
        core_type = ("P" if cpu in performance else
                     ("E" if "l3_kib" in caches else "LP-E") if cpu in efficient else "unique")
        rows.append({"cpu": cpu, "core_type": core_type, "l1_kib": caches.get("l1_kib", ""),
                     "l2_kib": caches.get("l2_kib", ""), "l3_kib": caches.get("l3_kib", "")})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=sorted(SETTINGS))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    settings = SETTINGS[args.mode]
    topology = read_topology()
    chosen = {}
    for row in topology:
        chosen[row["core_type"]] = row["cpu"]
    plan = [{"core": core, "cpu": chosen[core], "pages": pages,
             **{k: settings[k] for k in PLAN_FIELDS if k in settings}}
            for core in CORES if core in chosen for pages in PAGES for _ in range(settings["runs"])]
    random.Random(BASE_SEED).shuffle(plan)
    for run_id, row in enumerate(plan, start=1):
        row["run_id"] = run_id
        row["seed"] = BASE_SEED   # mêmes cycles pour tous les processus

    args.directory.mkdir(parents=True, exist_ok=True)
    for name, fields, rows in (("topology.csv", list(topology[0]), topology), ("plan.csv", PLAN_FIELDS, plan)):
        with (args.directory / name).open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print(f"plan={args.directory / 'plan.csv'} processes={len(plan)} cpus={ {c: chosen[c] for c in CORES if c in chosen} }")


if __name__ == "__main__":
    main()
