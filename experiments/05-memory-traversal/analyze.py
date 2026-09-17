#!/usr/bin/env python3
"""Résumés et figures du projet C1.

Règles fixées avant la campagne (README, sections 4.2 et 7) : unité statistique
le processus ; médiane par processus sur les tours hors échauffement ; médiane et
bootstrap percentile à 95 % entre processus ; pentes locales centrées sur une
octave, transition = suite de pentes > 0,2 ; contrôle d'attribution
G = coût(16 Mio) / coût(1 Mio) et coût(256 Mio) / coût(16 Mio) pour `random`.
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
BOOTSTRAP_SEED = 20260918
SLOPE_THRESHOLD = 0.2
MIB = 1 << 20
CORES = ("P", "E", "LP-E")
CORE_LABELS = {"P": "Cœur P (CPU 11)", "E": "Cœur E (CPU 19)", "LP-E": "Cœur LP-E (CPU 21)"}
PATTERNS = ("stride_1", "stride_17", "stride_4097", "random")
PATTERN_LABELS = {"stride_1": "Séquentiel", "stride_17": "Pas de 17 éléments",
                  "stride_4097": "Pas de 4 097 éléments", "random": "Aléatoire"}
BYTES_PER_ACCESS = {"pair_same_line": 16, "pair_split_line": 16}


def fmt(value, digits=4):
    return f"{value:.{digits}f}" if np.isfinite(value) else ""


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


def size_label(size):
    for unit, scale in (("Gio", 1 << 30), ("Mio", MIB), ("Kio", 1 << 10)):
        if size >= scale:
            return f"{figstyle.french_number(size / scale, 0 if size % scale == 0 else 1)} {unit}"
    return f"{size} o"


# ---------------------------------------------------------------- lecture

def load(directory):
    """Par processus : coût médian par accès (ns) et durée médiane d'un échantillon."""
    processes = []
    for planned in read_csv(directory / "plan.csv"):
        run_id = int(planned["run_id"])
        cost, elapsed = defaultdict(list), defaultdict(list)
        for row in read_csv(directory / f"run-{run_id:03d}.csv"):
            if row["phase"] != "measure":
                continue
            key = (row["label"], int(row["bytes"]))
            cost[key].append(int(row["elapsed_ns"]) / int(row["accesses"]))
            elapsed[key].append(int(row["elapsed_ns"]))
        processes.append({"core": planned["core"],
                          "cost": {k: float(np.median(v)) for k, v in cost.items()},
                          "elapsed": {k: float(np.median(v)) for k, v in elapsed.items()},
                          "meta": read_csv(directory / f"run-{run_id:03d}-meta.csv")[0]})
    topology = {row["core_type"]: row for row in read_csv(directory / "topology.csv")}
    return processes, topology


# ---------------------------------------------------------------- analyses

def curves(groups, sizes, labels):
    result, rows = {}, []
    for core, selected in groups.items():
        for label in labels:
            medians, lows, highs, q25s, q75s = [], [], [], [], []
            for size in sizes:
                values = [p["cost"][(label, size)] for p in selected]
                center, low, high = bootstrap_median(values)
                q25, q75 = np.quantile(values, [0.25, 0.75])
                medians.append(center)
                lows.append(low)
                highs.append(high)
                q25s.append(q25)
                q75s.append(q75)
                width = BYTES_PER_ACCESS.get(label, 8)
                rows.append({"core": core, "label": label, "bytes": size, "processes": len(values),
                             "median_ns_per_access": fmt(center, 4), "ci95_low": fmt(low, 4),
                             "ci95_high": fmt(high, 4), "q25": fmt(q25, 4), "q75": fmt(q75, 4),
                             "median_gib_per_s": fmt(width / center * 1e9 / (1 << 30), 3)})
            result[(core, label)] = {"median": np.array(medians), "low": np.array(lows),
                                     "high": np.array(highs), "q25": np.array(q25s), "q75": np.array(q75s)}
    return result, rows


def local_slopes(sizes, median):
    """Pente centrée sur une octave : entre les tailles i-1 et i+1 (demi-octaves)."""
    x = np.log2(np.asarray(sizes, dtype=float))
    y = np.log2(median)
    slopes = np.full(len(sizes), np.nan)
    slopes[1:-1] = (y[2:] - y[:-2]) / (x[2:] - x[:-2])
    return slopes


def transitions(sizes, slopes):
    found, current = [], []
    for size, slope in zip(sizes, slopes):
        if np.isfinite(slope) and slope > SLOPE_THRESHOLD:
            current.append((size, slope))
        elif current:
            found.append(current)
            current = []
    if current:
        found.append(current)
    return [{"from_bytes": run[0][0], "to_bytes": run[-1][0],
             "peak_bytes": max(run, key=lambda item: item[1])[0],
             "peak_slope": max(item[1] for item in run)} for run in found]


