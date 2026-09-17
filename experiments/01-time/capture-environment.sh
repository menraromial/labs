#!/usr/bin/env sh
set -eu

output=${1:-data/environment.txt}
{
    date --iso-8601=seconds
    uname -a
    sed -n '1,12p' /etc/os-release
    lscpu
    free -h
    cc --version
    python3 --version
    command -v perf >/dev/null 2>&1 && perf --version || true
    printf 'perf_event_paranoid='; sed -n '1p' /proc/sys/kernel/perf_event_paranoid
    printf 'clocksource='; sed -n '1p' /sys/devices/system/clocksource/clocksource0/current_clocksource
    systemd-detect-virt || true
} > "$output"

