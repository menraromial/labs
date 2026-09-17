#!/usr/bin/env python3
"""Résumés et figures du projet E2.

Règles fixées avant la campagne (README, section 7) : unité statistique le processus ;
T_inf = médiane du dernier tiers des pas (200 à 299 en campagne) ; rho0 = T_0 / T_inf ; E = somme des excès sur T_inf ;
allocation : c, b50, b99, bmax par processus ; entre processus, médiane et bootstrap
percentile à 95 % ; rapports entre modes par bootstrap de chaque groupe ; démarrage :
médiane et bootstrap sur les répétitions.
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import figstyle  # noqa: E402
from matplotlib.ticker import NullLocator  # noqa: E402

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260923
STARTUP = ("c-dynamic", "c-static", "rust", "go", "python", "python-no-site", "python-isolated", "python-numpy",
           "node", "node-jitless", "java", "java-no-cds")
STARTUP_LABELS = {"c-dynamic": "C\ndynamique", "c-static": "C\nstatique", "rust": "Rust", "go": "Go",
                  "python": "Python", "python-no-site": "Python\n-S", "python-isolated": "Python\n-I -S",
                  "python-numpy": "Python\n+ NumPy", "node": "Node", "node-jitless": "Node\n--jitless",
                  "java": "Java", "java-no-cds": "Java\nsans CDS"}
STARTUP_RATIOS = (("c-static", "c-dynamic"), ("python-no-site", "python"), ("python-isolated", "python-no-site"),
                  ("python-numpy", "python"), ("node-jitless", "node"), ("java-no-cds", "java"))
WARM_MODES = ("c", "java", "java-xint", "java-2cpu", "node", "node-jitless", "node-2cpu", "python", "python-jit")
WORKLOADS = ("hash_chain", "dot")
WORKLOAD_TITLES = {"hash_chain": "chaîne de hachage", "dot": "produit scalaire"}
FAMILIES = (("Java (HotSpot)", ("java", "java-xint", "java-2cpu")),
            ("Node (V8)", ("node", "node-jitless", "node-2cpu")),
            ("CPython", ("python", "python-jit")))
ROLE_STYLE = {"java": ("JIT, 1 cœur", 0, "-"), "node": ("JIT, 1 cœur", 0, "-"), "python": ("sans JIT", 1, "--"),
              "java-xint": ("interpréteur seul", 1, "--"), "node-jitless": ("interpréteur seul", 1, "--"),
              "java-2cpu": ("JIT, 2 cœurs", 2, "-."), "node-2cpu": ("JIT, 2 cœurs", 2, "-."),
              "python-jit": ("JIT", 0, "-")}
CHURN_MODES = ("c", "go-gogc100", "go-gogc400", "java-g1", "java-serial", "node", "python-gc", "python-nogc")
CHURN_LABELS = {"c": "C\nmalloc", "go-gogc100": "Go\nGOGC 100", "go-gogc400": "Go\nGOGC 400", "java-g1": "Java\nG1",
                "java-serial": "Java\nSerial", "node": "Node", "python-gc": "Python\ngc", "python-nogc": "Python\nsans gc"}


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


def bootstrap(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.median(values[rng.integers(0, values.size, size=(BOOTSTRAP_SAMPLES, values.size))], axis=1)
    low, high = np.percentile(draws, [2.5, 97.5])
    return float(np.median(values)), float(low), float(high), draws


def summary(values, digits=4):
    center, low, high, _ = bootstrap(values)
    return {"median": fmt(center, digits), "ci95_low": fmt(low, digits), "ci95_high": fmt(high, digits),
            "min": fmt(min(values), digits), "max": fmt(max(values), digits)}


def group_ratio(top, bottom):
    _, _, _, top_draws = bootstrap(top)
    _, _, _, bottom_draws = bootstrap(bottom)
    low, high = np.percentile(top_draws / bottom_draws, [2.5, 97.5])
    return float(np.median(top) / np.median(bottom)), float(low), float(high)


# ---------------------------------------------------------------- partie 1 : démarrage

def startup_analysis(directory):
    records = read_csv(directory / "startup.csv")
    table = {label: [int(r["elapsed_ns"]) / 1e6 for r in records if r["label"] == label] for label in STARTUP}
    rows = [{"label": label, "repetitions": len(v), **summary(v, 3),
             "p10": fmt(float(np.percentile(v, 10)), 3), "p90": fmt(float(np.percentile(v, 90)), 3)}
            for label, v in table.items()]
    ratios = []
    for top, bottom in STARTUP_RATIOS:
        center, low, high = group_ratio(table[top], table[bottom])
        ratios.append({"ratio": f"{top}/{bottom}", "median": fmt(center, 3), "ci95_low": fmt(low, 3),
                       "ci95_high": fmt(high, 3)})
    return rows, ratios, table


def decomposition_analysis(directory):
    values = defaultdict(list)
    for path in sorted((directory / "decomposition").glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        kind = path.stem.rsplit("-", 1)[0]
        if kind.startswith("python"):
            top = [(int(m.group(2)), m.group(3)) for m in
                   re.finditer(r"import time:\s+(\d+) \|\s+(\d+) \| (\S.*)$", text, re.M)]
            values[f"{kind}: imports (ms)"].append(sum(c for c, _ in top) / 1000)
            for cumulative, name in top:
                if name in ("site", "numpy"):
                    values[f"{kind}: import {name} (ms)"].append(cumulative / 1000)
        elif kind == "go":
            last = re.findall(r"@([\d.]+) ms, ([\d.]+) ms clock", text)
            if last:
                values["go: fin des init depuis le démarrage du runtime (ms)"].append(
                    float(last[-1][0]) + float(last[-1][1]))
                values["go: durée des init (ms)"].append(sum(float(c) for _, c in last))
        elif kind == "java":
            for phase, seconds in re.findall(r"\[startuptime\] (.+?), ([\d.]+) secs", text):
                values[f"java: {phase} (ms)"].append(float(seconds) * 1000)
    return [{"quantity": k, "repetitions": len(v), "median": fmt(float(np.median(v)), 3),
             "min": fmt(min(v), 3), "max": fmt(max(v), 3)} for k, v in values.items()]


# ---------------------------------------------------------------- partie 2 : échauffement

def warm_analysis(directory, plan):
    processes = defaultdict(list)
    for planned in plan:
        if planned["part"] != "warm":
            continue
        rows = read_csv(directory / f"warm-{int(planned['run_id']):03d}.csv")
        per = {}
        for workload in WORKLOADS:
            steps = np.array([int(r["elapsed_ns"]) for r in rows if r["workload"] == workload], dtype=float) / 1e6
            steady = float(np.median(steps[2 * len(steps) // 3:]))   # pas 200 à 299 en campagne
            per[workload] = {"steps": steps, "steady": steady, "rho0": steps[0] / steady,
                             "excess": float(np.sum(np.maximum(0.0, steps - steady))),
                             "elements": int(rows[0]["elements"])}
        processes[planned["mode"]].append(per)
    rows, ratios = [], []
    for workload in WORKLOADS:
        reference = [p[workload]["steady"] for p in processes["c"]]
        for mode in WARM_MODES:
            selected = processes[mode]
            steady = [p[workload]["steady"] for p in selected]
            elements = selected[0][workload]["elements"]
            center, low, high = group_ratio(steady, reference)
            rows.append({"workload": workload, "mode": mode, "processes": len(selected),
                         "steady_ns_per_element": fmt(float(np.median(steady)) * 1e6 / elements, 3),
                         "R_to_c": fmt(center, 3), "R_ci95_low": fmt(low, 3), "R_ci95_high": fmt(high, 3),
                         "rho0_median": fmt(float(np.median([p[workload]["rho0"] for p in selected])), 2),
                         "rho0_min": fmt(min(p[workload]["rho0"] for p in selected), 2),
                         "rho0_max": fmt(max(p[workload]["rho0"] for p in selected), 2),
                         "E_ms_median": fmt(float(np.median([p[workload]["excess"] for p in selected])), 2),
                         "E_in_steady_steps": fmt(float(np.median([p[workload]["excess"] / p[workload]["steady"]
                                                                    for p in selected])), 1)})
        for top, bottom, field in (("java-2cpu", "java", "excess"), ("node-2cpu", "node", "excess"),
                                   ("java-2cpu", "java", "steady"), ("node-2cpu", "node", "steady"),
                                   ("python-jit", "python", "steady")):
            center, low, high = group_ratio([p[workload][field] for p in processes[top]],
                                            [p[workload][field] for p in processes[bottom]])
            ratios.append({"workload": workload, "ratio": f"{top}/{bottom} {field}", "median": fmt(center, 3),
                           "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3)})
    return rows, ratios, processes


# ---------------------------------------------------------------- partie 3 : allocation

def churn_analysis(directory, plan):
    processes = defaultdict(list)
    for planned in plan:
        if planned["part"] != "churn":
            continue
        run_id = int(planned["run_id"])
        batches = np.array([int(r["elapsed_ns"]) for r in read_csv(directory / f"churn-{run_id:03d}.csv")],
                           dtype=float) / 1e6
        meta = read_csv(directory / f"churn-{run_id:03d}-meta.csv")[0]
        processes[planned["mode"]].append({
            "batches": batches, "c": batches.sum() * 1e6 / int(meta["operations"]),
            "b50": float(np.median(batches)), "b99": float(np.percentile(batches, 99)),
            "bmax": float(batches.max()), "gc": int(meta["gc_count"]), "pause": int(meta["gc_pause_ns"]) / 1e6,
            "rss": int(meta["peak_rss_kib"]) / 1024, "runtime": meta["runtime"]})
    rows = []
    for mode in CHURN_MODES:
        selected = processes[mode]
        row = {"mode": mode, "runtime": selected[0]["runtime"], "processes": len(selected)}
        for key, digits in (("c", 2), ("b50", 3), ("b99", 3), ("bmax", 3), ("gc", 0), ("pause", 2), ("rss", 1)):
            s = summary([p[key] for p in selected], digits)
            row.update({f"{key}_median": s["median"], f"{key}_ci95_low": s["ci95_low"],
                        f"{key}_ci95_high": s["ci95_high"], f"{key}_min": s["min"], f"{key}_max": s["max"]})
        row["bmax_over_b50_median"] = fmt(float(np.median([p["bmax"] / p["b50"] for p in selected])), 2)
        row["b99_over_b50_median"] = fmt(float(np.median([p["b99"] / p["b50"] for p in selected])), 2)
        rows.append(row)
    ratios = []
    for top, bottom in (("go-gogc400", "go-gogc100"), ("java-serial", "java-g1"), ("python-nogc", "python-gc")):
        for key in ("c", "bmax", "gc", "rss"):
            top_values = [p[key] for p in processes[top]]
            bottom_values = [p[key] for p in processes[bottom]]
            if np.median(bottom_values) == 0:
                continue
            center, low, high = group_ratio(top_values, bottom_values)
            ratios.append({"ratio": f"{top}/{bottom} {key}", "median": fmt(center, 3), "ci95_low": fmt(low, 3),
                           "ci95_high": fmt(high, 3)})
    return rows, ratios, processes


# ---------------------------------------------------------------- figures

def categorical(axis, labels):
    axis.set_xticks(range(len(labels)), labels)
    axis.tick_params(axis="x", length=0)
    axis.grid(axis="x", visible=False)
    axis.set_xlim(-0.6, len(labels) - 0.4)


def log_ticks(axis, values, pad=1.8, top_pad=None, multipliers=(1, 3)):
    data = np.asarray(values, dtype=float)
    low, high = data.min() / pad, data.max() * (top_pad or pad)
    ticks = [m * 10.0 ** e for e in range(-4, 7) for m in multipliers if low <= m * 10.0 ** e <= high]
    axis.set_yscale("log")
    axis.set_ylim(low, high)
    figstyle.fixed_ticks(axis, "y", ticks)


def plot_startup(table, path):
    figure, axis = figstyle.subplots(1, 1, height=2.5)
    everything = []
    for x, label in enumerate(STARTUP):
        values = table[label]
        everything.extend(values)
        figstyle.strip(axis, x - 0.1, values, width=0.08, seed=x, color=figstyle.PALETTE[0], s=5, alpha=0.4,
                       label="Une répétition" if x == 0 else None)
        center, low, high, _ = bootstrap(values)
        figstyle.interval(axis, x + 0.2, center, low, high, markersize=2.8,
                          label="Médiane, IC 95 %" if x == 0 else None)
    categorical(axis, [STARTUP_LABELS[s] for s in STARTUP])
    log_ticks(axis, everything, pad=2.0, top_pad=6)
    axis.set_ylabel(r"Démarrage $D$ (ms)")
    axis.legend(ncols=2)
    figstyle.save(figure, path)


def plot_warmup(processes, path):
    figure, axes = figstyle.subplots(3, 2, height=5.4)
    for row, (family, modes) in enumerate(FAMILIES):
        for column, workload in enumerate(WORKLOADS):
            axis = axes[row][column]
            values = []
            for mode in ("c",) + modes:
                selected = processes[mode]
                elements = selected[0][workload]["elements"]
                curve = np.median(np.vstack([p[workload]["steps"] for p in selected]), axis=0) * 1e6 / elements
                values.append(curve)
                values.extend(p[workload]["steps"] * 1e6 / elements for p in selected)
                steps = np.arange(1, curve.size + 1)
                if mode == "c":
                    axis.plot(steps, curve, color=figstyle.INK, linestyle=":", linewidth=1.0, label="C -O2")
                else:
                    label, slot, style = ROLE_STYLE[mode]
                    for process in selected:   # chaque processus en trait fin : régimes multiples visibles
                        axis.plot(steps, process[workload]["steps"] * 1e6 / elements, color=figstyle.PALETTE[slot],
                                  linewidth=0.35, alpha=0.25, zorder=1)
                    axis.plot(steps, curve, color=figstyle.PALETTE[slot], linestyle=style, label=label, zorder=3)
            axis.set_xscale("log")
            axis.set_xticks([1, 10, 100, 300], ["1", "10", "100", "300"])
            axis.xaxis.set_minor_locator(NullLocator())
            log_ticks(axis, np.concatenate(values), pad=1.6, top_pad=8, multipliers=(1,))
            axis.set_ylabel("ns par élément")
            if row == 2:
                axis.set_xlabel(r"Pas $k + 1$ depuis le lancement")
            axis.legend(ncols=2)
            figstyle.panel_title(axis, "abcdef"[2 * row + column], f"{family}, {WORKLOAD_TITLES[workload]}")
    figstyle.save(figure, path)


def plot_gc(processes, path):
    figure, (cost_axis, tail_axis) = figstyle.subplots(1, 2, height=2.7, gridspec_kw={"width_ratios": (1.5, 1)})
    everything = []
    for x, mode in enumerate(CHURN_MODES):
        values = [p["c"] for p in processes[mode]]
        everything.extend(values)
        figstyle.strip(cost_axis, x - 0.08, values, width=0.06, seed=x, color=figstyle.PALETTE[0], s=7,
                       label="Un processus" if x == 0 else None)
        center, low, high, _ = bootstrap(values)
        figstyle.interval(cost_axis, x + 0.18, center, low, high, markersize=2.6,
                          label="Médiane, IC 95 %" if x == 0 else None)
    categorical(cost_axis, [CHURN_LABELS[m] for m in CHURN_MODES])
    log_ticks(cost_axis, everything, pad=2.0, top_pad=5)
    cost_axis.set_ylabel(r"Coût par opération $c$ (ns)")
    cost_axis.legend()
    figstyle.panel_title(cost_axis, "a", "Allouer un objet, en abandonner un")

    styles = {"c": (figstyle.INK, ":"), "go-gogc100": (figstyle.PALETTE[0], "-"),
              "java-g1": (figstyle.PALETTE[1], "-"), "java-serial": (figstyle.PALETTE[1], "--"),
              "node": (figstyle.PALETTE[2], "-"), "python-gc": (figstyle.PALETTE[3], "-")}
    for mode, (color, style) in styles.items():
        ratios = np.concatenate([p["batches"] / p["b50"] for p in processes[mode]])
        figstyle.ccdf(tail_axis, ratios, color=color, linestyle=style,
                      label=CHURN_LABELS[mode].replace("\n", " "))
    tail_axis.set_xscale("log")
    tail_axis.set_yscale("log")
    tail_axis.set(xlabel=r"Durée d'un lot / $b_{50}$ du processus", ylabel="Fraction des lots au-delà")
    tail_axis.legend()
    figstyle.panel_title(tail_axis, "b", "Queue des durées de lot (pauses)")
    figstyle.save(figure, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--figures", type=Path)
    args = parser.parse_args()
    plan = read_csv(args.directory / "plan.csv")
    prefix = str(args.reports)
    startup, startup_ratios, startup_table = startup_analysis(args.directory)
    write_csv(Path(f"{prefix}-startup.csv"), startup)
    write_csv(Path(f"{prefix}-startup-ratios.csv"), startup_ratios)
    write_csv(Path(f"{prefix}-decomposition.csv"), decomposition_analysis(args.directory))
    warm, warm_ratios, warm_processes = warm_analysis(args.directory, plan)
    write_csv(Path(f"{prefix}-warmup.csv"), warm)
    write_csv(Path(f"{prefix}-warmup-ratios.csv"), warm_ratios)
    churn, churn_ratios, churn_processes = churn_analysis(args.directory, plan)
    write_csv(Path(f"{prefix}-gc.csv"), churn)
    write_csv(Path(f"{prefix}-gc-ratios.csv"), churn_ratios)
    if args.figures is not None:
        figstyle.use("times")
        plot_startup(startup_table, Path(f"{args.figures}-startup.pdf"))
        plot_warmup(warm_processes, Path(f"{args.figures}-warmup.pdf"))
        plot_gc(churn_processes, Path(f"{args.figures}-gc.pdf"))
    print(f"processus={len(plan)}")


if __name__ == "__main__":
    main()
