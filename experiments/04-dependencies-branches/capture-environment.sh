#!/usr/bin/env sh
set -eu

output=${1:-data/environment.txt}
read_first() { [ -r "$1" ] && sed -n '1p' "$1" || printf 'indisponible\n'; }
{
    date --iso-8601=seconds
    uname -a
    sed -n '1,4p' /etc/os-release
    lscpu
    lscpu -e=CPU,CORE,CACHE,MAXMHZ
    free -h
    gcc --version | sed -n '1p'
    clang --version | sed -n '1p'
    objdump --version | sed -n '1p'
    python3 --version
    printf 'cpu_core='; read_first /sys/devices/cpu_core/cpus
    printf 'cpu_atom='; read_first /sys/devices/cpu_atom/cpus
    printf 'scaling_driver='; read_first /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver
    printf 'scaling_governor='; read_first /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    printf 'energy_performance_preference='; read_first /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference
    printf 'clocksource='; read_first /sys/devices/system/clocksource/clocksource0/current_clocksource
    printf 'perf_event_paranoid='; read_first /proc/sys/kernel/perf_event_paranoid
    printf 'loadavg='; read_first /proc/loadavg
    systemd-detect-virt || true
    printf 'options de compilation :\n'
    make -s -n all 2>/dev/null | grep -E '^(gcc|clang) ' || true
    printf 'sources et binaires :\n'
    sha256sum src/kernels.c src/kernels.h src/harness.c build/bench-*
} > "$output"
