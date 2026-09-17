#!/usr/bin/env sh
# Exécute le plan : un processus indépendant, épinglé, par ligne de plan.csv.
set -eu

mode=${1:?usage: run.sh check|quick|campaign}
directory="data/$mode"

# Les données brutes d'une campagne ne sont jamais écrasées par accident.
if [ "$mode" = campaign ] && [ -e "$directory/plan.csv" ] && [ "${FORCE:-0}" != 1 ]; then
    printf '%s existe déjà ; relancer avec FORCE=1 pour le remplacer\n' "$directory" >&2
    exit 1
fi
rm -rf "$directory"
python3 prepare.py "$mode" "$directory"

tail -n +2 "$directory/plan.csv" |
while IFS=, read -r run_id binary compiler level cpu seed rounds warmup_rounds min_log2 max_log2 step_log2 target_log2; do
    base=$(printf '%s/run-%03d' "$directory" "$run_id")
    taskset -c "$cpu" "./$binary" --run-id "$run_id" --seed "$seed" --rounds "$rounds" \
        --warmup-rounds "$warmup_rounds" --min-log2 "$min_log2" --max-log2 "$max_log2" \
        --step-log2 "$step_log2" --target-log2 "$target_log2" \
        --output "$base.csv" --meta "$base-meta.csv"
done
