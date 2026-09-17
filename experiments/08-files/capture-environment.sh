#!/usr/bin/env sh
set -eu

output=${1:-data/environment.txt}
read_first() { [ -r "$1" ] && sed -n '1p' "$1" || printf 'indisponible\n'; }
scratch="$(pwd)/build/scratch"
mkdir -p "$scratch"
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
    printf 'scaling_governor='; read_first /sys/devices/system/cpu/cpu11/cpufreq/scaling_governor
    printf 'energy_performance_preference='; read_first /sys/devices/system/cpu/cpu11/cpufreq/energy_performance_preference
    printf 'cpuidle_governor='; read_first /sys/devices/system/cpu/cpuidle/current_governor_ro
    for state in /sys/devices/system/cpu/cpu11/cpuidle/state*; do
        printf 'cpu11 %s latence_sortie_us=%s\n' "$(cat "$state/name")" "$(cat "$state/latency")"
    done
    printf 'loadavg='; read_first /proc/loadavg
    systemd-detect-virt || true
    printf '\nstockage :\n'
    df -h "$scratch" /dev/shm
    findmnt -no SOURCE,FSTYPE,OPTIONS -T "$scratch"
    findmnt -no SOURCE,FSTYPE,OPTIONS -T /dev/shm
    cat /proc/fs/ext4/dm-0/options 2>/dev/null | tr '\n' ' ' || true
    printf '\n'
    sed -n '1p' /proc/fs/jbd2/dm-0-8/info 2>/dev/null || true
    lsblk -o NAME,TYPE,SIZE,ROTA,MODEL,SCHED 2>/dev/null | grep -v loop || true
    for queue in /sys/block/nvme0n1/queue /sys/block/dm-0/queue; do
        for knob in logical_block_size max_sectors_kb read_ahead_kb nr_requests scheduler write_cache fua io_poll; do
            printf '%s/%s=' "$queue" "$knob"; read_first "$queue/$knob"
        done
    done
    printf 'nvme_firmware='; read_first /sys/class/nvme/nvme0/firmware_rev
    printf 'nvme_core.default_ps_max_latency_us='; read_first /sys/module/nvme_core/parameters/default_ps_max_latency_us
    grep -E '^(Dirty|Writeback|Cached|MemAvailable):' /proc/meminfo
    for knob in dirty_ratio dirty_background_ratio dirty_expire_centisecs dirty_writeback_centisecs; do
        printf 'vm.%s=' "$knob"; read_first "/proc/sys/vm/$knob"
    done
    printf 'transparent_hugepage='; read_first /sys/kernel/mm/transparent_hugepage/enabled
    printf 'options de compilation :\n'
    make -s -n build/files 2>/dev/null | grep -E '^gcc ' || true
    printf 'sources et binaire :\n'
    sha256sum src/files.c build/files
} > "$output"
