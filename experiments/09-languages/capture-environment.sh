#!/usr/bin/env sh
set -eu

output=${1:-data/environment.txt}
read_first() { [ -r "$1" ] && sed -n '1p' "$1" || printf 'indisponible\n'; }
{
    date --iso-8601=seconds
    uname -a
    sed -n '1,4p' /etc/os-release
    lscpu
    free -h
    printf 'scaling_governor='; read_first /sys/devices/system/cpu/cpu11/cpufreq/scaling_governor
    printf 'energy_performance_preference='; read_first /sys/devices/system/cpu/cpu11/cpufreq/energy_performance_preference
    printf 'perf_event_paranoid='; read_first /proc/sys/kernel/perf_event_paranoid
    printf 'loadavg='; read_first /proc/loadavg
    printf '\nchaînes de compilation et environnements d exécution :\n'
    gcc --version | sed -n '1p'
    rustc -vV
    go version
    go env GOAMD64 GOGC GOMAXPROCS GOEXPERIMENT
    python3 -VV
    python3 -c "import sys, numpy; print('jit', sys._jit.is_enabled(), 'gil', sys._is_gil_enabled(), 'numpy', numpy.__version__)"
    printf 'libblas='; readlink -f /usr/lib/x86_64-linux-gnu/libblas.so.3
    printf 'OPENBLAS_NUM_THREADS=%s\n' "${OPENBLAS_NUM_THREADS:-non défini}"
    printf 'options de compilation :\n'
    make -s -n build/bench-c-O2 build/bench-c-O3 build/bench-rust build/bench-go build/launch 2>/dev/null \
        | grep -E '^(gcc|rustc|go) ' || true
    printf 'sources et binaires :\n'
    sha256sum src/c/bench.c src/c/launch.c src/rust/bench.rs src/go/bench.go src/python/bench.py \
        build/bench-c-O2 build/bench-c-O3 build/bench-rust build/bench-go build/launch
} > "$output"
