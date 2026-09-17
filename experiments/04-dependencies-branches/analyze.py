#!/usr/bin/env python3
"""Résumés et figures du projet B2.

Règles fixées avant la campagne (README, section 7) : unité statistique le
processus ; médiane par processus sur les tours hors échauffement ; rapports
calculés par processus ; médiane et bootstrap percentile à 95 % entre
processus ; modèle de pénalité ajusté sur les médianes des 7 jeux mélangés ;
droite des petites boucles ajustée sur n = 256 à 1 024.
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

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260917
COMPILERS = ("gcc", "clang")
COMPILER_LABELS = {"gcc": "GCC", "clang": "Clang"}
VARIANTS = ("scalar", "O2", "O3-v3")
VARIANT_LABELS = {"scalar": "scalaire", "O2": "-O2", "O3-v3": "-O3 AVX2"}
BUILDS = tuple(f"{c}-{v}" for c in COMPILERS for v in VARIANTS)
DEPENDENCY_LABELS = ("chain_xor_mul", "split_xor_mul", "sum_one", "sum_four")
SHUFFLED = ("p000", "p100", "p250", "p500", "p750", "p900", "p1000")
PROBABILITY = {"p000": 0.0, "p100": 0.1, "p250": 0.25, "p500": 0.5, "p750": 0.75,
               "p900": 0.9, "p1000": 1.0}
BRANCH_KERNELS = ("sum_if", "filter_copy", "filter_copy_mask")
FIT_MIN_N = 256


def variant_of(build):
    return build.split("-", 1)[1]


def build_color(build):
    return figstyle.PALETTE[VARIANTS.index(variant_of(build))]


def build_marker(build):
    return figstyle.MARKERS[VARIANTS.index(variant_of(build))]


def fmt(value, digits=4):
    return f"{value:.{digits}f}" if np.isfinite(value) else ""


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        fields = list(dict.fromkeys(key for row in rows for key in row))  # union ordonnée
        writer = csv.DictWriter(target, fieldnames=fields, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def bootstrap_median(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(0, values.size, size=(BOOTSTRAP_SAMPLES, values.size))
    low, high = np.percentile(np.median(values[indices], axis=1), [2.5, 97.5])
    return float(np.median(values)), float(low), float(high)


# ---------------------------------------------------------------- lecture

def load(directory):
    """Par processus : médiane du coût par élément ou de la durée d'un appel, par mesure."""
    processes = []
    for planned in read_csv(directory / "plan.csv"):
        run_id = int(planned["run_id"])
        values = defaultdict(list)
        for row in read_csv(directory / f"run-{run_id:03d}.csv"):
            if row["phase"] != "measure":
                continue
            n, calls, elapsed = int(row["n"]), int(row["calls"]), int(row["elapsed_ns"])
            if row["part"] == "small":
                values[("small", row["label"], n)].append(elapsed / calls)
            else:
                values[(row["part"], row["label"], row["dataset"])].append(elapsed / (calls * n))
        processes.append({"build": planned["build"],
                          "value": {key: float(np.median(v)) for key, v in values.items()},
                          "meta": read_csv(directory / f"run-{run_id:03d}-meta.csv")[0]})
    return processes


def by_build(processes):
    groups = defaultdict(list)
    for process in processes:
        groups[process["build"]].append(process)
    return groups


# ---------------------------------------------------------------- analyses

def dependency_analysis(groups):
    rows, costs, ratios = [], {}, {}
    for build in BUILDS:
        selected = groups[build]
        for label in DEPENDENCY_LABELS + ("sum_one_bis", "sum_twice"):
            data = [p["value"][("dependency", label, "uniform")] for p in selected]
            costs[(build, label)] = bootstrap_median(data)
            rows.append({"build": build, "measure": label, "processes": len(data),
                         "median_ns_per_element": fmt(costs[(build, label)][0]),
                         "ci95_low": fmt(costs[(build, label)][1]), "ci95_high": fmt(costs[(build, label)][2])})
        for name, top, bottom in (("chain/split", "chain_xor_mul", "split_xor_mul"),
                                  ("one/four", "sum_one", "sum_four"),
                                  ("bis/one", "sum_one_bis", "sum_one"),
                                  ("twice/one", "sum_twice", "sum_one")):
            per_process = [p["value"][("dependency", top, "uniform")] / p["value"][("dependency", bottom, "uniform")]
                           for p in selected]
            center, low, high = bootstrap_median(per_process)
            ratios[(build, name)] = (per_process, center, low, high)
            rows.append({"build": build, "measure": name, "processes": len(per_process),
                         "median_ns_per_element": fmt(center), "ci95_low": fmt(low), "ci95_high": fmt(high),
                         "min": fmt(min(per_process)), "max": fmt(max(per_process))})
    return rows, costs, ratios


