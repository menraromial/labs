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
    printf 'loadavg='; read_first /proc/loadavg
    printf 'cpu9 frères=%s ; cpu11 frères=%s\n' "$(cat /sys/devices/system/cpu/cpu9/topology/thread_siblings_list)" \
        "$(cat /sys/devices/system/cpu/cpu11/topology/thread_siblings_list)"
    printf '\nenvironnements d exécution :\n'
    gcc --version | sed -n '1p'
    rustc -V
    go version
    java -XshowSettings:vm -version 2>&1
    javac -version 2>&1
    node -p '"node " + process.version + " v8 " + process.versions.v8'
    python3 -VV
    python3 -c "import sys, numpy; print('jit disponible', sys._jit.is_available(), 'gil', sys._is_gil_enabled(), 'numpy', numpy.__version__)"
    printf 'options de compilation :\n'
    make -s -n build/warm-c build/churn-c build/noop-c build/noop-c-static build/noop-rust build/churn-go \
        build/noop-go 2>/dev/null | grep -E '^(gcc|rustc|go|javac) ' || true
    printf 'sources et binaires :\n'
    sha256sum src/*/* build/warm-c build/churn-c build/churn-go build/noop-c build/noop-c-static build/noop-rust \
        build/noop-go build/launch build/classes/*.class
} > "$output"
