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
while IFS=, read -r run_id binary build cpu seed rounds warmup_rounds calls_shift; do
    base=$(printf '%s/run-%03d' "$directory" "$run_id")
    taskset -c "$cpu" "./$binary" --run-id "$run_id" --seed "$seed" --rounds "$rounds" \
        --warmup-rounds "$warmup_rounds" --calls-shift "$calls_shift" \
        --output "$base.csv" --meta "$base-meta.csv"
done
