// E2, partie 3 : allocation continue à ensemble vivant fixe en Go. Même protocole que
// src/c/churn.c ; le ramasse-miettes est réglé par la variable GOGC du seul processus.
package main

import (
	"bufio"
	"fmt"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"
)

type object struct{ key, a, b uint64 }

func make3(i uint64) *object { return &object{i, 2*i + 1, 3*i + 2} }

func peakRSSKiB() int64 {
	data, _ := os.ReadFile("/proc/self/status")
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "VmHWM:") {
			v, _ := strconv.ParseInt(strings.Fields(line)[1], 10, 64)
			return v
		}
	}
	return -1
}

// CPU autorisés (Cpus_allowed_list), virgules remplacées par « ; » pour le CSV.
func allowedCPUs() string {
	data, _ := os.ReadFile("/proc/self/status")
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "Cpus_allowed_list:") {
			return strings.ReplaceAll(strings.TrimSpace(strings.TrimPrefix(line, "Cpus_allowed_list:")), ",", ";")
		}
	}
	return "inconnu"
}

func main() {
	opt := map[string]string{"--live-log2": "20", "--batch-log2": "13", "--batches": "1024"}
	for i := 1; i+1 < len(os.Args); i += 2 {
		opt[os.Args[i]] = os.Args[i+1]
	}
	atoi := func(k string) int { v, _ := strconv.Atoi(opt[k]); return v }
	live, batch, batches := 1<<atoi("--live-log2"), 1<<atoi("--batch-log2"), atoi("--batches")
	runID, mode := opt["--run-id"], opt["--mode"]

	ring := make([]*object, live)
	var i uint64
	for ; i < uint64(live); i++ {
		ring[i] = make3(i)
	}
	elapsed := make([]int64, batches)
	var before runtime.MemStats
	runtime.ReadMemStats(&before)
	start := time.Now()
	for k := 0; k < batches; k++ {
		t0 := time.Now()
		for j := 0; j < batch; j++ {
			ring[i&uint64(live-1)] = make3(i)
			i++
		}
		elapsed[k] = time.Since(t0).Nanoseconds()
	}
	total := time.Since(start).Nanoseconds()
	var after runtime.MemStats
	runtime.ReadMemStats(&after)
	var checksum uint64
	for _, o := range ring {
		checksum += o.key + o.a + o.b
	}

	f, _ := os.Create(opt["--output"])
	w := bufio.NewWriter(f)
	fmt.Fprintln(w, "run_id,mode,batch,operations,elapsed_ns")
	for k, e := range elapsed {
		fmt.Fprintf(w, "%s,%s,%d,%d,%d\n", runID, mode, k, batch, e)
	}
	w.Flush()
	f.Close()
	gogc := os.Getenv("GOGC")
	if gogc == "" {
		gogc = "100"
	}
	m, _ := os.Create(opt["--meta"])
	fmt.Fprintln(m, "run_id,mode,runtime,total_ns,operations,checksum,gc_count,gc_pause_ns,peak_rss_kib,cpus_allowed")
	fmt.Fprintf(m, "%s,%s,%s GOGC=%s,%d,%d,%d,%d,%d,%d,%s\n", runID, mode, runtime.Version(), gogc, total,
		batches*batch, checksum, after.NumGC-before.NumGC, after.PauseTotalNs-before.PauseTotalNs, peakRSSKiB(), allowedCPUs())
	m.Close()
}
