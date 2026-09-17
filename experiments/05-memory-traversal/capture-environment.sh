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
    lscpu -C
    free -h
    grep -E 'MemTotal|MemAvailable|AnonHugePages|Hugepagesize' /proc/meminfo
    gcc --version | sed -n '1p'
    python3 --version
    printf 'transparent_hugepage='; read_first /sys/kernel/mm/transparent_hugepage/enabled
    printf 'transparent_hugepage_defrag='; read_first /sys/kernel/mm/transparent_hugepage/defrag
    printf 'page_size='; getconf PAGESIZE
    printf 'scaling_governor='; read_first /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    printf 'energy_performance_preference='; read_first /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference
    printf 'perf_event_paranoid='; read_first /proc/sys/kernel/perf_event_paranoid
    printf 'loadavg='; read_first /proc/loadavg
    systemd-detect-virt || true
    printf 'options de compilation :\n'
    make -s -n build/traversal 2>/dev/null | grep -E '^gcc ' || true
    printf 'sources et binaire :\n'
    sha256sum src/traversal.c build/traversal
} > "$output"
