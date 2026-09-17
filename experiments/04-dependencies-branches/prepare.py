#!/usr/bin/env python3
"""Prépare une campagne B2 : topologie, CPU d'épinglage et plan complet des processus.

Un processus exécute un seul binaire. L'ordre des processus est tiré au hasard
avec une graine fixe ; tous sont épinglés sur le même CPU P, choisi avant la
mesure (le CPU P de plus grand numéro, comme en A2 et B1).
"""

import argparse
import csv
import random
from pathlib import Path

BASE_SEED = 20260917
BUILDS = ("gcc-scalar", "gcc-O2", "gcc-O3-v3", "clang-scalar", "clang-O2", "clang-O3-v3")

SETTINGS = {
    "check": {"runs": 1, "rounds": 2, "warmup_rounds": 1, "calls_shift": 6},
    "quick": {"runs": 2, "rounds": 4, "warmup_rounds": 1, "calls_shift": 2},
    "campaign": {"runs": 15, "rounds": 21, "warmup_rounds": 1, "calls_shift": 0},
}

PLAN_FIELDS = ["run_id", "binary", "build", "cpu", "seed", "rounds", "warmup_rounds", "calls_shift"]


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
        core_type = ("P" if cpu in performance else
                     ("E" if has_l3 else "LP-E") if cpu in efficient else "unique")
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
    cpu = max(row["cpu"] for row in topology if row["core_type"] in ("P", "unique"))
    plan = [{"binary": f"build/bench-{build}", "build": build, "cpu": cpu,
             "rounds": settings["rounds"], "warmup_rounds": settings["warmup_rounds"],
             "calls_shift": settings["calls_shift"]}
            for build in BUILDS for _ in range(settings["runs"])]
    random.Random(BASE_SEED).shuffle(plan)
    for run_id, row in enumerate(plan, start=1):
        row["run_id"] = run_id
        row["seed"] = BASE_SEED  # mêmes valeurs pour tous : seuls le binaire et l'ordre de mélange varient

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