def branch_analysis(groups):
    rows, curves, penalty_rows = [], {}, []
    datasets = SHUFFLED + ("p500_sorted", "p500_alternating")
    for build in BUILDS:
        selected = groups[build]
        for kernel in BRANCH_KERNELS:
            medians = {}
            for dataset in datasets:
                data = [p["value"][("branch", kernel, dataset)] for p in selected]
                center, low, high = bootstrap_median(data)
                medians[dataset] = (center, low, high)
                rows.append({"build": build, "kernel": kernel, "dataset": dataset, "processes": len(data),
                             "median_ns_per_element": fmt(center), "ci95_low": fmt(low), "ci95_high": fmt(high)})
            shuffled_sorted = bootstrap_median([p["value"][("branch", kernel, "p500")] /
                                                p["value"][("branch", kernel, "p500_sorted")] for p in selected])
            alternating_sorted = bootstrap_median([p["value"][("branch", kernel, "p500_alternating")] /
                                                   p["value"][("branch", kernel, "p500_sorted")] for p in selected])
            spread = max(m[0] for m in medians.values()) / min(m[0] for m in medians.values())
            # Modèle fixé à l'avance : coût(p) = c + P min(p, 1 - p).
            x = np.array([min(PROBABILITY[d], 1 - PROBABILITY[d]) for d in SHUFFLED])
            y = np.array([medians[d][0] for d in SHUFFLED])
            design = np.column_stack([np.ones_like(x), x])
            (c, penalty), *_ = np.linalg.lstsq(design, y, rcond=None)
            fitted = design @ np.array([c, penalty])
            r2 = 1 - np.sum((y - fitted) ** 2) / np.sum((y - y.mean()) ** 2) if np.ptp(y) > 0 else float("nan")
            curves[(build, kernel)] = medians
            penalty_rows.append({
                "build": build, "kernel": kernel,
                "shuffled_over_sorted_p500": fmt(shuffled_sorted[0], 3),
                "ci95_low": fmt(shuffled_sorted[1], 3), "ci95_high": fmt(shuffled_sorted[2], 3),
                "alternating_over_sorted_p500": fmt(alternating_sorted[0], 3),
                "max_over_min_all_datasets": fmt(spread, 3),
                "fit_base_ns": fmt(c, 3), "fit_penalty_ns": fmt(penalty, 2), "fit_r2": fmt(r2, 3)})
    return rows, curves, penalty_rows


def small_analysis(groups):
    rows, curves = [], {}
    for build in BUILDS:
        selected = groups[build]
        sizes = sorted({key[2] for key in selected[0]["value"] if key[0] == "small"})
        medians = np.array([np.median([p["value"][("small", "sum_one", n)] for p in selected]) for n in sizes])
        x = np.asarray(sizes, dtype=float)
        mask = x >= FIT_MIN_N
        slope, intercept = np.polyfit(x[mask], medians[mask], 1)
        residual = medians - (intercept + slope * x)
        # Écart par processus, pour un intervalle sur chaque taille.
        per_process = np.array([[p["value"][("small", "sum_one", n)] for n in sizes] for p in selected])
        residual_process = per_process - (intercept + slope * x)
        low, high = np.percentile(residual_process, [25, 75], axis=0)
        curves[build] = {"sizes": x, "median": medians, "residual": residual, "q25": low, "q75": high,
                         "a": intercept, "b": slope}
        for i, n in enumerate(sizes):
            rows.append({"build": build, "n": n, "median_ns_per_call": fmt(medians[i], 3),
                         "fit_ns_per_call": fmt(intercept + slope * n, 3), "residual_ns": fmt(residual[i], 3),
                         "fit_a_ns": fmt(intercept, 3), "fit_b_ns_per_element": fmt(slope, 4)})
    return rows, curves


# ---------------------------------------------------------------- figures

def categorical(axis, labels):
    axis.set_xticks(range(len(labels)), labels)
    axis.tick_params(axis="x", length=0)
    axis.grid(axis="x", visible=False)
    axis.set_xlim(-0.6, len(labels) - 0.4)