def attribution(result, sizes, groups):
    index = {size: i for i, size in enumerate(sizes)}
    rows = []
    for core in groups:
        median = result[(core, "random")]["median"]
        g = median[index[16 * MIB]] / median[index[1 * MIB]]
        beyond = median[index[256 * MIB]] / median[index[16 * MIB]]
        per_process_g = [p["cost"][("random", 16 * MIB)] / p["cost"][("random", 1 * MIB)] for p in groups[core]]
        center, low, high = bootstrap_median(per_process_g)
        rows.append({"core": core, "G_16MiB_over_1MiB": fmt(g, 3), "G_per_process_median": fmt(center, 3),
                     "G_ci95_low": fmt(low, 3), "G_ci95_high": fmt(high, 3),
                     "cost_256MiB_over_16MiB": fmt(beyond, 3)})
    return rows


def ratio_rows(groups, sizes):
    rows, values = [], {}
    for core, selected in groups.items():
        aa = [float(np.median([p["cost"][("stride_1_bis", s)] / p["cost"][("stride_1", s)] for s in sizes]))
              for p in selected]
        double = [float(np.median([p["elapsed"][("stride_1_double", s)] / p["elapsed"][("stride_1", s)]
                                   for s in sizes])) for p in selected]
        row = {"core": core, "processes": len(selected)}
        for name, data in (("aa", aa), ("double", double)):
            center, low, high = bootstrap_median(data)
            row.update({f"{name}_median": fmt(center), f"{name}_ci95_low": fmt(low),
                        f"{name}_ci95_high": fmt(high), f"{name}_min": fmt(min(data)),
                        f"{name}_max": fmt(max(data))})
        row["max_minor_faults"] = max(int(p["meta"]["minor_faults"]) for p in selected)
        row["max_involuntary_switches"] = max(int(p["meta"]["involuntary_switches"]) for p in selected)
        rows.append(row)
        split = np.array([[p["cost"][("pair_split_line", s)] / p["cost"][("pair_same_line", s)] for s in sizes]
                          for p in selected])
        values[core] = {"median": np.median(split, axis=0), "q25": np.quantile(split, 0.25, axis=0),
                        "q75": np.quantile(split, 0.75, axis=0)}
    return rows, values


# ---------------------------------------------------------------- figures

def readable_log_axis(axis, *groups):
    """Graduations 1-2-5 (et 3 sur moins d'une décennie), au format français."""
    data = np.concatenate([np.asarray(g, dtype=float).ravel() for g in groups])
    data = data[np.isfinite(data) & (data > 0)]
    low, high = data.min() / 1.25, data.max() * 1.25
    multipliers = (1, 2, 3, 5) if high / low < 10 else (1, 2, 5)
    ticks = [m * 10.0 ** e for e in range(-3, 6) for m in multipliers if low <= m * 10.0 ** e <= high]
    if len(ticks) > 8:
        ticks = [t for t in ticks if np.isclose(t / 10 ** np.floor(np.log10(t)), 1)]
    axis.set_yscale("log")
    axis.set_ylim(low, high)
    figstyle.fixed_ticks(axis, "y", ticks)


def size_axis(axis, sizes):
    axis.set_xscale("log", base=2)
    ticks = [s for s in sizes if (s & (s - 1)) == 0 and int(np.log2(s)) % 4 == 0]
    axis.set_xticks(ticks, [size_label(s) for s in ticks])
    axis.xaxis.set_minor_locator(__import__("matplotlib.ticker", fromlist=["NullLocator"]).NullLocator())
    axis.set_xlabel("Taille des données")


def cache_marks(axis, topology_row, which=("l1_kib", "l2_kib", "l3_kib"), names=None):
    names = names or {"l1_kib": "L1d", "l2_kib": "L2", "l3_kib": "L3"}
    for key in which:
        if topology_row.get(key):
            size = int(topology_row[key]) * 1024
            axis.axvline(size, **figstyle.reference_style(linewidth=0.7))
            axis.text(size, 0.985, f" {names[key]}", transform=axis.get_xaxis_transform(),
                      ha="left", va="top", fontsize=6, color=figstyle.MUTED)


def plot_patterns(result, sizes, topology, path):
    figure, (cost, band) = figstyle.subplots(1, 2, height=2.4)
    x = np.asarray(sizes, dtype=float)
    for i, label in enumerate(PATTERNS):
        curve = result[("P", label)]
        style = {"color": figstyle.PALETTE[i], "marker": figstyle.MARKERS[i], "markersize": 2.4}
        cost.fill_between(x, curve["q25"], curve["q75"], color=figstyle.PALETTE[i], alpha=0.18, linewidth=0)
        cost.plot(x, curve["median"], label=PATTERN_LABELS[label], **style)
        band.plot(x, 8 / curve["median"] * 1e9 / (1 << 30), label=PATTERN_LABELS[label], **style)
    for axis in (cost, band):
        size_axis(axis, sizes)
        cache_marks(axis, topology["P"])
    readable_log_axis(cost, *[result[("P", l)]["q25"] for l in PATTERNS],
                      *[result[("P", l)]["q75"] for l in PATTERNS])
    readable_log_axis(band, *[8 / result[("P", l)]["median"] * 1e9 / (1 << 30) for l in PATTERNS])
    cost.set_ylabel("Coût par accès (ns)")
    band.set_ylabel("Débit de lecture (Gio/s)")
    cost.legend()
    figstyle.panel_title(cost, "a", "Coût par accès, cœur P")
    figstyle.panel_title(band, "b", "Débit de lecture, cœur P")
    figstyle.save(figure, path)


