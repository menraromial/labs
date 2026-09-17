#!/usr/bin/env sh
# Exécute le plan : un processus indépendant, épinglé, par ligne de plan.csv, puis la
# mesure du démarrage de chaque version. OPENBLAS_NUM_THREADS=1 est fixé par le Makefile
# pour ces seuls processus.
set -eu

mode=${1:?usage: run.sh check|quick|campaign}
directory="data/$mode"
input="build/input.bin"
python=$(command -v python3)

if [ "$mode" = campaign ] && [ -e "$directory/plan.csv" ] && [ "${FORCE:-0}" != 1 ]; then
    printf '%s existe déjà ; relancer avec FORCE=1 pour le remplacer\n' "$directory" >&2
    exit 1
fi
rm -rf "$directory"
python3 prepare.py "$mode" "$directory"

# Données communes : 2^22 entiers de 64 bits, générés une fois par la version C.
if [ "$(stat -c %s "$input" 2>/dev/null || echo 0)" != 33554432 ]; then
    ./build/bench-c-O2 --generate "$input" --count 4194304 --seed 20260922
fi
sha256sum "$input" > "$directory/input.sha256"

tail -n +2 "$directory/plan.csv" |
while IFS=, read -r run_id build cpu seed rounds warmup_rounds scale_log2; do
    base=$(printf '%s/run-%03d' "$directory" "$run_id")
    case "$build" in
        c-O2) command="./build/bench-c-O2" ;;
        c-O3) command="./build/bench-c-O3" ;;
        rust) command="./build/bench-rust" ;;
        go) command="./build/bench-go" ;;
        python) command="$python src/python/bench.py" ;;
    esac
    # shellcheck disable=SC2086
    taskset -c "$cpu" $command --input "$input" --output "$base.csv" --meta "$base-meta.csv" \
        --run-id "$run_id" --build "$build" --seed "$seed" --rounds "$rounds" \
        --warmup-rounds "$warmup_rounds" --scale-log2 "$scale_log2"
done

cpu=$(sed -n '2p' "$directory/plan.csv" | cut -d, -f3)
taskset -c "$cpu" ./build/launch "$directory/startup.csv" "$(cat "$directory/startup-reps.txt")" 20260922 \
    c-O2 "./build/bench-c-O2 --noop" c-O3 "./build/bench-c-O3 --noop" rust "./build/bench-rust --noop" \
    go "./build/bench-go --noop" python "$python src/python/bench.py --noop" \
    python-numpy "$python src/python/bench.py --noop-numpy"
