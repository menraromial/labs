#!/usr/bin/env sh
# Exécute le plan d'une campagne : un processus indépendant par ligne de plan.csv.
set -eu

mode=${1:?usage: run.sh check|quick|campaign|prime}
directory="data/$mode"

# Les données brutes d'une campagne ne sont jamais écrasées par accident.
if { [ "$mode" = campaign ] || [ "$mode" = prime ]; } && [ -e "$directory/plan.csv" ] && [ "${FORCE:-0}" != 1 ]; then
    printf '%s existe déjà ; relancer avec FORCE=1 pour le remplacer\n' "$directory" >&2
    exit 1
fi
rm -rf "$directory"
python3 prepare.py "$mode" "$directory"

tail -n +2 "$directory/plan.csv" |
while IFS=, read -r run_id protocol run_mode affinity cpu seed batch rounds warmup_rounds max_batch warmup_ops prime; do
    base=$(printf '%s/run-%03d' "$directory" "$run_id")
    set -- ./build/microbench --mode "$run_mode" --protocol "$protocol" \
        --affinity "$affinity" --run-id "$run_id" --seed "$seed" \
        --rounds "$rounds" --warmup-rounds "$warmup_rounds" --warmup-ops "$warmup_ops" \
        --prime "${prime:-none}" --output "$base.csv" --meta "$base-meta.csv"
    [ -n "$batch" ] && set -- "$@" --batch "$batch"
    [ -n "$max_batch" ] && set -- "$@" --max-batch "$max_batch"
    if [ -n "$cpu" ]; then
        taskset -c "$cpu" "$@"
    else
        "$@"
    fi
done