def plot_cores(result, sizes, split, topology, path):
    figure, ((random_cost, slope), (band, lines)) = figstyle.subplots(2, 2, height=3.9)
    x = np.asarray(sizes, dtype=float)
    for i, core in enumerate(CORES):
        if (core, "random") not in result:
            continue
        color, marker = figstyle.PALETTE[i], figstyle.MARKERS[i]
        curve = result[(core, "random")]
        random_cost.fill_between(x, curve["q25"], curve["q75"], color=color, alpha=0.18, linewidth=0)
        random_cost.plot(x, curve["median"], color=color, marker=marker, markersize=2.4, label=CORE_LABELS[core])
        slope.plot(x, local_slopes(sizes, curve["median"]), color=color, marker=marker, markersize=2.4,
                   label=CORE_LABELS[core])
        seq = result[(core, "stride_1")]
        band.plot(x, 8 / seq["median"] * 1e9 / (1 << 30), color=color, marker=marker, markersize=2.4,
                  label=CORE_LABELS[core])
        lines.fill_between(x, split[core]["q25"], split[core]["q75"], color=color, alpha=0.18, linewidth=0)
        lines.plot(x, split[core]["median"], color=color, marker=marker, markersize=2.4, label=CORE_LABELS[core])
    for axis in (random_cost, slope, band, lines):
        size_axis(axis, sizes)
    # Repères : L2 (identique pour les trois cœurs) et L3 (cœurs P et E seulement).
    for axis in (random_cost, slope):
        cache_marks(axis, topology["P"], which=("l2_kib", "l3_kib"),
                    names={"l2_kib": "L2", "l3_kib": "L3 (P, E)"})
    present = [c for c in CORES if (c, "random") in result]
    readable_log_axis(random_cost, *[result[(c, "random")]["q25"] for c in present],
                      *[result[(c, "random")]["q75"] for c in present])
    random_cost.set_ylabel("Coût par accès aléatoire (ns)")
    random_cost.legend()
    figstyle.panel_title(random_cost, "a", "Accès aléatoires selon le cœur")
    slope.axhline(SLOPE_THRESHOLD, **figstyle.reference_style())
    figstyle.french_ticks(slope, "y")
    slope.set_ylabel(r"Pente locale $\Delta \log$ coût / $\Delta \log$ taille")
    slope.legend()
    figstyle.panel_title(slope, "b", "Pente locale des accès aléatoires")
    readable_log_axis(band, *[8 / result[(c, "stride_1")]["median"] * 1e9 / (1 << 30) for c in present])
    band.set_ylabel("Débit séquentiel (Gio/s)")
    band.legend()
    figstyle.panel_title(band, "c", "Débit séquentiel selon le cœur")
    lines.axhline(1, **figstyle.reference_style())
    figstyle.french_ticks(lines, "y")
    lines.set_ylabel("Deux lignes / une ligne")
    lines.legend()
    figstyle.panel_title(lines, "d", "Paire à cheval sur deux lignes de cache")
    figstyle.save(figure, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--figures", type=Path)
    args = parser.parse_args()

    processes, topology = load(args.directory)
    groups = defaultdict(list)
    for process in processes:
        groups[process["core"]].append(process)
    groups = {core: groups[core] for core in CORES if core in groups}
    sizes = sorted({size for (_, size) in processes[0]["cost"]})
    labels = sorted({label for (label, _) in processes[0]["cost"]})

    result, cost_rows = curves(groups, sizes, labels)
    control_rows, split = ratio_rows(groups, sizes)
    transition_rows = []
    for core in groups:
        slopes = local_slopes(sizes, result[(core, "random")]["median"])
        for item in transitions(sizes, slopes):
            transition_rows.append({"core": core, "from": size_label(item["from_bytes"]),
                                    "to": size_label(item["to_bytes"]), "peak": size_label(item["peak_bytes"]),
                                    "peak_slope": fmt(item["peak_slope"], 3)})

    prefix = str(args.reports)
    write_csv(Path(f"{prefix}-costs.csv"), cost_rows)
    write_csv(Path(f"{prefix}-controls.csv"), control_rows)
    if transition_rows:
        write_csv(Path(f"{prefix}-transitions.csv"), transition_rows)
    if 256 * MIB in sizes:
        write_csv(Path(f"{prefix}-attribution.csv"), attribution(result, sizes, groups))
    if args.figures is not None:
        figstyle.use("times")
        plot_patterns(result, sizes, topology, Path(f"{args.figures}-patterns.pdf"))
        plot_cores(result, sizes, split, topology, Path(f"{args.figures}-cores.pdf"))
    print(f"processus={len(processes)} tailles={len(sizes)}")


if __name__ == "__main__":
    main()
