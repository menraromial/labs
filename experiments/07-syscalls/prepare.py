#!/usr/bin/env python3
"""Prépare une campagne D1 : topologie et plan complet des processus.

Les mêmes mesures sur un cœur P, un cœur E et un cœur LP-E (le CPU de plus grand
numéro de chaque type, choisi avant la mesure) ; ordre des processus tiré au
hasard avec une graine fixe.
"""

import argparse
import csv
import random
from pathlib import Path

BASE_SEED = 20260920
CORES = ("P", "E", "LP-E")

SETTINGS = {
    "check": {"runs": 1, "rounds": 2, "warmup_rounds": 1, "scale_log2": 8},
    "quick": {"runs": 1, "rounds": 2, "warmup_rounds": 1, "scale_log2": 4},
    "campaign": {"runs": 10, "rounds": 11, "warmup_rounds": 1, "scale_log2": 0},
}

PLAN_FIELDS = ["run_id", "core", "cpu", "seed", "rounds", "warmup_rounds", "scale_log2"]


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
        has_l3 = any((index / "level").read_text().strip() == "3"
                     for index in (root / f"cpu{cpu}" / "cache").glob("index*"))
        core_type = ("P" if cpu in performance else
                     ("E" if has_l3 else "LP-E") if cpu in efficient else "unique")
        rows.append({"cpu": cpu, "core_type": core_type})
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
    plan = [{"core": core, "cpu": chosen[core], **{k: settings[k] for k in PLAN_FIELDS if k in settings}}
            for core in CORES if core in chosen for _ in range(settings["runs"])]
    random.Random(BASE_SEED).shuffle(plan)
    for run_id, row in enumerate(plan, start=1):
        row["run_id"] = run_id
        row["seed"] = BASE_SEED

    args.directory.mkdir(parents=True, exist_ok=True)
    for name, fields, rows in (("topology.csv", list(topology[0]), topology), ("plan.csv", PLAN_FIELDS, plan)):
        with (args.directory / name).open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print(f"plan={args.directory / 'plan.csv'} processes={len(plan)} cpus={ {c: chosen[c] for c in CORES if c in chosen} }")


if __name__ == "__main__":
    main()