def plot_dependencies(costs, ratios, path):
    figure, ((gcc, clang), (chain, four)) = figstyle.subplots(2, 2, height=3.9)
    names = ["chain_xor_mul", "split_xor_mul", "sum_one", "sum_four"]
    for axis, compiler, letter in ((gcc, "gcc", "a"), (clang, "clang", "b")):
        offsets = {"scalar": -0.22, "O2": 0.0, "O3-v3": 0.22}
        for variant in VARIANTS:
            build = f"{compiler}-{variant}"
            for x, label in enumerate(DEPENDENCY_LABELS):
                center, low, high = costs[(build, label)]
                figstyle.interval(axis, x + offsets[variant], center, low, high, color=build_color(build),
                                  marker=build_marker(build), markersize=3.4, capsize=1.5,
                                  label=VARIANT_LABELS[variant] if x == 0 else None)
        categorical(axis, names)
        axis.set_yscale("log")
        values = [costs[(f"{compiler}-{v}", l)][0] for v in VARIANTS for l in DEPENDENCY_LABELS]
        ticks = [t for t in (0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5) if min(values) / 1.6 <= t <= max(values) * 3]
        figstyle.fixed_ticks(axis, "y", ticks)
        axis.set_ylim(min(values) / 1.6, max(values) * 3)
        axis.set_ylabel("Coût par élément (ns)")
        axis.legend(title=COMPILER_LABELS[compiler], title_fontsize=6.5, ncols=3)
        figstyle.panel_title(axis, letter, f"{COMPILER_LABELS[compiler]} : coût selon la dépendance")

    for axis, name, expected, letter, title in (
            (chain, "chain/split", None, "c", "chain_xor_mul / split_xor_mul"),
            (four, "one/four", 1, "d", "sum_one / sum_four")):
        done = set()
        for x, build in enumerate(BUILDS):
            per_process, center, low, high = ratios[(build, name)]
            variant = variant_of(build)
            figstyle.strip(axis, x - 0.1, per_process, width=0.1, seed=x, color=build_color(build),
                           marker=build_marker(build), s=8,
                           label=VARIANT_LABELS[variant] if variant not in done else None)
            done.add(variant)
            figstyle.interval(axis, x + 0.2, center, low, high, markersize=2.6, capsize=1.5,
                              label="Médiane, IC 95 %" if x == 0 else None)
        if expected is not None:
            axis.axhline(expected, **figstyle.reference_style())
        categorical(axis, [f"{COMPILER_LABELS[b.split('-')[0]]}\n{VARIANT_LABELS[variant_of(b)]}" for b in BUILDS])
        axis.axvline(2.5, color=figstyle.GRID, linewidth=0.8, zorder=0)
        axis.set_yscale("log")
        everything = np.concatenate([ratios[(b, name)][0] for b in BUILDS])
        low_limit, high_limit = everything.min() / 1.3, everything.max() * 2.2
        figstyle.fixed_ticks(axis, "y", [t for t in (0.2, 0.5, 1, 2, 3, 5, 10) if low_limit <= t <= high_limit])
        axis.set_ylim(low_limit, high_limit)
        axis.set_ylabel("Rapport par processus")
        axis.legend(ncols=2)
        figstyle.panel_title(axis, letter, title)
    figstyle.save(figure, path)


def plot_branches(curves, path):
    figure, axes = figstyle.subplots(2, 3, height=3.9)
    x = np.array([PROBABILITY[d] for d in SHUFFLED])
    titles = {"sum_if": "sum_if", "filter_copy": "filter_copy (if)",
              "filter_copy_mask": "filter_copy_mask"}
    letters = iter("abcdef")
    top = max(m[0] for c in curves.values() for m in c.values()) * 1.5  # marge pour les légendes
    for row, compiler in enumerate(COMPILERS):
        for column, kernel in enumerate(BRANCH_KERNELS):
            axis = axes[row][column]
            for variant in VARIANTS:
                build = f"{compiler}-{variant}"
                medians = curves[(build, kernel)]
                y = np.array([medians[d][0] for d in SHUFFLED])
                low = np.array([medians[d][1] for d in SHUFFLED])
                high = np.array([medians[d][2] for d in SHUFFLED])
                color = build_color(build)
                axis.fill_between(x, low, high, color=color, alpha=0.18, linewidth=0)
                axis.plot(x, y, color=color, marker=build_marker(build), markersize=2.6,
                          label=VARIANT_LABELS[variant])
                offset = {"scalar": -0.02, "O2": 0.0, "O3-v3": 0.02}[variant]
                axis.scatter([0.465 + offset], [medians["p500_sorted"][0]], s=16, marker="s",
                             facecolors="white", edgecolors=color, linewidths=0.9, zorder=4)
                axis.scatter([0.535 + offset], [medians["p500_alternating"][0]], s=18, marker="x",
                             color=color, linewidths=0.9, zorder=4)
            axis.set_ylim(0, top)
            axis.set_xlim(-0.04, 1.04)
            figstyle.fixed_ticks(axis, "x", [0, 0.25, 0.5, 0.75, 1])
            figstyle.french_ticks(axis, "y")
            axis.set(xlabel="Part des éléments retenus p", ylabel="Coût par élément (ns)")
            if column == 0:
                axis.legend(title=COMPILER_LABELS[compiler], title_fontsize=6.5)
            if column == 1:
                from matplotlib.lines import Line2D
                handles = [Line2D([], [], color=figstyle.INK, marker="o", markersize=2.6, label="ordre aléatoire"),
                           Line2D([], [], color=figstyle.INK, marker="s", markerfacecolor="white",
                                  linestyle="none", markersize=3.6, label="p = 0,5 trié"),
                           Line2D([], [], color=figstyle.INK, marker="x", linestyle="none",
                                  markersize=3.6, label="p = 0,5 alterné")]
                axis.legend(handles=handles)
            figstyle.panel_title(axis, next(letters), f"{COMPILER_LABELS[compiler]} : {titles[kernel]}")
    figstyle.save(figure, path)


