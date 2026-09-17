#!/usr/bin/env python3
"""Prépare une campagne B1 : topologie, CPU d'épinglage et plan complet des processus.

Chaque processus exécute un seul binaire (compilateur et niveau d'optimisation
des noyaux). L'ordre des processus est tiré au hasard avec une graine fixe.
Tous les processus sont épinglés sur le même CPU P, choisi avant la mesure :
A2 a montré que le type de cœur domine sinon la dispersion entre processus.
"""

import argparse
import csv
import random
from pathlib import Path

BASE_SEED = 20260916
COMPILERS = ("gcc", "clang")
LEVELS = ("O0", "O1", "O2", "O3")

SETTINGS = {
    "check": {"runs": 1, "rounds": 2, "warmup_rounds": 1, "min_log2": 4, "max_log2": 8,
              "step_log2": 2, "target_log2": 10},
    "quick": {"runs": 2, "rounds": 3, "warmup_rounds": 1, "min_log2": 6, "max_log2": 22,
              "step_log2": 2, "target_log2": 20},
    "campaign": {"runs": 15, "rounds": 16, "warmup_rounds": 1, "min_log2": 6, "max_log2": 22,
                 "step_log2": 2, "target_log2": 22},
}

PLAN_FIELDS = ["run_id", "binary", "compiler", "level", "cpu", "seed", "rounds",
               "warmup_rounds", "min_log2", "max_log2", "step_log2", "target_log2"]


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
        has_l3 = any((cache / "level").read_text().strip() == "3"
                     for cache in (root / f"cpu{cpu}" / "cache").glob("index*"))
        if cpu in performance:
            core_type = "P"
        elif cpu in efficient:
            core_type = "E" if has_l3 else "LP-E"
        else:
            core_type = "unique"
        max_freq = root / f"cpu{cpu}" / "cpufreq" / "cpuinfo_max_freq"
        rows.append({"cpu": cpu, "core_type": core_type, "has_l3": int(has_l3),
                     "max_freq_khz": max_freq.read_text().strip() if max_freq.exists() else ""})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=sorted(SETTINGS))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    settings = SETTINGS[args.mode]
    topology = read_topology()
    preferred = [row["cpu"] for row in topology if row["core_type"] in ("P", "unique")]
    # Même CPU que A2 (le CPU P de plus grand numéro), pour comparer les observations.
    cpu = max(preferred)

    plan = []
    for compiler in COMPILERS:
        for level in LEVELS:
            for _ in range(settings["runs"]):
                plan.append({"binary": f"build/bench-{compiler}-{level}", "compiler": compiler,
                             "level": level, "cpu": cpu,
                             **{key: settings[key] for key in PLAN_FIELDS if key in settings}})
    random.Random(BASE_SEED).shuffle(plan)
    for run_id, row in enumerate(plan, start=1):
        row["run_id"] = run_id
        row["seed"] = BASE_SEED  # même tableau pour tous : seule la compilation varie

    args.directory.mkdir(parents=True, exist_ok=True)
    for name, fields, rows in (("topology.csv", list(topology[0]), topology),
                               ("plan.csv", PLAN_FIELDS, plan)):
        with (args.directory / name).open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print(f"plan={args.directory / 'plan.csv'} processes={len(plan)} cpu={cpu}")


if __name__ == "__main__":
    main()
