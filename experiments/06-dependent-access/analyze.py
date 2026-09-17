#!/usr/bin/env python3
"""Résumés et figures du projet C2.

Règles fixées avant la campagne (README, section 7) : unité statistique le
processus ; médiane par processus sur les tours hors échauffement ; médiane et
bootstrap percentile à 95 % entre processus ; rapports entre accès calculés par
processus ; rapports entre tailles de page calculés sur des groupes indépendants ;
G = coût(16 Mio) / coût(1 Mio) ; échantillon de défauts « pages géantes obtenues »
si défauts ≤ 1,1 × taille / 2 Mio.
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
from matplotlib.ticker import NullLocator  # noqa: E402

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260919
MIB = 1 << 20
HUGE = 2 * MIB
CORES = ("P", "LP-E")
PAGES = ("4k", "2m")
PAGE_LABELS = {"4k": "pages de 4 Kio", "2m": "pages de 2 Mio"}
PAGE_STYLE = {"4k": "-", "2m": "--"}
CORE_LABELS = {"P": "Cœur P", "LP-E": "Cœur LP-E"}
CORE_COLOR = {"P": figstyle.PALETTE[0], "LP-E": figstyle.PALETTE[2]}   # mêmes couleurs qu'en A2 et C1
CORE_MARKER = {"P": "o", "LP-E": "^"}
ACCESS = ("chase_random", "independent_random", "chase_sequential")
ACCESS_LABELS = {"chase_random": "Dépendants dispersés", "independent_random": "Indépendants dispersés",
                 "chase_sequential": "Dépendants contigus"}


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


def bootstrap_median(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(0, values.size, size=(BOOTSTRAP_SAMPLES, values.size))
    low, high = np.percentile(np.median(values[indices], axis=1), [2.5, 97.5])
    return float(np.median(values)), float(low), float(high)


def bootstrap_ratio(top, bottom):
    top, bottom = np.asarray(top, float), np.asarray(bottom, float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    a = np.median(top[rng.integers(0, top.size, (BOOTSTRAP_SAMPLES, top.size))], axis=1)
    b = np.median(bottom[rng.integers(0, bottom.size, (BOOTSTRAP_SAMPLES, bottom.size))], axis=1)
    low, high = np.percentile(a / b, [2.5, 97.5])
    return float(np.median(top) / np.median(bottom)), float(low), float(high)


def size_label(size):
    for unit, scale in (("Gio", 1 << 30), ("Mio", MIB), ("Kio", 1 << 10)):
        if size >= scale:
            return f"{figstyle.french_number(size / scale)} {unit}"
    return f"{size} o"


# ---------------------------------------------------------------- lecture

def load(directory):
    processes = []
    for planned in read_csv(directory / "plan.csv"):
        run_id = int(planned["run_id"])
        cost, faults = defaultdict(list), defaultdict(list)
        for row in read_csv(directory / f"run-{run_id:03d}.csv"):
            if row["phase"] != "measure":
                continue
            size = int(row["bytes"])
            if row["label"] == "page_fault_touch":
                pages = size // 4096
                huge = int(row["faults"]) <= 1.1 * size / HUGE
                faults[(size, "huge" if (planned["pages"] == "2m" and huge) else
                        "refused" if planned["pages"] == "2m" else "base")].append({
                    "first_per_page": int(row["elapsed_ns"]) / pages,
                    "second_per_page": int(row["second_elapsed_ns"]) / pages,
                    "faults": int(row["faults"])})
            else:
                cost[(row["label"], size)].append(int(row["elapsed_ns"]) / int(row["accesses"]))
        processes.append({"core": planned["core"], "pages": planned["pages"],
                          "cost": {k: float(np.median(v)) for k, v in cost.items()},
                          "faults": faults,
                          "meta": read_csv(directory / f"run-{run_id:03d}-meta.csv")[0]})
    return processes


# ---------------------------------------------------------------- analyses

def cost_curves(groups, sizes, labels):
    result, rows = {}, []
    for (core, pages), selected in groups.items():
        for label in labels:
            med, q25, q75 = [], [], []
            for size in sizes:
                values = [p["cost"][(label, size)] for p in selected]
                center, low, high = bootstrap_median(values)
                a, b = np.quantile(values, [0.25, 0.75])
                med.append(center)
                q25.append(a)
                q75.append(b)
                rows.append({"core": core, "pages": pages, "label": label, "bytes": size,
                             "processes": len(values), "median_ns_per_access": fmt(center, 3),
                             "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3)})
            result[(core, pages, label)] = {"median": np.array(med), "q25": np.array(q25), "q75": np.array(q75)}
    return result, rows


def overlap_rows(groups, sizes):
    rows, curves = [], {}
    for (core, pages), selected in groups.items():
        med = []
        for size in sizes:
            ratio = [p["cost"][("chase_random", size)] / p["cost"][("independent_random", size)] for p in selected]
            seq = [p["cost"][("chase_sequential", size)] / p["cost"][("chase_random", size)] for p in selected]
            center, low, high = bootstrap_median(ratio)
            seq_center, seq_low, seq_high = bootstrap_median(seq)
            med.append((center, low, high))
            rows.append({"core": core, "pages": pages, "bytes": size,
                         "chase_over_independent": fmt(center, 3), "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3),
                         "sequential_over_chase": fmt(seq_center, 4), "seq_ci95_low": fmt(seq_low, 4),
                         "seq_ci95_high": fmt(seq_high, 4)})
        curves[(core, pages)] = np.array(med)
    return rows, curves


def page_rows(groups, sizes):
    rows, curves = [], {}
    for core in CORES:
        if (core, "4k") not in groups or (core, "2m") not in groups:
            continue
        for label in ACCESS:
            med = []
            for size in sizes:
                ratio = bootstrap_ratio([p["cost"][(label, size)] for p in groups[(core, "4k")]],
                                        [p["cost"][(label, size)] for p in groups[(core, "2m")]])
                med.append(ratio)
                rows.append({"core": core, "label": label, "bytes": size, "cost_4k_over_2m": fmt(ratio[0], 3),
                             "ci95_low": fmt(ratio[1], 3), "ci95_high": fmt(ratio[2], 3)})
            curves[(core, label)] = np.array(med)
    return rows, curves


def attribution_rows(groups):
    rows, values = [], {}
    for (core, pages), selected in groups.items():
        for label in ("independent_random", "chase_random"):
            g = [p["cost"][(label, 16 * MIB)] / p["cost"][(label, MIB)] for p in selected]
            center, low, high = bootstrap_median(g)
            values[(core, pages, label)] = (g, center, low, high)
            rows.append({"core": core, "pages": pages, "label": label, "G_16MiB_over_1MiB": fmt(center, 3),
                         "ci95_low": fmt(low, 3), "ci95_high": fmt(high, 3)})
    tests = []
    for label in ("independent_random", "chase_random"):
        if all((c, "2m", label) in values for c in CORES):
            ratio = values[("LP-E", "2m", label)][1] / values[("P", "2m", label)][1]
            tests.append({"test": f"G(LP-E, 2 Mio) / G(P, 2 Mio), {label}", "value": fmt(ratio, 3),
                          "threshold": ">= 2", "passed": int(ratio >= 2)})
        if all(("P", p, label) in values for p in PAGES):
            ratio = values[("P", "2m", label)][1] / values[("P", "4k", label)][1]
            tests.append({"test": f"G(P, 2 Mio) / G(P, 4 Kio), {label}", "value": fmt(ratio, 3),
                          "threshold": "<= 0.6", "passed": int(ratio <= 0.6)})
    return rows, tests, values


def fault_rows(groups):
    rows, values = [], {}
    for (core, pages), selected in groups.items():
        keys = sorted({key for p in selected for key in p["faults"]})
        for size, kind in keys:
            per_process = [p["faults"][(size, kind)] for p in selected if p["faults"].get((size, kind))]
            first = [np.median([s["first_per_page"] for s in samples]) for samples in per_process]
            second = [np.median([s["second_per_page"] / s["first_per_page"] for s in samples]) for samples in per_process]
            count = [np.median([s["faults"] for s in samples]) for samples in per_process]
            total = sum(len(p["faults"].get((size, k), [])) for p in selected for k in ("huge", "refused", "base"))
            samples = sum(len(s) for s in per_process)
            center, low, high = bootstrap_median(first)
            per_mib = [f * 256 / 1000 for f in first]   # ns par page de 4 Kio -> µs par Mio
            values[(core, pages, size, kind)] = per_mib
            rows.append({"core": core, "pages": pages, "bytes": size, "class": kind,
                         "processes": len(per_process), "samples": samples,
                         "share_of_samples": fmt(samples / total, 3),
                         "first_touch_ns_per_4k_page": fmt(center, 1), "ci95_low": fmt(low, 1),
                         "ci95_high": fmt(high, 1), "first_touch_us_per_mib": fmt(center * 256 / 1000, 1),
                         "second_over_first": fmt(float(np.median(second)), 4),
                         "median_faults": fmt(float(np.median(count)), 0)})
    return rows, values


def control_rows(groups, sizes):
    rows = []
    for (core, pages), selected in groups.items():
        aa = [float(np.median([p["cost"][("independent_random_bis", s)] / p["cost"][("independent_random", s)]
                               for s in sizes])) for p in selected]
        double = [float(np.median([2 * p["cost"][("chase_random_double", s)] / p["cost"][("chase_random", s)]
                                   for s in sizes])) for p in selected]
        row = {"core": core, "pages": pages, "processes": len(selected)}
        for name, data in (("aa", aa), ("double_duration", double)):
            center, low, high = bootstrap_median(data)
            row.update({f"{name}_median": fmt(center), f"{name}_ci95_low": fmt(low), f"{name}_ci95_high": fmt(high),
                        f"{name}_min": fmt(min(data)), f"{name}_max": fmt(max(data))})
        shares = [float(p["meta"]["huge_share"]) for p in selected]
        row.update({"huge_share_min": fmt(min(shares), 3), "huge_share_max": fmt(max(shares), 3),
                    "max_involuntary_switches": max(int(p["meta"]["involuntary_switches"]) for p in selected)})
        rows.append(row)
    return rows


# ---------------------------------------------------------------- figures

def size_axis(axis, sizes):
    axis.set_xscale("log", base=2)
    ticks = [s for s in sizes if int(np.log2(s)) % 4 == 0]
    axis.set_xticks(ticks, [size_label(s) for s in ticks])
    axis.xaxis.set_minor_locator(NullLocator())
    axis.set_xlabel("Taille des données")


def readable_log_axis(axis, *groups):
    data = np.concatenate([np.asarray(g, dtype=float).ravel() for g in groups])
    data = data[np.isfinite(data) & (data > 0)]
    low, high = data.min() / 1.3, data.max() * 1.3
    multipliers = (1, 2, 3, 5) if high / low < 10 else (1, 2, 5)
    ticks = [m * 10.0 ** e for e in range(-3, 8) for m in multipliers if low <= m * 10.0 ** e <= high]
    if len(ticks) > 8:
        ticks = [t for t in ticks if np.isclose(t / 10 ** np.floor(np.log10(t)), 1)]
    axis.set_yscale("log")
    axis.set_ylim(low, high)
    figstyle.fixed_ticks(axis, "y", ticks)


def plot_latency(curves, sizes, path):
    figure, axes = figstyle.subplots(1, 2, height=2.5)
    x = np.asarray(sizes, dtype=float)
    everything = [c[k] for c in curves.values() for k in ("q25", "q75")]
    for axis, core, letter in zip(axes, CORES, "ab"):
        for i, label in enumerate(ACCESS):
            for pages in PAGES:
                curve = curves.get((core, pages, label))
                if curve is None:
                    continue
                color = figstyle.PALETTE[(0, 1, 3)[i]]
                axis.fill_between(x, curve["q25"], curve["q75"], color=color, alpha=0.15, linewidth=0)
                axis.plot(x, curve["median"], color=color, linestyle=PAGE_STYLE[pages],
                          marker=figstyle.MARKERS[i], markersize=2.4)
        size_axis(axis, sizes)
        readable_log_axis(axis, *everything)
        axis.set_ylabel("Coût par accès (ns)")
        handles = [Line2D([], [], color=figstyle.PALETTE[(0, 1, 3)[i]], marker=figstyle.MARKERS[i],
                          markersize=2.4, label=ACCESS_LABELS[label]) for i, label in enumerate(ACCESS)]
        handles += [Line2D([], [], color=figstyle.INK, linestyle=PAGE_STYLE[p], label=PAGE_LABELS[p]) for p in PAGES]
        axis.legend(handles=handles if axis is axes[0] else handles[3:])
        figstyle.panel_title(axis, letter, f"{CORE_LABELS[core]} : coût par accès")
    figstyle.save(figure, path)


def plot_overlap_tlb(overlap, page_ratio, attribution, sizes, path):
    figure, ((over, indep), (chase, g_axis)) = figstyle.subplots(2, 2, height=3.9)
    x = np.asarray(sizes, dtype=float)
    for core, pages in [(c, p) for c in CORES for p in PAGES if (c, p) in overlap]:
        med = overlap[(core, pages)]
        over.fill_between(x, med[:, 1], med[:, 2], color=CORE_COLOR[core], alpha=0.15, linewidth=0)
        over.plot(x, med[:, 0], color=CORE_COLOR[core], linestyle=PAGE_STYLE[pages], marker=CORE_MARKER[core],
                  markersize=2.4, label=f"{CORE_LABELS[core]}, {PAGE_LABELS[pages]}")
    over.axhline(1, **figstyle.reference_style())
    size_axis(over, sizes)
    readable_log_axis(over, *[m[:, 1:] for m in overlap.values()], [1])
    over.set_ylabel("Dépendants / indépendants")
    over.legend()
    figstyle.panel_title(over, "a", "Recouvrement des défauts de cache")

    for axis, label, letter, title in ((indep, "independent_random", "b", "Accès indépendants : 4 Kio / 2 Mio"),
                                       (chase, "chase_random", "c", "Accès dépendants : 4 Kio / 2 Mio")):
        for core in CORES:
            med = page_ratio.get((core, label))
            if med is None:
                continue
            axis.fill_between(x, med[:, 1], med[:, 2], color=CORE_COLOR[core], alpha=0.15, linewidth=0)
            axis.plot(x, med[:, 0], color=CORE_COLOR[core], marker=CORE_MARKER[core], markersize=2.4,
                      label=CORE_LABELS[core])
        axis.axhline(1, **figstyle.reference_style())
        size_axis(axis, sizes)
        readable_log_axis(axis, *[page_ratio[(c, label)][:, 1:] for c in CORES if (c, label) in page_ratio], [1])
        axis.set_ylabel("Coût en 4 Kio / coût en 2 Mio")
        axis.legend()
        figstyle.panel_title(axis, letter, title)

    categories = [(c, p) for c in CORES for p in PAGES if (c, p, "independent_random") in attribution]
    for x_pos, (core, pages) in enumerate(categories):
        g, center, low, high = attribution[(core, pages, "independent_random")]
        figstyle.strip(g_axis, x_pos - 0.1, g, width=0.1, seed=x_pos, color=CORE_COLOR[core],
                       marker=CORE_MARKER[core], s=9,
                       label=CORE_LABELS[core] if pages == "4k" else None)
        figstyle.interval(g_axis, x_pos + 0.2, center, low, high, markersize=2.8, capsize=1.6,
                          label="Médiane, IC 95 %" if x_pos == 0 else None)
    g_axis.set_xticks(range(len(categories)), [f"{CORE_LABELS[c]}\n{PAGE_LABELS[p]}" for c, p in categories])
    g_axis.tick_params(axis="x", length=0)
    g_axis.grid(axis="x", visible=False)
    g_axis.set_xlim(-0.6, len(categories) - 0.4)
    everything = np.concatenate([attribution[(c, p, "independent_random")][0] for c, p in categories])
    g_axis.set_ylim(0, everything.max() * 1.45)
    figstyle.french_ticks(g_axis, "y")
    g_axis.set_ylabel("G = coût(16 Mio) / coût(1 Mio)")
    g_axis.legend()
    figstyle.panel_title(g_axis, "d", "Contrôle d'attribution, accès indépendants")
    figstyle.save(figure, path)


def plot_faults(fault_values, path):
    figure, axis = figstyle.subplots(1, 1, width=figstyle.DOUBLE_COLUMN, height=2.3)
    kinds = [("4k", "base", "4 Kio"), ("2m", "huge", "2 Mio, pages\ngéantes obtenues"),
             ("2m", "refused", "2 Mio, refus\npartiel")]
    sizes = sorted({key[2] for key in fault_values})
    categories = [(size, pages, kind, text) for size in sizes for pages, kind, text in kinds
                  if any((c, pages, size, kind) in fault_values for c in CORES)]
    done = set()
    for x_pos, (size, pages, kind, text) in enumerate(categories):
        for offset, core in zip((-0.14, 0.14), CORES):
            values = fault_values.get((core, pages, size, kind))
            if not values:
                continue
            figstyle.strip(axis, x_pos + offset - 0.05, values, width=0.05, seed=x_pos * 7 + len(core),
                           color=CORE_COLOR[core], marker=CORE_MARKER[core], s=9,
                           label=CORE_LABELS[core] if core not in done else None)
            done.add(core)
            center, low, high = bootstrap_median(values)
            figstyle.interval(axis, x_pos + offset + 0.07, center, low, high, markersize=2.6, capsize=1.4,
                              label="Médiane, IC 95 %" if "interval" not in done else None)
            done.add("interval")
    axis.set_xticks(range(len(categories)), [f"{size_label(s)}\n{t}" for s, _, _, t in categories])
    axis.tick_params(axis="x", length=0)
    axis.grid(axis="x", visible=False)
    axis.set_xlim(-0.6, len(categories) - 0.4)
    readable_log_axis(axis, *[v for v in fault_values.values()])
    axis.set_ylabel("Premier accès (µs par Mio)")
    axis.legend()
    axis.set_title("Coût du premier accès à une zone neuve")   # panneau unique : pas de lettre
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
        groups[(process["core"], process["pages"])].append(process)
    groups = {key: groups[key] for key in sorted(groups)}
    sizes = sorted({size for p in processes for (_, size) in p["cost"]})
    labels = sorted({label for p in processes for (label, _) in p["cost"]})

    curves, cost_table = cost_curves(groups, sizes, labels)
    overlap_table, overlap = overlap_rows(groups, sizes)
    page_table, page_ratio = page_rows(groups, sizes)
    fault_table, fault_values = fault_rows(groups)
    prefix = str(args.reports)
    write_csv(Path(f"{prefix}-costs.csv"), cost_table)
    write_csv(Path(f"{prefix}-overlap.csv"), overlap_table)
    if page_table:
        write_csv(Path(f"{prefix}-pages.csv"), page_table)
    write_csv(Path(f"{prefix}-faults.csv"), fault_table)
    write_csv(Path(f"{prefix}-controls.csv"), control_rows(groups, sizes))
    attribution = {}
    if 16 * MIB in sizes and MIB in sizes:
        attribution_table, tests, attribution = attribution_rows(groups)
        write_csv(Path(f"{prefix}-attribution.csv"), attribution_table)
        if tests:
            write_csv(Path(f"{prefix}-attribution-tests.csv"), tests)
    if args.figures is not None:
        figstyle.use("times")
        plot_latency(curves, sizes, Path(f"{args.figures}-latency.pdf"))
        if attribution and page_ratio:
            plot_overlap_tlb(overlap, page_ratio, attribution, sizes, Path(f"{args.figures}-overlap-tlb.pdf"))
        plot_faults(fault_values, Path(f"{args.figures}-faults.pdf"))
    print(f"processus={len(processes)} tailles={len(sizes)}")


if __name__ == "__main__":
    main()
