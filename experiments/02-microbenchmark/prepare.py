#!/usr/bin/env python3
"""Prépare une campagne : topologie des cœurs et plan complet des processus.

Le plan est écrit avant toute mesure. L'ordre des processus est tiré au hasard
avec une graine fixe, afin qu'aucun protocole ne profite systématiquement d'un
moment plus calme de la machine.
"""

import argparse
import csv
import random
from pathlib import Path

BASE_SEED = 20260916

SETTINGS = {
    "check": {"amortization_runs": 1, "amortization_rounds": 2, "max_batch": 8,
              "ladder_runs": 1, "affinity_runs": 1, "prime_runs": 1, "batch": 50,
              "rounds": 4, "warmup_rounds": 1, "warmup_ops": 10},
    "quick": {"amortization_runs": 3, "amortization_rounds": 10, "max_batch": 1024,
              "ladder_runs": 5, "affinity_runs": 2, "prime_runs": 0, "batch": 20000,
              "rounds": 30, "warmup_rounds": 5, "warmup_ops": 100000},
    "campaign": {"amortization_runs": 20, "amortization_rounds": 40, "max_batch": 32768,
                 "ladder_runs": 30, "affinity_runs": 15, "prime_runs": 0, "batch": 20000,
                 "rounds": 100, "warmup_rounds": 10, "warmup_ops": 100000},
    # Contrôle exploratoire, décidé après la première campagne (README, section 3 bis).
    "prime": {"amortization_runs": 0, "amortization_rounds": 0, "max_batch": 0,
              "ladder_runs": 0, "affinity_runs": 0, "prime_runs": 30, "batch": 1,
              "rounds": 1, "warmup_rounds": 0, "warmup_ops": 0},
}

PRIMES = ("none", "clock", "code", "full")

# « prime » est la dernière colonne : un plan plus ancien, sans elle, reste lisible.
PLAN_FIELDS = ["run_id", "protocol", "mode", "affinity", "cpu", "seed", "batch",
               "rounds", "warmup_rounds", "max_batch", "warmup_ops", "prime"]


def parse_cpu_list(text):
    cpus = []
    for part in text.strip().split(","):
        if not part:
            continue
        if "-" in part:
            first, last = part.split("-")
            cpus.extend(range(int(first), int(last) + 1))
        else:
            cpus.append(int(part))
    return cpus


def read_topology():
    """Classe chaque CPU logique : P (cpu_core), E (cpu_atom avec L3), LP-E (sans L3).

    La correspondance avec les cœurs « Performance », « Efficient » et « Low Power
    Efficient » du processeur est une interprétation des indications du noyau.
    """
    root = Path("/sys/devices/system/cpu")
    online = parse_cpu_list((root / "online").read_text())
    core = Path("/sys/devices/cpu_core/cpus")
    atom = Path("/sys/devices/cpu_atom/cpus")
    performance = set(parse_cpu_list(core.read_text())) if core.exists() else set()
    efficient = set(parse_cpu_list(atom.read_text())) if atom.exists() else set()
    rows = []
    for cpu in online:
        has_l3 = any((cache / "level").read_text().strip() == "3"
                     for cache in (root / f"cpu{cpu}" / "cache").glob("index*"))
        max_freq = root / f"cpu{cpu}" / "cpufreq" / "cpuinfo_max_freq"
        if cpu in performance:
            core_type = "P"
        elif cpu in efficient:
            core_type = "E" if has_l3 else "LP-E"
        else:
            core_type = "unique"
        rows.append({"cpu": cpu, "core_type": core_type, "has_l3": int(has_l3),
                     "max_freq_khz": max_freq.read_text().strip() if max_freq.exists() else ""})
    return rows


def pinned_cpus(topology):
    """Un CPU représentatif par type : le dernier numéro, choisi avant la mesure."""
    chosen = {}
    for row in topology:
        chosen[row["core_type"]] = row["cpu"]
    return chosen


def build_plan(settings, topology):
    common = {"batch": settings["batch"], "rounds": settings["rounds"],
              "warmup_rounds": settings["warmup_rounds"], "max_batch": "", "warmup_ops": 0,
              "prime": "none"}
    plan = []
    for _ in range(settings["amortization_runs"]):
        plan.append({"protocol": "amortization", "mode": "amortization", "affinity": "libre",
                     "cpu": "", "batch": "", "rounds": settings["amortization_rounds"],
                     "warmup_rounds": 0, "max_batch": settings["max_batch"],
                     "warmup_ops": settings["warmup_ops"], "prime": "none"})
    for _ in range(settings["ladder_runs"]):
        plan.append({**common, "protocol": "naive", "mode": "fixed", "affinity": "libre",
                     "cpu": "", "batch": 1, "rounds": 1, "warmup_rounds": 0})
        plan.append({**common, "protocol": "batched", "mode": "fixed", "affinity": "libre",
                     "cpu": "", "rounds": 1, "warmup_rounds": 0})
        plan.append({**common, "protocol": "interleaved", "mode": "interleaved",
                     "affinity": "libre", "cpu": ""})
    for core_type, cpu in pinned_cpus(topology).items():
        for _ in range(settings["affinity_runs"]):
            plan.append({**common, "protocol": "interleaved", "mode": "interleaved",
                         "affinity": core_type, "cpu": cpu})
    for _ in range(settings["prime_runs"]):
        for prime in PRIMES:
            plan.append({**common, "protocol": "naive", "mode": "fixed", "affinity": "libre",
                         "cpu": "", "batch": 1, "rounds": 1, "warmup_rounds": 0,
                         "prime": prime})

    random.Random(BASE_SEED).shuffle(plan)
    for run_id, row in enumerate(plan, start=1):
        row["run_id"] = run_id
        row["seed"] = BASE_SEED + run_id
    return plan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=sorted(SETTINGS))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    args.directory.mkdir(parents=True, exist_ok=True)
    topology = read_topology()
    with (args.directory / "topology.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=["cpu", "core_type", "has_l3", "max_freq_khz"],
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(topology)
    plan = build_plan(SETTINGS[args.mode], topology)
    with (args.directory / "plan.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=PLAN_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(plan)
    print(f"plan={args.directory / 'plan.csv'} processes={len(plan)}")


if __name__ == "__main__":
    main()
