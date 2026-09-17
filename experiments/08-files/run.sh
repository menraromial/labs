#!/usr/bin/env sh
# Exécute le plan : un processus indépendant, épinglé, par ligne de plan.csv.
# Aucun réglage global : seuls nos fichiers sont retirés du cache (posix_fadvise).
set -eu

mode=${1:?usage: run.sh check|quick|campaign}
directory="data/$mode"
scratch="$(pwd)/build/scratch"
tmpfs="/dev/shm/labs-d2-$$"

# Les données brutes d'une campagne ne sont jamais écrasées par accident.
if [ "$mode" = campaign ] && [ -e "$directory/plan.csv" ] && [ "${FORCE:-0}" != 1 ]; then
    printf '%s existe déjà ; relancer avec FORCE=1 pour le remplacer\n' "$directory" >&2
    exit 1
fi
rm -rf "$directory"
mkdir -p "$scratch" "$tmpfs"
trap 'rm -rf "$tmpfs" "$scratch"/append-* "$scratch"/overwrite-*' EXIT
python3 prepare.py "$mode" "$directory" --scratch "$scratch"

# Interruptions du NVMe par CPU, avant et après : quel cœur traite les fins d'entrée-sortie.
grep -E 'CPU|nvme' /proc/interrupts > "$directory/interrupts-before.txt" || true

tail -n +2 "$directory/plan.csv" |
while IFS=, read -r run_id core cpu seed rounds warmup_rounds ops file_mib device_stat journal_info; do
    read_file="$scratch/read-$file_mib.dat"
    # Fichier lu, créé une fois et gardé propre (fsync) ; sa taille est contrôlée par le harnais.
    if [ "$(stat -c %s "$read_file" 2>/dev/null || echo 0)" != $((file_mib * 1048576)) ]; then
        ./build/files --create-read-file "$read_file" --file-mib "$file_mib"
    fi
    base=$(printf '%s/run-%03d' "$directory" "$run_id")
    taskset -c "$cpu" ./build/files --run-id "$run_id" --core "$core" --seed "$seed" --rounds "$rounds" \
        --warmup-rounds "$warmup_rounds" --ops "$ops" --file-mib "$file_mib" \
        --read-file "$read_file" --scratch "$scratch" --tmpfs "$tmpfs" \
        --device-stat "$device_stat" --journal-info "$journal_info" \
        --output "$base.csv" --ops-output "$base-ops.csv" --meta "$base-meta.csv"
done

grep -E 'CPU|nvme' /proc/interrupts > "$directory/interrupts-after.txt" || true