def plot_small(curves, path):
    figure, axes = figstyle.subplots(2, 2, height=3.7)
    letters = {(0, 0): "a", (0, 1): "b", (1, 0): "c", (1, 1): "d"}  # ordre de lecture
    for column, compiler in enumerate(COMPILERS):
        duration, residual = axes[0][column], axes[1][column]
        for variant in VARIANTS:
            build = f"{compiler}-{variant}"
            curve = curves[build]
            color, marker = build_color(build), build_marker(build)
            duration.plot(curve["sizes"], curve["median"], color=color, marker=marker, markersize=2.4,
                          label=VARIANT_LABELS[variant])
            residual.fill_between(curve["sizes"], curve["q25"], curve["q75"], color=color, alpha=0.18, linewidth=0)
            residual.plot(curve["sizes"], curve["residual"], color=color, marker=marker, markersize=2.4,
                          label=VARIANT_LABELS[variant])
        for axis in (duration, residual):
            axis.set_xscale("log", base=2)
            figstyle.fixed_ticks(axis, "x", [1, 4, 16, 64, 256, 1024])
            axis.set_xlabel("Taille n (éléments)")
            axis.axvspan(FIT_MIN_N, 1100, color="#F2F2F2", linewidth=0, zorder=0,
                         label="Zone d'ajustement" if axis is residual else None)
        duration.set_yscale("log")
        figstyle.log_axis(duration, "y")
        duration.set_ylabel("Durée d'un appel (ns)")
        duration.legend(title=COMPILER_LABELS[compiler], title_fontsize=6.5)
        figstyle.panel_title(duration, letters[(0, column)], f"{COMPILER_LABELS[compiler]} : durée d'un appel à sum_one")
        residual.axhline(0, **figstyle.reference_style())
        figstyle.french_ticks(residual, "y")
        residual.set_ylabel("Écart à la droite a + b n (ns)")
        residual.legend()
        figstyle.panel_title(residual, letters[(1, column)], f"{COMPILER_LABELS[compiler]} : écart au modèle linéaire")
    # Même échelle pour les deux panneaux d'écart.
    limits = [axes[1][c].get_ylim() for c in range(2)]
    for c in range(2):
        axes[1][c].set_ylim(min(l[0] for l in limits), max(l[1] for l in limits))
    figstyle.save(figure, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--assembly", type=Path, required=True)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--figures", type=Path)
    args = parser.parse_args()

    groups = by_build(load(args.directory))
    dependency_rows, costs, ratios = dependency_analysis(groups)
    branch_rows, curves, penalty_rows = branch_analysis(groups)
    small_rows, small_curves = small_analysis(groups)
    rusage = [{"build": b, "processes": len(groups[b]),
               "max_involuntary_switches": max(int(p["meta"]["involuntary_switches"]) for p in groups[b]),
               "max_minor_faults": max(int(p["meta"]["minor_faults"]) for p in groups[b])} for b in BUILDS]

    prefix = str(args.reports)
    write_csv(Path(f"{prefix}-dependencies.csv"), dependency_rows)
    write_csv(Path(f"{prefix}-branches.csv"), branch_rows)
    write_csv(Path(f"{prefix}-branch-summary.csv"), penalty_rows)
    write_csv(Path(f"{prefix}-small.csv"), small_rows)
    write_csv(Path(f"{prefix}-rusage.csv"), rusage)
    if args.figures is not None:
        figstyle.use("times")
        plot_dependencies(costs, ratios, Path(f"{args.figures}-dependencies.pdf"))
        plot_branches(curves, Path(f"{args.figures}-branches.pdf"))
        plot_small(small_curves, Path(f"{args.figures}-small.pdf"))
    print(f"processus={sum(len(g) for g in groups.values())}")


if __name__ == "__main__":
    main()
