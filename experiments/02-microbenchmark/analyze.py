#!/usr/bin/env python3
"""Résumés et figures du projet A2.

Analyses fixées avant la campagne (README, section 7) : l'unité statistique est
le processus, les tours d'échauffement déclarés sont exclus des estimations mais
conservés et tracés, les intervalles sont des bootstraps percentiles des
processus, l'amortissement est ajusté sur la médiane de tous les processus.

Analyses ajoutées après la première campagne, signalées comme exploratoires :
séparation par type de cœur, temps avant migration vers un cœur P et contrôle
d'amorçage (README, section 3 bis).
"""

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))
import figstyle  # noqa: E402

BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260916
MISLEADING_GAP = 0.05
MIN_SAMPLES_PER_STRATUM = 10
VARIANTS = ("A", "A_bis", "B")
LADDER = ("naive", "batched", "interleaved")
PRIMES = ("none", "clock", "code", "full")
# Ordre fixe : chaque type de cœur garde sa couleur et son marqueur dans toutes les figures.
CORE_TYPES = ("P", "E", "LP-E", "unique")
CORE_LABELS = {"P": "Cœur P", "E": "Cœur E", "LP-E": "Cœur LP-E", "unique": "Cœur"}
AGGREGATE = figstyle.PALETTE[3]


def core_color(core_type):
    return figstyle.PALETTE[min(CORE_TYPES.index(core_type), 2)]


def core_marker(core_type):
    return figstyle.MARKERS[min(CORE_TYPES.index(core_type), 2)]


# ---------------------------------------------------------------- lecture et écriture

