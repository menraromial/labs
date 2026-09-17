#!/usr/bin/env python3
"""Prépare une campagne E1 : plan des processus, un par ligne, dans un ordre aléatoire fixé.

Chaque processus exécute une version (C -O2, C -O3, Rust, Go, Python), épinglée sur le
cœur P de plus grand numéro, choisi avant la mesure.
"""

import argparse
import csv
import random
from pathlib import Path

BASE_SEED = 20260922
BUILDS = ("c-O2", "c-O3", "rust", "go", "python")
SETTINGS = {
    "check": {"runs": 1, "rounds": 2, "warmup_rounds": 1, "scale_log2": 8, "startup_reps": 3},
    "quick": {"runs": 1, "rounds": 3, "warmup_rounds": 1, "scale_log2": 0, "startup_reps": 10},
    "campaign": {"runs": 10, "rounds": 11, "warmup_rounds": 1, "scale_log2": 0, "startup_reps": 50},
}
PLAN_FIELDS = ["run_id", "build", "cpu", "seed", "rounds", "warmup_rounds", "scale_log2"]


def parse_cpu_list(text):
    cpus = []
    for part in text.strip().split(","):
        first, _, last = part.partition("-")
        cpus.extend(range(int(first), int(last or first) + 1))
    return cpus


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=sorted(SETTINGS))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    settings = SETTINGS[args.mode]
    cpu = max(parse_cpu_list(Path("/sys/devices/cpu_core/cpus").read_text()))
    plan = [{"build": build, "cpu": cpu, "seed": BASE_SEED, "rounds": settings["rounds"],
             "warmup_rounds": settings["warmup_rounds"], "scale_log2": settings["scale_log2"]}
            for build in BUILDS for _ in range(settings["runs"])]
    random.Random(BASE_SEED).shuffle(plan)
    for run_id, row in enumerate(plan, start=1):
        row["run_id"] = run_id
    args.directory.mkdir(parents=True, exist_ok=True)
    with (args.directory / "plan.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=PLAN_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(plan)
    (args.directory / "startup-reps.txt").write_text(f"{settings['startup_reps']}\n", encoding="utf-8")
    print(f"plan={args.directory / 'plan.csv'} processes={len(plan)} cpu={cpu}")


if __name__ == "__main__":
    main()
