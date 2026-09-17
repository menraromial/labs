#!/usr/bin/env python3
"""Résumés et figures du projet E1.

Règles fixées avant la campagne (README, section 7) : unité statistique le processus ;
t = médiane des tours mesurés du coût par élément ; entre processus, médiane et bootstrap
percentile à 95 % ; rapports entre variantes par processus ; rapports entre versions par
bootstrap de chaque groupe ; démarrage : médiane et bootstrap sur les répétitions.
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import figstyle  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260922
BUILDS = ("c-O2", "c-O3", "rust", "go", "python")
BUILD_LABELS = {"c-O2": "C -O2", "c-O3": "C -O3", "rust": "Rust", "go": "Go", "python": "Python"}
WORKLOADS = ("hash_chain", "dot", "count")
WORKLOAD_TITLES = {"hash_chain": "Chaîne de hachage entière", "dot": "Produit scalaire flottant",
                   "count": "Comptage par table de hachage"}
VARIANT_STYLE = {"control": ("Traduction contrôlée", figstyle.PALETTE[0], "o"),
                 "idiomatic": ("Écriture idiomatique", figstyle.PALETTE[1], "s"),
                 "numpy": ("NumPy", figstyle.PALETTE[2], "^")}
STARTUP = ("c-O2", "c-O3", "rust", "go", "python", "python-numpy")
STARTUP_LABELS = {**BUILD_LABELS, "python-numpy": "Python\n+ NumPy"}


def fmt(value, digits=4):
    return f"{value:.{digits}f}" if value is not None and np.isfinite(value) else ""


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        fields = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(target, fieldnames=fields, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def bootstrap(values, statistic=np.median, rng_seed=BOOTSTRAP_SEED):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(rng_seed)
    draws = statistic(values[rng.integers(0, values.size, size=(BOOTSTRAP_SAMPLES, values.size))], axis=1)
    low, high = np.percentile(draws, [2.5, 97.5])
    return float(statistic(values)), float(low), float(high), draws


# ---------------------------------------------------------------- lecture

def load(directory):
    processes = []
    for planned in read_csv(directory / "plan.csv"):
        run_id = int(planned["run_id"])
        rows = read_csv(directory / f"run-{run_id:03d}.csv")
        meta = read_csv(directory / f"run-{run_id:03d}-meta.csv")[0]
        per_element, sample, first, gc_samples = defaultdict(list), defaultdict(list), {}, defaultdict(int)
        for row in rows:
            key = (row["workload"], row["variant"])
            elapsed = int(row["elapsed_ns"])
            if row["phase"] == "warmup":
                first[key] = elapsed
                continue
            per_element[key].append(elapsed / int(row["elements"]))
            sample[key].append(elapsed)
            gc_samples[key] += int(row["gc_delta"]) > 0
        processes.append({"run_id": run_id, "build": planned["build"], "meta": meta,
                          "t": {k: float(np.median(v)) for k, v in per_element.items()},
                          "T": {k: float(np.median(v)) for k, v in sample.items()},
                          "first": first, "gc_samples": gc_samples})
    return processes


# ---------------------------------------------------------------- analyses

def cost_rows(groups):
    rows, table = [], {}
    for build, selected in groups.items():
        for key in sorted(selected[0]["t"]):
            values = [p["t"][key] for p in selected]
            center, low, high, draws = bootstrap(values)
            table[(build,) + key] = (values, center, low, high, draws)
            rows.append({"build": build, "workload": key[0], "variant": key[1], "processes": len(values),
                         "median_ns_per_element": fmt(center, 4), "ci95_low": fmt(low, 4),
                         "ci95_high": fmt(high, 4), "min": fmt(min(values), 4), "max": fmt(max(values), 4),
                         "samples_with_gc": sum(p["gc_samples"][key] for p in selected)})
    return rows, table


def between_build_rows(table):
    rows = []
    for workload in WORKLOADS:
        reference = table[("c-O2", workload, "control")]
        for build in BUILDS:
            for variant in ("control", "idiomatic", "numpy"):
                key = (build, workload, variant)
                if key not in table:
                    continue
                draws = table[key][4] / reference[4]
                low, high = np.percentile(draws, [2.5, 97.5])
                rows.append({"workload": workload, "build": build, "variant": variant,
                             "ratio_to_c_O2_control": fmt(table[key][1] / reference[1], 3),
                             "ci95_low": fmt(float(low), 3), "ci95_high": fmt(float(high), 3)})
    return rows


def within_process_rows(groups):
    pairs = (("idiomatic/control", "idiomatic", "control", "t"),
             ("aa control_bis/control", "control_bis", "control", "T"),
             ("positive control_double/control", "control_double", "control", "T"),
             ("aa idiomatic_bis/idiomatic", "idiomatic_bis", "idiomatic", "T"),
             ("numpy/control", "numpy", "control", "t"),
             ("numpy/idiomatic", "numpy", "idiomatic", "t"))
    rows = []
    for build, selected in groups.items():
        for workload in WORKLOADS:
            for name, top, bottom, field in pairs:
                if (workload, top) not in selected[0][field] or (workload, bottom) not in selected[0][field]:
                    continue
                values = [p[field][(workload, top)] / p[field][(workload, bottom)] for p in selected]
                center, low, high, _ = bootstrap(values)
                rows.append({"build": build, "workload": workload, "ratio": name, "median": fmt(center, 3),
                             "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3), "min": fmt(min(values), 3),
                             "max": fmt(max(values), 3)})
    return rows


def warmup_rows(groups):
    rows = []
    for build, selected in groups.items():
        for key in sorted(selected[0]["T"]):
            values = [p["first"][key] / p["T"][key] for p in selected]
            rows.append({"build": build, "workload": key[0], "variant": key[1],
                         "first_over_steady_median": fmt(float(np.median(values)), 3),
                         "min": fmt(min(values), 3), "max": fmt(max(values), 3)})
    return rows


def meta_rows(groups):
    rows = []
    for build, selected in groups.items():
        rss = [int(p["meta"]["peak_rss_kib"]) for p in selected]
        rows.append({"build": build, "processes": len(selected), "runtime": selected[0]["meta"]["runtime"],
                     "peak_rss_mib_median": fmt(float(np.median(rss)) / 1024, 1),
                     "automatic_gc_total_max": max(int(p["meta"]["gc_total"]) for p in selected),
                     "jit": selected[0]["meta"]["jit"], "gil": selected[0]["meta"]["gil"]})
    return rows


def startup_rows(directory):
    rows, table = [], {}
    records = read_csv(directory / "startup.csv")
    for label in STARTUP:
        values = [int(r["elapsed_ns"]) / 1e6 for r in records if r["label"] == label]
        center, low, high, _ = bootstrap(values)
        table[label] = values
        rows.append({"label": label, "repetitions": len(values), "median_ms": fmt(center, 3),
                     "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3),
                     "p10_ms": fmt(float(np.percentile(values, 10)), 3),
                     "p90_ms": fmt(float(np.percentile(values, 90)), 3),
                     "max_rss_kib_median": fmt(float(np.median([int(r["max_rss_kib"]) for r in records
                                                                 if r["label"] == label])), 0)})
    return rows, table


# ---------------------------------------------------------------- figures

def log_ticks(axis, values, pad=1.8, top_pad=None):
    data = np.asarray(values, dtype=float)
    low, high = data.min() / pad, data.max() * (top_pad or pad)
    ticks = [m * 10.0 ** e for e in range(-3, 6) for m in (1, 3) if low <= m * 10.0 ** e <= high]
    axis.set_yscale("log")
    axis.set_ylim(low, high)
    figstyle.fixed_ticks(axis, "y", ticks)


def plot_steady(table, path):
    figure, axes = figstyle.subplots(1, 3, height=2.7)
    for letter, axis, workload in zip("abc", axes, WORKLOADS):
        everything = []
        for x, build in enumerate(BUILDS):
            present = [v for v in ("control", "idiomatic", "numpy") if (build, workload, v) in table]
            offsets = np.linspace(-0.22, 0.22, len(present)) if len(present) > 1 else [0.0]
            for offset, variant in zip(offsets, present):
                values, center, low, high, _ = table[(build, workload, variant)]
                everything.extend(values)
                _, color, marker = VARIANT_STYLE[variant]
                figstyle.strip(axis, x + offset - 0.03, values, width=0.03, seed=x * 7 + len(variant),
                               color=color, marker=marker, s=8)
                axis.errorbar([x + offset + 0.05], [center], yerr=[[center - low], [high - center]], fmt="_",
                              color=figstyle.INK, markersize=4, elinewidth=0.9, capsize=1.5, zorder=4)
        axis.set_xticks(range(len(BUILDS)), [BUILD_LABELS[b] for b in BUILDS])
        axis.tick_params(axis="x", length=0)
        axis.grid(axis="x", visible=False)
        axis.set_xlim(-0.6, len(BUILDS) - 0.4)
        log_ticks(axis, everything, pad=2.2, top_pad=6)   # bandeau libre pour la légende
        axis.set_ylabel(r"Coût par élément $t$ (ns)")
        figstyle.panel_title(axis, letter, WORKLOAD_TITLES[workload])
    handles = [Line2D([], [], color=VARIANT_STYLE[v][1], marker=VARIANT_STYLE[v][2], linestyle="none",
                      markersize=4, label=VARIANT_STYLE[v][0]) for v in ("control", "idiomatic", "numpy")]
    handles.append(Line2D([], [], color=figstyle.INK, marker="_", linestyle="none", markersize=6,
                          label="Médiane, IC 95 %"))
    axes[0].legend(handles=handles)
    figstyle.save(figure, path)


def plot_startup(startup, meta, path):
    figure, (time_axis, rss_axis) = figstyle.subplots(1, 2, height=2.4)
    everything = []
    for x, label in enumerate(STARTUP):
        values = startup[label]
        everything.extend(values)
        figstyle.strip(time_axis, x - 0.08, values, width=0.07, seed=x, color=figstyle.PALETTE[0],
                       s=6, alpha=0.45, label="Une répétition" if x == 0 else None)
        center, low, high, _ = bootstrap(values)
        figstyle.interval(time_axis, x + 0.18, center, low, high, label="Médiane, IC 95 %" if x == 0 else None)
    time_axis.set_xticks(range(len(STARTUP)), [STARTUP_LABELS[s] for s in STARTUP])
    time_axis.tick_params(axis="x", length=0)
    time_axis.grid(axis="x", visible=False)
    log_ticks(time_axis, everything, pad=2.0, top_pad=8)   # bandeau libre pour la légende
    time_axis.set_ylabel(r"Démarrage $D$ (ms)")
    time_axis.legend()
    figstyle.panel_title(time_axis, "a", "Lancer un programme qui se termine aussitôt")

    rss = [float(r["peak_rss_mib_median"]) for r in meta]
    labels = [BUILD_LABELS[r["build"]] for r in meta]
    rss_axis.barh(range(len(rss)), rss, color=figstyle.PALETTE[0], height=0.55)
    for y, value in enumerate(rss):
        rss_axis.text(value * 1.03, y, figstyle.french_number(value, 0), va="center", fontsize=6.5)
    rss_axis.set_yticks(range(len(rss)), labels)
    rss_axis.invert_yaxis()
    rss_axis.set_xlim(0, max(rss) * 1.18)
    rss_axis.grid(axis="y", visible=False)
    rss_axis.set_xlabel("Mémoire résidente maximale (Mio)")
    figstyle.panel_title(rss_axis, "b", "Mémoire d'un processus de mesure")
    figstyle.save(figure, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--figures", type=Path)
    args = parser.parse_args()

    processes = load(args.directory)
    groups = defaultdict(list)
    for process in processes:
        groups[process["build"]].append(process)
    groups = {b: groups[b] for b in BUILDS if b in groups}
    rows, table = cost_rows(groups)
    meta = meta_rows(groups)
    startup, startup_table = startup_rows(args.directory)
    prefix = str(args.reports)
    write_csv(Path(f"{prefix}-costs.csv"), rows)
    write_csv(Path(f"{prefix}-between-builds.csv"), between_build_rows(table))
    write_csv(Path(f"{prefix}-within-process.csv"), within_process_rows(groups))
    write_csv(Path(f"{prefix}-warmup.csv"), warmup_rows(groups))
    write_csv(Path(f"{prefix}-meta.csv"), meta)
    write_csv(Path(f"{prefix}-startup.csv"), startup)
    if args.figures is not None:
        figstyle.use("times")
        plot_steady(table, Path(f"{args.figures}-steady.pdf"))
        plot_startup(startup_table, meta, Path(f"{args.figures}-startup.pdf"))
    print(f"processus={len(processes)}")


if __name__ == "__main__":
    main()
