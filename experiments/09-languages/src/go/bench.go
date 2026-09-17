// E1, version Go (bibliothèque standard seule). Même plan de mesure, mêmes données et
// mêmes boucles « contrôlées » que les versions C, Rust et Python (README, section 4).
package main

import (
	"bufio"
	"encoding/binary"
	"fmt"
	"math"
	"os"
	"runtime"
	"strconv"
	"strings"
	"syscall"
	"time"
	"unsafe"
)

const (
	K         uint64 = 0x9e3779b97f4a7c15
	tableBits        = 17
	tableSize        = 1 << tableBits
	sysGetcpu        = 309 // getcpu sur linux/amd64, absent du paquet syscall
)

// ------------------------------------------------------------------ charges contrôlées

//go:noinline
func hashChain(u []uint64, h uint64) uint64 {
	for i := 0; i < len(u); i++ {
		h = (h ^ u[i]) * K
	}
	return h
}

//go:noinline
func dot(a, b []float64) float64 {
	s := 0.0
	for i := 0; i < len(a); i++ {
		s += a[i] * b[i]
	}
	return s
}

//go:noinline
func countTable(keys []uint32, slotKeys, slotCounts []uint32) {
	for i := 0; i < len(keys); i++ {
		stored := keys[i] + 1
		slot := uint32((uint64(stored) * K) >> (64 - tableBits))
		for slotKeys[slot] != 0 && slotKeys[slot] != stored {
			slot = (slot + 1) & (tableSize - 1)
		}
		slotKeys[slot] = stored
		slotCounts[slot]++
	}
}

// ------------------------------------------------------------------ versions idiomatiques

//go:noinline
func hashChainRange(u []uint64, h uint64) uint64 {
	for _, x := range u {
		h = (h ^ x) * K
	}
	return h
}

//go:noinline
func dotRange(a, b []float64) float64 {
	s := 0.0
	for i, x := range a {
		s += x * b[i]
	}
	return s
}

//go:noinline
func countMap(keys []uint32) map[uint32]uint32 {
	counts := make(map[uint32]uint32)
	for _, k := range keys {
		counts[k]++
	}
	return counts
}

// ------------------------------------------------------------------ outils

func cpu() int {
	var c uint32
	syscall.RawSyscall(sysGetcpu, uintptr(unsafe.Pointer(&c)), 0, 0)
	return int(c)
}

func xorshift(state *uint64) uint64 {
	*state ^= *state >> 12
	*state ^= *state << 25
	*state ^= *state >> 27
	return *state * 2685821657736338717
}

func peakRSSKiB() int64 {
	data, err := os.ReadFile("/proc/self/status")
	if err != nil {
		return -1
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "VmHWM:") {
			v, _ := strconv.ParseInt(strings.Fields(line)[1], 10, 64)
			return v
		}
	}
	return -1
}

func numGC() uint32 {
	var stats runtime.MemStats
	runtime.ReadMemStats(&stats)
	return stats.NumGC
}

type measure struct {
	workload, variant string
	kind              int
	passes            int
}

const (
	hashControl = iota
	hashRange
	dotControl
	dotRange_
	countControl
	countMap_
)

