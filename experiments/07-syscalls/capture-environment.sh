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
    gcc --version | sed -n '1p'
    ldd --version | sed -n '1p'
    python3 --version
    printf 'cmdline='; read_first /proc/cmdline
    grep -H . /sys/devices/system/cpu/vulnerabilities/* 2>/dev/null || true
    grep -E '^CONFIG_(HZ|VIRT_CPU_ACCOUNTING_GEN|TICK_CPU_ACCOUNTING|MITIGATION_PAGE_TABLE_ISOLATION|NO_HZ_FULL)=' \
        "/boot/config-$(uname -r)" 2>/dev/null || true
    printf 'scaling_governor='; read_first /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    printf 'energy_performance_preference='; read_first /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference
    printf 'perf_event_paranoid='; read_first /proc/sys/kernel/perf_event_paranoid
    printf 'loadavg='; read_first /proc/loadavg
    stat -c '%n blksize=%o' /dev/null /dev/zero
    systemd-detect-virt || true
    printf 'options de compilation :\n'
    make -s -n build/syscalls 2>/dev/null | grep -E '^gcc ' || true
    printf 'sources et binaire :\n'
    sha256sum src/syscalls.c build/syscalls
} > "$output"
