#!/usr/bin/env sh
# Exécute le plan (parties 2 et 3), puis la partie 1 : démarrage et sa décomposition.
# Les options des environnements d'exécution (GOGC, PYTHON_JIT, -Xint, --jitless, choix du
# collecteur) sont propres à chaque processus : aucun réglage global.
set -eu

mode=${1:?usage: run.sh check|quick|campaign}
directory="data/$mode"
input="build/input.bin"
python=$(command -v python3)
node=$(command -v node)
java=$(command -v java)

if [ "$mode" = campaign ] && [ -e "$directory/plan.csv" ] && [ "${FORCE:-0}" != 1 ]; then
    printf '%s existe déjà ; relancer avec FORCE=1 pour le remplacer\n' "$directory" >&2
    exit 1
fi
rm -rf "$directory"
python3 prepare.py "$mode" "$directory"
if [ "$(stat -c %s "$input" 2>/dev/null || echo 0)" != 33554432 ]; then
    ./build/warm-c --generate "$input" --count 4194304 --seed 20260923
fi
sha256sum "$input" > "$directory/input.sha256"

tail -n +2 "$directory/plan.csv" |
while IFS=, read -r run_id part mode_name cpus steps n_log2 live_log2 batch_log2 batches; do
    base=$(printf '%s/%s-%03d' "$directory" "$part" "$run_id")
    cpus=$(printf '%s' "$cpus" | tr ';' ',')
    common="--run-id $run_id --mode $mode_name --output $base.csv --meta $base-meta.csv"
    if [ "$part" = warm ]; then
        args="--input $input --steps $steps --n-log2 $n_log2 $common"
        case "$mode_name" in
            c) taskset -c "$cpus" ./build/warm-c $args ;;
            java|java-2cpu) taskset -c "$cpus" "$java" -cp build/classes Warm $args ;;
            java-xint) taskset -c "$cpus" "$java" -Xint -cp build/classes Warm $args ;;
            node|node-2cpu) taskset -c "$cpus" "$node" src/node/warm.mjs $args ;;
            node-jitless) taskset -c "$cpus" "$node" --jitless src/node/warm.mjs $args ;;
            python) PYTHON_JIT=0 taskset -c "$cpus" "$python" src/python/warm.py $args ;;
            python-jit) PYTHON_JIT=1 taskset -c "$cpus" "$python" src/python/warm.py $args ;;
        esac
    else
        args="--live-log2 $live_log2 --batch-log2 $batch_log2 --batches $batches $common"
        case "$mode_name" in
            c) taskset -c "$cpus" ./build/churn-c $args ;;
            go-gogc100) GOGC=100 taskset -c "$cpus" ./build/churn-go $args ;;
            go-gogc400) GOGC=400 taskset -c "$cpus" ./build/churn-go $args ;;
            java-g1) taskset -c "$cpus" "$java" -XX:+UseG1GC -cp build/classes Churn $args ;;
            java-serial) taskset -c "$cpus" "$java" -XX:+UseSerialGC -cp build/classes Churn $args ;;
            node) taskset -c "$cpus" "$node" src/node/churn.mjs $args ;;
            python-gc) taskset -c "$cpus" "$python" src/python/churn.py $args ;;
            python-nogc) taskset -c "$cpus" "$python" src/python/churn.py --no-gc $args ;;
        esac
    fi
done

# Partie 1 : démarrage de programmes qui se terminent aussitôt, ordre tiré à chaque répétition.
read -r reps decomposition_reps < "$directory/startup-reps.txt"
taskset -c 11 ./build/launch "$directory/startup.csv" "$reps" 20260923 \
    c-dynamic "./build/noop-c" c-static "./build/noop-c-static" rust "./build/noop-rust" go "./build/noop-go" \
    python "$python src/python/noop.py" python-no-site "$python -S src/python/noop.py" \
    python-isolated "$python -I -S src/python/noop.py" python-numpy "$python src/python/noop_numpy.py" \
    node "$node src/node/noop.mjs" node-jitless "$node --jitless src/node/noop.mjs" \
    java "$java -cp build/classes Noop" java-no-cds "$java -Xshare:off -cp build/classes Noop"

# Décomposition : traces fournies par chaque environnement, conservées brutes.
mkdir -p "$directory/decomposition"
i=0
while [ "$i" -lt "$decomposition_reps" ]; do
    taskset -c 11 "$python" -X importtime src/python/noop.py 2> "$directory/decomposition/python-$i.txt"
    taskset -c 11 "$python" -X importtime src/python/noop_numpy.py 2> "$directory/decomposition/python-numpy-$i.txt"
    GODEBUG=inittrace=1 taskset -c 11 ./build/noop-go 2> "$directory/decomposition/go-$i.txt"
    LC_ALL=C taskset -c 11 "$java" -Xlog:startuptime -cp build/classes Noop > "$directory/decomposition/java-$i.txt" 2>&1
    i=$((i + 1))
done