func main() {
	if len(os.Args) == 2 && os.Args[1] == "--noop" {
		return
	}
	opt := map[string]string{}
	for i := 1; i+1 < len(os.Args); i += 2 {
		opt[os.Args[i]] = os.Args[i+1]
	}
	num := func(name string, def uint64) uint64 {
		if v, ok := opt[name]; ok {
			x, err := strconv.ParseUint(v, 10, 64)
			if err != nil {
				panic(err)
			}
			return x
		}
		return def
	}
	input, output, metaPath, build := opt["--input"], opt["--output"], opt["--meta"], opt["--build"]
	runID, seed := num("--run-id", 0), num("--seed", 20260922)
	rounds, warmup, scale := int(num("--rounds", 11)), int(num("--warmup-rounds", 1)), num("--scale-log2", 0)
	if input == "" || output == "" || metaPath == "" || runID == 0 || warmup >= rounds || scale > 12 {
		fmt.Fprintln(os.Stderr, "usage : bench --noop | --input F --output CSV --meta CSV --run-id N --build NOM")
		os.Exit(1)
	}

	nHash := 1 << (20 - scale)
	nDot, nCount := nHash, 1<<(22-scale)
	nTotal := max(nCount, 2*nDot)
	raw, err := os.ReadFile(input)
	if err != nil {
		panic(err)
	}
	u := make([]uint64, nTotal)
	for i := range u {
		u[i] = binary.LittleEndian.Uint64(raw[8*i:])
	}
	a, b := make([]float64, nDot), make([]float64, nDot)
	for i := 0; i < nDot; i++ {
		a[i] = float64(u[i]>>11) * 0x1p-53
		b[i] = float64(u[nDot+i]>>11) * 0x1p-53
	}
	keys := make([]uint32, nCount)
	var keysSum uint64
	for i := range keys {
		keys[i] = uint32(((u[i] >> 48) * ((u[i] >> 32) & 0xFFFF)) >> 16)
		keysSum += uint64(keys[i])
	}
	hashData := u[:nHash]
	slotKeys, slotCounts := make([]uint32, tableSize), make([]uint32, tableSize)

	measures := []measure{
		{"hash_chain", "control", hashControl, 1},
		{"hash_chain", "control_bis", hashControl, 1},
		{"hash_chain", "control_double", hashControl, 2},
		{"hash_chain", "idiomatic", hashRange, 1},
		{"dot", "control", dotControl, 1},
		{"dot", "idiomatic", dotRange_, 1},
		{"count", "control", countControl, 1},
		{"count", "idiomatic", countMap_, 1},
		{"count", "idiomatic_bis", countMap_, 1},
	}
	m := len(measures)
	state := seed ^ (runID * K)
	if state == 0 {
		state = 1
	}
	order := make([]int, 0, m*rounds)
	for r := 0; r < rounds; r++ {
		slice := make([]int, m)
		for j := range slice {
			slice[j] = j
		}
		for j := m; j > 1; j-- {
			other := int(xorshift(&state) % uint64(j))
			slice[j-1], slice[other] = slice[other], slice[j-1]
		}
		order = append(order, slice...)
	}

	type row struct {
		index, before, after int
		elapsed, result      uint64
		gc                   uint32
	}
	rows := make([]row, 0, len(order))
	firstCPU := cpu()
	gcStart := numGC()
	for _, index := range order {
		me := measures[index]
		if me.kind == countControl {
			clear(slotKeys)
			clear(slotCounts)
		}
		runtime.GC() // déchets des échantillons précédents collectés hors chronométrage
		gcBefore := numGC()
		before := cpu()
		t0 := time.Now()
		var r uint64
		var counts map[uint32]uint32
		switch me.kind {
		case hashControl:
			r = hashChain(hashData, 0)
			if me.passes == 2 {
				r = hashChain(hashData, r)
			}
		case hashRange:
			r = hashChainRange(hashData, 0)
		case dotControl:
			r = math.Float64bits(dot(a, b))
		case dotRange_:
			r = math.Float64bits(dotRange(a, b))
		case countControl:
			countTable(keys, slotKeys, slotCounts)
		case countMap_:
			counts = countMap(keys)
		}
		elapsed := uint64(time.Since(t0).Nanoseconds())
		after := cpu()
		gcAfter := numGC()
		if me.kind == countControl {
			for s, k := range slotKeys {
				if k != 0 {
					r += uint64(slotCounts[s]) * (uint64(k) * K)
				}
			}
		}
		if counts != nil {
			for k, c := range counts {
				r += uint64(c) * (uint64(k+1) * K)
			}
		}
		rows = append(rows, row{index, before, after, elapsed, r, gcAfter - gcBefore})
	}
	gcTotal := int(numGC()-gcStart) - len(order) // sans les collectes forcées

	f, err := os.Create(output)
	if err != nil {
		panic(err)
	}
	w := bufio.NewWriter(f)
	fmt.Fprintln(w, "run_id,build,seed,sample,round,phase,position,workload,variant,elements,passes,elapsed_ns,result,gc_delta,cpu_before,cpu_after")
	for s, rw := range rows {
		me := measures[rw.index]
		elements := nCount
		if me.kind == hashControl || me.kind == hashRange {
			elements = nHash
		} else if me.kind == dotControl || me.kind == dotRange_ {
			elements = nDot
		}
		phase := "measure"
		if s/m < warmup {
			phase = "warmup"
		}
		fmt.Fprintf(w, "%d,%s,%d,%d,%d,%s,%d,%s,%s,%d,%d,%d,%016x,%d,%d,%d\n", runID, build, seed, s, s/m, phase, s%m,
			me.workload, me.variant, elements, me.passes, rw.elapsed, rw.result, rw.gc, rw.before, rw.after)
	}
	if w.Flush() != nil || f.Close() != nil {
		os.Exit(1)
	}
	meta, err := os.Create(metaPath)
	if err != nil {
		panic(err)
	}
	fmt.Fprintln(meta, "run_id,build,runtime,first_cpu,peak_rss_kib,keys_sum,gc_total,jit,gil")
	fmt.Fprintf(meta, "%d,%s,%s,%d,%d,%d,%d,none,none\n", runID, build, runtime.Version(), firstCPU, peakRSSKiB(), keysSum, gcTotal)
	if meta.Close() != nil {
		os.Exit(1)
	}
}