def read_csv(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load(directory):
    topology = {int(row["cpu"]): row["core_type"] for row in read_csv(directory / "topology.csv")}
    processes = {}
    for planned in read_csv(directory / "plan.csv"):
        run_id = int(planned["run_id"])
        samples = []
        for row in read_csv(directory / f"run-{run_id:03d}.csv"):
            ops = int(row["ops"])
            before, after = int(row["cpu_before"]), int(row["cpu_after"])
            samples.append({
                "sample": int(row["sample"]),
                "round": int(row["round"]),
                "phase": row["phase"],
                "position": int(row["position"]),
                "variant": row["variant"],
                "ops": ops,
                "elapsed": int(row["elapsed_ns"]),
                "cost": int(row["elapsed_ns"]) / ops,
                # Type de cœur de l'échantillon, s'il n'a pas changé de CPU pendant la mesure.
                "core": topology[before] if topology[before] == topology[after] else None,
            })
        samples.sort(key=lambda s: s["sample"])
        types = Counter(s["core"] for s in samples if s["core"] is not None)
        processes[run_id] = {
            "protocol": planned["protocol"],
            "affinity": planned["affinity"],
            "prime": planned.get("prime") or "none",
            "samples": samples,
            "core_type": types.most_common(1)[0][0],
            "migrations": sum(s["core"] is None for s in samples),
            "meta": read_csv(directory / f"run-{run_id:03d}-meta.csv")[0],
        }
    return processes


# ---------------------------------------------------------------- statistiques

def bootstrap_median(values):
    """Médiane et intervalle bootstrap percentile à 95 %, processus rééchantillonnés."""
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(0, values.size, size=(BOOTSTRAP_SAMPLES, values.size))
    low, high = np.percentile(np.median(values[indices], axis=1), [2.5, 97.5])
    return float(np.median(values)), float(low), float(high)


def relative_iqr(values):
    q25, q50, q75 = np.quantile(np.asarray(values, dtype=float), [0.25, 0.5, 0.75])
    return float((q75 - q25) / q50)


def fit_model(sizes, costs):
    """Ajuste coût(N) = C + H/N en erreur relative : C / y + H / (N y) = 1, linéaire en (C, H)."""
    sizes = np.asarray(sizes, dtype=float)
    costs = np.asarray(costs, dtype=float)
    design = np.column_stack([1 / costs, 1 / (sizes * costs)])
    (c, h), *_ = np.linalg.lstsq(design, np.ones_like(costs), rcond=None)
    return float(h), float(c)


def bootstrap_fit(matrix, sizes):
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    fits = np.array([fit_model(sizes, np.median(matrix[rng.integers(0, len(matrix), len(matrix))], axis=0))
                     for _ in range(2_000)])
    return np.percentile(fits[:, 0], [2.5, 97.5]), np.percentile(fits[:, 1], [2.5, 97.5])


def variant_costs(process):
    """Coût par opération de chaque variante : médiane des échantillons hors échauffement."""
    measured = [s for s in process["samples"] if s["phase"] == "measure"]
    return {variant: float(np.median([s["cost"] for s in measured if s["variant"] == variant]))
            for variant in VARIANTS}


def fmt(value, digits=4):
    return f"{value:.{digits}f}"


def select(processes, protocol, affinity="libre", prime="none"):
    return [p for _, p in sorted(processes.items())
            if p["protocol"] == protocol and p["affinity"] == affinity and p["prime"] == prime]


# ---------------------------------------------------------------- amortissement

def analyze_amortization(processes):
    selected = select(processes, "amortization")
    sizes = sorted({s["ops"] for s in selected[0]["samples"]})

    # Analyse prévue : médiane par processus, tous types de cœurs confondus.
    matrix = np.array([[np.median([s["cost"] for s in p["samples"] if s["ops"] == size])
                        for size in sizes] for p in selected])
    within = np.array([[relative_iqr([s["cost"] for s in p["samples"] if s["ops"] == size])
                        for size in sizes] for p in selected])
    h, c = fit_model(sizes, np.median(matrix, axis=0))
    (h_low, h_high), (c_low, c_high) = bootstrap_fit(matrix, sizes)
    models = [{"stratum": "tous (prévu)", "processes": len(selected), "H_ns": fmt(h, 2),
               "H_low_ns": fmt(h_low, 2), "H_high_ns": fmt(h_high, 2), "C_ns": fmt(c, 3),
               "C_low_ns": fmt(c_low, 3), "C_high_ns": fmt(c_high, 3)}]

    # Analyse exploratoire : échantillons séparés selon le type de cœur où ils ont été pris.
    strata = {}
    for core_type in CORE_TYPES:
        rows, spreads = [], []
        for process in selected:
            by_size = [[s["cost"] for s in process["samples"]
                        if s["ops"] == size and s["core"] == core_type] for size in sizes]
            if all(len(values) >= MIN_SAMPLES_PER_STRATUM for values in by_size):
                rows.append([np.median(values) for values in by_size])
                spreads.append([relative_iqr(values) for values in by_size])
        if len(rows) < 3:
            continue
        rows = np.array(rows)
        h_type, c_type = fit_model(sizes, np.median(rows, axis=0))
        (hl, hh), (cl, ch) = bootstrap_fit(rows, sizes)
        strata[core_type] = {"matrix": rows, "within": np.array(spreads), "h": h_type,
                             "c": c_type, "h_ci": (hl, hh), "c_ci": (cl, ch)}
        models.append({"stratum": core_type, "processes": len(rows), "H_ns": fmt(h_type, 2),
                       "H_low_ns": fmt(hl, 2), "H_high_ns": fmt(hh, 2), "C_ns": fmt(c_type, 3),
                       "C_low_ns": fmt(cl, 3), "C_high_ns": fmt(ch, 3)})

    center = np.median(matrix, axis=0)
    q25, q75 = np.quantile(matrix, [0.25, 0.75], axis=0)
    between_same = np.array([np.median([relative_iqr(stratum["matrix"][:, i])
                                        for stratum in strata.values()])
                             for i in range(len(sizes))]) if strata else np.full(len(sizes), np.nan)
    table = []
    for i, size in enumerate(sizes):
        row = {"batch_size": size, "processes": len(selected),
               "q25_ns_per_op": fmt(q25[i]), "median_ns_per_op": fmt(center[i]),
               "q75_ns_per_op": fmt(q75[i]), "model_ns_per_op": fmt(c + h / size),
               "within_process_relative_iqr": fmt(float(np.median(within[:, i]))),
               "between_process_relative_iqr": fmt(relative_iqr(matrix[:, i])),
               "between_process_same_core_relative_iqr": fmt(between_same[i])}
        for core_type, stratum in strata.items():
            row[f"median_ns_per_op_{core_type}"] = fmt(float(np.median(stratum["matrix"][:, i])))
        table.append(row)
    return {"sizes": sizes, "center": center, "h": h, "c": c, "h_ci": (h_low, h_high),
            "c_ci": (c_low, c_high), "within": np.median(within, axis=0),
            "between": np.array([relative_iqr(matrix[:, i]) for i in range(len(sizes))]),
            "between_same": between_same, "strata": strata, "table": table, "models": models}


# ---------------------------------------------------------------- réparation et contrôles

def ratio_summary(label_fields, groups):
    """groups : {clé: processus}. Renvoie les rapports par processus et les lignes de résumé."""
    result, rows = {}, []
    for key, selected in groups.items():
        ratios = {"A_bis/A": [], "B/A": []}
        types = []
        for process in selected:
            costs = variant_costs(process)
            ratios["A_bis/A"].append(costs["A_bis"] / costs["A"])
            ratios["B/A"].append(costs["B"] / costs["A"])
            types.append(process["core_type"])
        result[key] = {"ratios": ratios, "types": types}
        for comparison, values in ratios.items():
            center, low, high = bootstrap_median(values)
            values = np.asarray(values)
            result[key][comparison] = (center, low, high)
            rows.append({
                **label_fields(key), "comparison": comparison, "processes": values.size,
                "median": fmt(center), "ci95_low": fmt(low), "ci95_high": fmt(high),
                "min": fmt(values.min()), "max": fmt(values.max()),
                "share_below_1": fmt(float(np.mean(values < 1)), 3),
                # Critère de conclusion trompeuse, défini pour le seul contrôle A/A.
                "share_gap_over_5pct_from_1": (fmt(float(np.mean(np.abs(values - 1) > MISLEADING_GAP)), 3)
                                               if comparison == "A_bis/A" else ""),
            })
    return result, rows


def analyze_prime(processes):
    groups = {prime: select(processes, "naive", prime=prime) for prime in PRIMES}
    result, rows = ratio_summary(lambda prime: {"prime": prime}, groups)
    cost_rows = []
    for prime, selected in groups.items():
        row = {"prime": prime, "processes": len(selected)}
        for variant in VARIANTS:
            center, low, high = bootstrap_median([variant_costs(p)[variant] for p in selected])
            row[f"median_ns_{variant}"] = fmt(center, 1)
            row[f"ci95_low_ns_{variant}"] = fmt(low, 1)
            row[f"ci95_high_ns_{variant}"] = fmt(high, 1)
        cost_rows.append(row)
    return result, rows, cost_rows


def analyze_affinity(processes):
    groups = ["libre"] + [t for t in CORE_TYPES
                          if any(p["affinity"] == t for p in processes.values())]
    result, rows = {}, []
    for group in groups:
        selected = select(processes, "interleaved", affinity=group)
        costs = [variant_costs(p)["A"] for p in selected]
        within = [relative_iqr([s["cost"] for s in p["samples"]
                                if s["phase"] == "measure" and s["variant"] == "A"]) for p in selected]
        types = [p["core_type"] for p in selected]
        center, low, high = bootstrap_median(costs)
        result[group] = {"costs": costs, "types": types, "summary": (center, low, high)}
        rows.append({
            "affinity": group, "processes": len(costs), "median_ns_per_op_A": fmt(center),
            "ci95_low": fmt(low), "ci95_high": fmt(high),
            "between_process_relative_iqr": fmt(relative_iqr(costs)),
            "median_within_process_relative_iqr": fmt(float(np.median(within))),
            "median_B_over_A": fmt(float(np.median([variant_costs(p)["B"] / variant_costs(p)["A"]
                                                    for p in selected]))),
            "core_types": " ".join(f"{t}:{n}" for t, n in sorted(Counter(types).items())),
        })
    return result, rows


# ---------------------------------------------------------------- placement et échauffement

def analyze_warmup(processes):
    selected = select(processes, "interleaved")
    warmup_rounds = sum(s["phase"] == "warmup" for s in selected[0]["samples"]) // len(VARIANTS)
    normalized = defaultdict(list)
    not_p = defaultdict(list)
    positions = defaultdict(list)
    for process in selected:
        reference = variant_costs(process)
        by_round, by_position, cores = defaultdict(list), defaultdict(list), defaultdict(list)
        for sample in process["samples"]:
            value = sample["cost"] / reference[sample["variant"]]
            by_round[sample["round"]].append(value)
            cores[sample["round"]].append(sample["core"])
            if sample["phase"] == "measure":
                by_position[sample["position"]].append(value)
        for index, values in by_round.items():
            normalized[index].append(float(np.median(values)))
            not_p[index].append(float(all(core not in ("P", "unique") for core in cores[index])))
        for index, values in by_position.items():
            positions[index].append(float(np.median(values)))

    indices = sorted(normalized)
    rows = [{"round": i, "phase": "warmup" if i < warmup_rounds else "measure",
             "processes": len(normalized[i]),
             "q25_normalized_cost": fmt(np.quantile(normalized[i], 0.25)),
             "median_normalized_cost": fmt(np.median(normalized[i])),
             "q75_normalized_cost": fmt(np.quantile(normalized[i], 0.75)),
             "share_processes_off_P": fmt(float(np.mean(not_p[i])), 3)} for i in indices]
    position_rows = []
    for index in sorted(positions):
        center, low, high = bootstrap_median(positions[index])
        position_rows.append({"position": index + 1, "processes": len(positions[index]),
                              "median_normalized_cost": fmt(center), "ci95_low": fmt(low),
                              "ci95_high": fmt(high)})
    return {"indices": np.array(indices),
            "median": np.array([np.median(normalized[i]) for i in indices]),
            "q25": np.array([np.quantile(normalized[i], 0.25) for i in indices]),
            "q75": np.array([np.quantile(normalized[i], 0.75) for i in indices]),
            "off_p": np.array([np.mean(not_p[i]) for i in indices]),
            "warmup_rounds": warmup_rounds, "rows": rows, "position_rows": position_rows}


def migration_rows(processes):
    """Temps chronométré cumulé avant le premier échantillon pris sur un cœur P."""
    rows = []
    groups = defaultdict(list)
    for process in processes.values():
        if process["affinity"] == "libre":
            groups[(process["protocol"], process["prime"])].append(process)
    for (protocol, prime), selected in sorted(groups.items()):
        delays, never = [], 0
        started_off_p = 0
        for process in selected:
            samples = process["samples"]
            if samples[0]["core"] == "P":
                continue
            started_off_p += 1
            index = next((i for i, s in enumerate(samples) if s["core"] == "P"), None)
            if index is None:
                never += 1
            else:
                delays.append(sum(s["elapsed"] for s in samples[:index]) / 1e6)
        rows.append({
            "protocol": protocol, "prime": prime, "processes": len(selected),
            "first_sample_off_P": started_off_p, "reached_P_later": len(delays),
            "never_on_P": never,
            "median_ms_before_first_P": fmt(float(np.median(delays)), 2) if delays else "",
            "max_ms_before_first_P": fmt(max(delays), 2) if delays else "",
            "migrated_samples": sum(p["migrations"] for p in selected),
            "median_involuntary_switches": fmt(float(np.median(
                [int(p["meta"]["involuntary_switches"]) for p in selected])), 1),
            "max_involuntary_switches": max(int(p["meta"]["involuntary_switches"]) for p in selected),
            "max_minor_faults": max(int(p["meta"]["minor_faults"]) for p in selected),
        })
    return rows


# ---------------------------------------------------------------- figures

def readable_log_ticks(*groups):
    """Graduations 1-2-5 couvrant les données, pour un axe logarithmique de faible étendue."""
    data = np.concatenate([np.asarray(g, dtype=float).ravel() for g in groups])
    data = data[np.isfinite(data) & (data > 0)]
    low, high = data.min() / 1.3, data.max() * 1.3
    return [t for t in (m * 10.0 ** e for e in range(-3, 6) for m in (1, 2, 5)) if low <= t <= high]


def categorical_axis(axis, labels):
    axis.set_xticks(range(len(labels)), labels)
    axis.tick_params(axis="x", length=0)
    axis.grid(axis="x", visible=False)
    axis.set_xlim(-0.55, len(labels) - 0.45)


def strips_by_core(axis, x, values, types, seed, labels_done):
    values, types = np.asarray(values), np.asarray(types)
    for core_type in CORE_TYPES:
        mask = types == core_type
        if not mask.any():
            continue
        label = CORE_LABELS[core_type] if core_type not in labels_done else None
        labels_done.add(core_type)
        figstyle.strip(axis, x - 0.12, values[mask], seed=seed * 10 + CORE_TYPES.index(core_type),
                       color=core_color(core_type), marker=core_marker(core_type), label=label)


def ratio_panel(axis, groups, keys, labels, comparison, expected, show_share):
    labels_done = set()
    for x, key in enumerate(keys):
        values = groups[key]["ratios"][comparison]
        strips_by_core(axis, x, values, groups[key]["types"], x, labels_done)
        center, low, high = groups[key][comparison]
        figstyle.interval(axis, x + 0.24, center, low, high,
                          label="Médiane, IC 95 %" if x == 0 else None)
        if show_share:
            share = np.mean(np.abs(np.asarray(values) - 1) > MISLEADING_GAP)
            axis.text(x, 0.985, f"{figstyle.french_number(100 * share)} % hors ±5 %",
                      transform=axis.get_xaxis_transform(), ha="center", va="top",
                      fontsize=6, color=figstyle.MUTED)
    axis.axhline(expected, **figstyle.reference_style())
    everything = np.concatenate([groups[k]["ratios"][comparison] for k in keys] + [[expected]])
    low, high = everything.min() / 1.08, everything.max() * (1.5 if show_share else 1.1)
    axis.set_yscale("log")
    axis.set_ylim(low, high)
    candidates = [0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10]
    if high / low < 4:
        candidates += [0.8, 1.25, 1.5, 3]
    figstyle.fixed_ticks(axis, "y", sorted(t for t in candidates if low <= t <= high))
    categorical_axis(axis, labels)
    axis.legend()


def plot_amortization(amortization, path):
    figure, (cost, spread) = figstyle.subplots(1, 2, height=2.15)
    sizes = np.asarray(amortization["sizes"], dtype=float)
    ticks = [size for size in amortization["sizes"] if int(np.log2(size)) % 3 == 0]
    dense = np.geomspace(sizes[0], sizes[-1], 200)

    notes = []
    strata = amortization["strata"]
    if not strata:
        # Trop peu d'échantillons par type de cœur (ex. make quick) : courbe regroupée.
        strata = {"tous": {"matrix": np.array([amortization["center"]]), "h": amortization["h"],
                           "c": amortization["c"], "h_ci": amortization["h_ci"],
                           "c_ci": amortization["c_ci"]}}
    for core_type, stratum in strata.items():
        matrix = stratum["matrix"]
        pooled = core_type == "tous"
        color = AGGREGATE if pooled else core_color(core_type)
        low, high = np.quantile(matrix, [0.25, 0.75], axis=0)
        cost.fill_between(sizes, low, high, color=color, alpha=0.18, linewidth=0)
        label = "Médiane, tous cœurs" if pooled else f"{CORE_LABELS[core_type]} ({len(matrix)} processus)"
        cost.plot(sizes, np.median(matrix, axis=0), color=color,
                  marker="o" if pooled else core_marker(core_type), markersize=2.6, label=label)
        (hl, hh), (cl, ch) = stratum["h_ci"], stratum["c_ci"]
        notes.append(rf"{'Tous' if core_type == 'tous' else core_type} : $H$ = {figstyle.french_number(stratum['h'], 1)} "
                     rf"[{figstyle.french_number(hl, 1)} ; {figstyle.french_number(hh, 1)}] ns, "
                     rf"$C$ = {figstyle.french_number(stratum['c'], 2)} "
                     rf"[{figstyle.french_number(cl, 2)} ; {figstyle.french_number(ch, 2)}] ns")
    for index, stratum in enumerate(strata.values()):
        cost.plot(dense, stratum["c"] + stratum["h"] / dense, **figstyle.reference_style(
            label=r"Modèle $C + H/N$" if index == 0 else None))
    cost.text(0.97, 0.95, "\n".join(notes), transform=cost.transAxes, ha="right", va="top",
              fontsize=6, color=figstyle.MUTED, linespacing=1.3)
    cost.set_xscale("log", base=2)
    cost.set_yscale("log")
    figstyle.fixed_ticks(cost, "x", ticks)
    figstyle.fixed_ticks(cost, "y", readable_log_ticks(*[s["matrix"] for s in strata.values()]))
    cost.set(xlabel="Taille du lot N (opérations)", ylabel="Coût apparent (ns/opération)")
    cost.legend()
    figstyle.panel_title(cost, "a", "Amortissement du chronométrage")

    spread.plot(sizes, 100 * amortization["within"], color=AGGREGATE, marker="o", markersize=2.6,
                linestyle="-", label="Entre répétitions d'un processus")
    spread.plot(sizes, 100 * amortization["between"], color=AGGREGATE, marker="s", markersize=2.6,
                linestyle="--", label="Entre processus, tous cœurs")
    if np.isfinite(amortization["between_same"]).all():
        spread.plot(sizes, 100 * amortization["between_same"], color=AGGREGATE, marker="^",
                    markersize=2.8, linestyle="-.", label="Entre processus, même type de cœur")
    spread.set_xscale("log", base=2)
    spread.set_yscale("log")
    figstyle.fixed_ticks(spread, "x", ticks)
    figstyle.fixed_ticks(spread, "y", readable_log_ticks(
        100 * amortization["within"], 100 * amortization["between"],
        100 * amortization["between_same"]))
    spread.set(xlabel="Taille du lot N (opérations)", ylabel="Écart interquartile relatif (%)")
    spread.legend()
    figstyle.panel_title(spread, "b", "Dispersion selon l'échelle d'observation")
    figstyle.save(figure, path)


def plot_repair(ladder, prime, affinity, path):
    figure, ((same, double), (primed, cores)) = figstyle.subplots(2, 2, height=3.75)
    ladder_labels = ["Naïf\n1 opération", "Lot unique\n20 000 opérations",
                     "Lots entrelacés\nordre aléatoire"]

    ratio_panel(same, ladder, LADDER, ladder_labels, "A_bis/A", 1, show_share=True)
    same.set_ylabel(r"Rapport $A_{bis}/A$ par processus")
    figstyle.panel_title(same, "a", "Contrôle A/A : rapport vrai 1")

    ratio_panel(double, ladder, LADDER, ladder_labels, "B/A", 2, show_share=False)
    double.set_ylabel(r"Rapport $B/A$ par processus")
    figstyle.panel_title(double, "b", "Contrôle positif : deux fois plus d'appels")

    if prime:
        ratio_panel(primed, prime, PRIMES,
                    ["Aucun", "Lecture\nd'horloge", "Appel des\nfonctions", "Mesure\njetée"],
                    "A_bis/A", 1, show_share=True)
        primed.set(xlabel="Amorçage non chronométré (protocole naïf)",
                   ylabel=r"Rapport $A_{bis}/A$ par processus")
        figstyle.panel_title(primed, "c", "Contrôle exploratoire : premier passage")
    else:
        primed.set_visible(False)

    labels_done = set()
    groups = list(affinity)
    for x, group in enumerate(groups):
        strips_by_core(cores, x, affinity[group]["costs"], affinity[group]["types"], 100 + x, labels_done)
        center, low, high = affinity[group]["summary"]
        figstyle.interval(cores, x + 0.24, center, low, high,
                          label="Médiane, IC 95 %" if x == 0 else None)
    names = {"libre": "Sans\naffinité", "P": "Épinglé\nCPU P", "E": "Épinglé\nCPU E",
             "LP-E": "Épinglé\nCPU LP-E", "unique": "Épinglé"}
    categorical_axis(cores, [names[g] for g in groups])
    cores.set_ylim(0, max(max(affinity[g]["costs"]) for g in groups) * 1.15)
    figstyle.french_ticks(cores, "y")
    cores.set(xlabel="Lots entrelacés", ylabel="Coût de A (ns/opération)")
    cores.legend()
    figstyle.panel_title(cores, "d", "Contrôle d'affinité")
    figstyle.save(figure, path)


def plot_warmup(warmup, path):
    figure, (drift, placement) = figstyle.subplots(1, 2, height=2.1)
    rounds = warmup["indices"]
    for axis in (drift, placement):
        axis.axvspan(-0.5, warmup["warmup_rounds"] - 0.5, color="#EFEFEF", linewidth=0, zorder=0,
                     label="Échauffement déclaré")
        axis.set_xlim(-0.5, rounds[-1] + 0.5)
        axis.set_xlabel("Tour dans le processus (lots entrelacés, sans affinité)")

    drift.fill_between(rounds, warmup["q25"], warmup["q75"], color=AGGREGATE, alpha=0.2,
                       linewidth=0, label="Écart interquartile")
    drift.plot(rounds, warmup["median"], color=AGGREGATE, label="Médiane des processus")
    drift.axhline(1, **figstyle.reference_style())
    figstyle.french_ticks(drift, "y")
    drift.set_ylabel("Coût / médiane hors échauffement")
    drift.legend()
    figstyle.panel_title(drift, "a", "Ralentissement initial apparent")

    placement.step(rounds, 100 * warmup["off_p"], where="mid", color=core_color("E"),
                   label="Tour entier hors cœur P")
    placement.set_ylim(0, 100)
    placement.set_ylabel("Processus (%)")
    placement.legend()
    figstyle.panel_title(placement, "b", "Placement par l'ordonnanceur")
    figstyle.save(figure, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--prime", type=Path, help="données du contrôle d'amorçage, si présentes")
    parser.add_argument("--reports", type=Path, required=True, help="préfixe, ex. reports/campaign")
    parser.add_argument("--figures", type=Path, help="préfixe, ex. figures/campaign")
    args = parser.parse_args()

    processes = load(args.directory)
    figstyle.use("times")
    amortization = analyze_amortization(processes)
    ladder, ladder_rows = ratio_summary(lambda protocol: {"protocol": protocol},
                                        {protocol: select(processes, protocol) for protocol in LADDER})
    affinity, affinity_rows = analyze_affinity(processes)
    warmup = analyze_warmup(processes)

    prefix = str(args.reports)
    write_csv(Path(f"{prefix}-amortization.csv"), amortization["table"])
    write_csv(Path(f"{prefix}-model.csv"), amortization["models"])
    write_csv(Path(f"{prefix}-ratios.csv"), ladder_rows)
    write_csv(Path(f"{prefix}-affinity.csv"), affinity_rows)
    write_csv(Path(f"{prefix}-warmup.csv"), warmup["rows"])
    write_csv(Path(f"{prefix}-position.csv"), warmup["position_rows"])
    write_csv(Path(f"{prefix}-placement.csv"), migration_rows(processes))

    prime = None
    if args.prime is not None and (args.prime / "plan.csv").exists():
        prime_processes = load(args.prime)
        prime, prime_rows, prime_costs = analyze_prime(prime_processes)
        write_csv(Path(f"{prefix}-prime-ratios.csv"), prime_rows)
        write_csv(Path(f"{prefix}-prime-costs.csv"), prime_costs)
        write_csv(Path(f"{prefix}-prime-placement.csv"), migration_rows(prime_processes))

    if args.figures is not None:
        plot_amortization(amortization, Path(f"{args.figures}-amortization.pdf"))
        plot_repair(ladder, prime, affinity, Path(f"{args.figures}-repair.pdf"))
        plot_warmup(warmup, Path(f"{args.figures}-warmup.pdf"))
    print(f"processus={len(processes)} rapports={prefix}-*.csv")


if __name__ == "__main__":
    main()
