#!/usr/bin/env python3
"""Prépare une campagne D2 : topologie, chemins des compteurs du stockage et plan des processus.

Toutes les mesures sur le cœur P de plus grand numéro, choisi avant la mesure ;
ordre des processus sans objet (un seul type de cœur) mais plan écrit avant la
première mesure, comme dans les autres projets.
"""

import argparse
import csv
import os
import random
from pathlib import Path

BASE_SEED = 20260921
CORE = "P"

SETTINGS = {
    "check": {"runs": 1, "rounds": 2, "warmup_rounds": 1, "ops": 256, "file_mib": 8},
    "quick": {"runs": 1, "rounds": 3, "warmup_rounds": 1, "ops": 256, "file_mib": 256},
    "campaign": {"runs": 10, "rounds": 11, "warmup_rounds": 1, "ops": 256, "file_mib": 256},
}

PLAN_FIELDS = ["run_id", "core", "cpu", "seed", "rounds", "warmup_rounds", "ops", "file_mib",
               "device_stat", "journal_info"]


def parse_cpu_list(text):
    cpus = []
    for part in text.strip().split(","):
        if "-" in part:
            first, last = part.split("-")
            cpus.extend(range(int(first), int(last) + 1))
        elif part:
            cpus.append(int(part))
    return cpus


def performance_cpu():
    core = Path("/sys/devices/cpu_core/cpus")
    if core.exists():
        return max(parse_cpu_list(core.read_text()))
    return max(parse_cpu_list(Path("/sys/devices/system/cpu/online").read_text()))


def storage_paths(directory):
    """Périphérique bloc du système de fichiers, disque physique sous-jacent et journal ext4."""
    device = os.stat(directory).st_dev
    block = Path(f"/sys/dev/block/{os.major(device)}:{os.minor(device)}").resolve()
    journal = Path(f"/proc/fs/jbd2/{block.name}-8/info")
    disk = block
    while (disk / "slaves").is_dir() and any((disk / "slaves").iterdir()):
        disk = next((disk / "slaves").iterdir()).resolve()   # dm-0 -> nvme0n1p2
    if (disk / "partition").exists():
        disk = disk.parent                                    # nvme0n1p2 -> nvme0n1
    return {"filesystem_device": block.name, "disk": disk.name, "device_stat": f"/sys/block/{disk.name}/stat",
            "journal_info": str(journal)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=sorted(SETTINGS))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()

    settings = SETTINGS[args.mode]
    storage = storage_paths(args.scratch)
    for key in ("device_stat", "journal_info"):
        if not Path(storage[key]).exists():
            raise SystemExit(f"{storage[key]} introuvable : compteurs de mécanisme indisponibles")
    cpu = performance_cpu()
    plan = [{"core": CORE, "cpu": cpu, "seed": BASE_SEED, **{k: settings[k] for k in PLAN_FIELDS if k in settings},
             "device_stat": storage["device_stat"], "journal_info": storage["journal_info"]}
            for _ in range(settings["runs"])]
    random.Random(BASE_SEED).shuffle(plan)
    for run_id, row in enumerate(plan, start=1):
        row["run_id"] = run_id

    args.directory.mkdir(parents=True, exist_ok=True)
    with (args.directory / "plan.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=PLAN_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(plan)
    with (args.directory / "storage.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(storage), lineterminator="\n")
        writer.writeheader()
        writer.writerow(storage)
    print(f"plan={args.directory / 'plan.csv'} processes={len(plan)} cpu={cpu} "
          f"disk={storage['disk']} journal={storage['journal_info']}")


if __name__ == "__main__":
    main()
