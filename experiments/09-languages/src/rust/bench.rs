// E1, version Rust (bibliothèque standard seule). Même plan de mesure, mêmes données et
// mêmes boucles « contrôlées » que les versions C, Go et Python (README, section 4).

use std::collections::HashMap;
use std::fs;
use std::io::Write;
use std::time::Instant;

const K: u64 = 0x9e3779b97f4a7c15;
const TABLE_BITS: u32 = 17;
const TABLE_SIZE: usize = 1 << TABLE_BITS;

extern "C" {
    fn sched_getcpu() -> i32;
}

fn cpu() -> i32 {
    unsafe { sched_getcpu() }
}

// ------------------------------------------------------------------ charges contrôlées

#[inline(never)]
fn hash_chain(u: &[u64], mut h: u64) -> u64 {
    for i in 0..u.len() {
        h = (h ^ u[i]).wrapping_mul(K);
    }
    h
}

#[inline(never)]
fn dot(a: &[f64], b: &[f64]) -> f64 {
    let mut s = 0.0;
    for i in 0..a.len() {
        s += a[i] * b[i];
    }
    s
}

#[inline(never)]
fn count_table(keys: &[u32], slot_keys: &mut [u32], slot_counts: &mut [u32]) {
    for i in 0..keys.len() {
        let stored = keys[i] + 1;
        let mut slot = ((stored as u64).wrapping_mul(K) >> (64 - TABLE_BITS)) as usize;
        while slot_keys[slot] != 0 && slot_keys[slot] != stored {
            slot = (slot + 1) & (TABLE_SIZE - 1);
        }
        slot_keys[slot] = stored;
        slot_counts[slot] += 1;
    }
}

// ------------------------------------------------------------------ versions idiomatiques

#[inline(never)]
fn hash_chain_iter(u: &[u64], h: u64) -> u64 {
    u.iter().fold(h, |h, &x| (h ^ x).wrapping_mul(K))
}

#[inline(never)]
fn dot_iter(a: &[f64], b: &[f64]) -> f64 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}

#[inline(never)]
fn count_hashmap(keys: &[u32]) -> HashMap<u32, u32> {
    let mut counts = HashMap::new();
    for &k in keys {
        *counts.entry(k).or_insert(0) += 1;
    }
    counts
}

// ------------------------------------------------------------------ outils

fn xorshift(state: &mut u64) -> u64 {
    *state ^= *state >> 12;
    *state ^= *state << 25;
    *state ^= *state >> 27;
    state.wrapping_mul(2685821657736338717)
}

fn peak_rss_kib() -> i64 {
    fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| s.lines().find(|l| l.starts_with("VmHWM:")).map(|l| l.to_string()))
        .and_then(|l| l.split_whitespace().nth(1).and_then(|v| v.parse().ok()))
        .unwrap_or(-1)
}

#[derive(Clone, Copy, PartialEq)]
enum Kind {
    HashControl,
    HashIter,
    DotControl,
    DotIter,
    CountControl,
    CountMap,
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() == 2 && args[1] == "--noop" {
        return;
    }
    let mut opt = HashMap::new();
    for pair in args[1..].chunks(2) {
        if pair.len() == 2 {
            opt.insert(pair[0].clone(), pair[1].clone());
        }
    }
    let get = |name: &str| opt.get(name).cloned().unwrap_or_else(|| panic!("option manquante {name}"));
    let num = |name: &str, default: u64| opt.get(name).map(|v| v.parse::<u64>().unwrap()).unwrap_or(default);
    let (input, output, meta_path, build) = (get("--input"), get("--output"), get("--meta"), get("--build"));
    let run_id = num("--run-id", 0);
    let seed = num("--seed", 20260922);
    let rounds = num("--rounds", 11) as usize;
    let warmup = num("--warmup-rounds", 1) as usize;
    let scale = num("--scale-log2", 0);
    assert!(run_id > 0 && warmup < rounds && scale <= 12);

    let n_hash = 1usize << (20 - scale);
    let n_dot = n_hash;
    let n_count = 1usize << (22 - scale);
    let n_total = n_count.max(2 * n_dot);
    let bytes = fs::read(&input).expect("lecture du fichier d'entrée");
    let u: Vec<u64> = bytes[..n_total * 8]
        .chunks_exact(8)
        .map(|c| u64::from_le_bytes(c.try_into().unwrap()))
        .collect();
    let scale53 = 1.0 / (1u64 << 53) as f64;
    let a: Vec<f64> = (0..n_dot).map(|i| (u[i] >> 11) as f64 * scale53).collect();
    let b: Vec<f64> = (0..n_dot).map(|i| (u[n_dot + i] >> 11) as f64 * scale53).collect();
    let keys: Vec<u32> = (0..n_count).map(|i| (((u[i] >> 48) * ((u[i] >> 32) & 0xFFFF)) >> 16) as u32).collect();
    let keys_sum: u64 = keys.iter().map(|&k| k as u64).sum();
    let hash_data = &u[..n_hash];
    let mut slot_keys = vec![0u32; TABLE_SIZE];
    let mut slot_counts = vec![0u32; TABLE_SIZE];

    let measures: [(&str, &str, Kind, u32); 9] = [
        ("hash_chain", "control", Kind::HashControl, 1),
        ("hash_chain", "control_bis", Kind::HashControl, 1),
        ("hash_chain", "control_double", Kind::HashControl, 2),
        ("hash_chain", "idiomatic", Kind::HashIter, 1),
        ("dot", "control", Kind::DotControl, 1),
        ("dot", "idiomatic", Kind::DotIter, 1),
        ("count", "control", Kind::CountControl, 1),
        ("count", "idiomatic", Kind::CountMap, 1),
        ("count", "idiomatic_bis", Kind::CountMap, 1),
    ];
    let m = measures.len();
    let mut state = seed ^ run_id.wrapping_mul(K);
    if state == 0 {
        state = 1;
    }
    let mut order = Vec::with_capacity(m * rounds);
    for _ in 0..rounds {
        let mut slice: Vec<usize> = (0..m).collect();
        for j in (2..=m).rev() {
            let other = (xorshift(&mut state) % j as u64) as usize;
            slice.swap(j - 1, other);
        }
        order.extend(slice);
    }

    let first_cpu = cpu();
    let mut rows = Vec::with_capacity(order.len());
    for (s, &index) in order.iter().enumerate() {
        let (_, _, kind, passes) = measures[index];
        if kind == Kind::CountControl {
            slot_keys.fill(0);
            slot_counts.fill(0);
        }
        let before = cpu();
        let t0 = Instant::now();
        let mut map = None;
        let mut r = match kind {
            Kind::HashControl => {
                let h = hash_chain(hash_data, 0);
                if passes == 2 { hash_chain(hash_data, h) } else { h }
            }
            Kind::HashIter => hash_chain_iter(hash_data, 0),
            Kind::DotControl => dot(&a, &b).to_bits(),
            Kind::DotIter => dot_iter(&a, &b).to_bits(),
            Kind::CountControl => {
                count_table(&keys, &mut slot_keys, &mut slot_counts);
                0
            }
            Kind::CountMap => {
                map = Some(count_hashmap(&keys));
                0
            }
        };
        let elapsed = t0.elapsed().as_nanos() as u64;
        let after = cpu();
        if kind == Kind::CountControl {
            r = slot_keys
                .iter()
                .zip(&slot_counts)
                .filter(|(&k, _)| k != 0)
                .fold(0u64, |acc, (&k, &c)| acc.wrapping_add((c as u64).wrapping_mul((k as u64).wrapping_mul(K))));
        }
        if let Some(counts) = map {   // libérée hors chronométrage
            r = counts.iter().fold(0u64, |acc, (&k, &c)| {
                acc.wrapping_add((c as u64).wrapping_mul(((k + 1) as u64).wrapping_mul(K)))
            });
        }
        rows.push((s, index, elapsed, r, before, after));
    }

    let mut out = fs::File::create(&output).expect("création du CSV");
    writeln!(out, "run_id,build,seed,sample,round,phase,position,workload,variant,elements,passes,elapsed_ns,result,gc_delta,cpu_before,cpu_after").unwrap();
    for (s, index, elapsed, r, before, after) in rows {
        let (workload, variant, kind, passes) = measures[index];
        let elements = match kind {
            Kind::HashControl | Kind::HashIter => n_hash,
            Kind::DotControl | Kind::DotIter => n_dot,
            _ => n_count,
        };
        let round = s / m;
        writeln!(out, "{run_id},{build},{seed},{s},{round},{},{},{workload},{variant},{elements},{passes},{elapsed},{r:016x},0,{before},{after}",
                 if round < warmup { "warmup" } else { "measure" }, s % m).unwrap();
    }
    let mut meta = fs::File::create(&meta_path).expect("création des métadonnées");
    writeln!(meta, "run_id,build,runtime,first_cpu,peak_rss_kib,keys_sum,gc_total,jit,gil").unwrap();
    writeln!(meta, "{run_id},{build},rustc,{first_cpu},{},{keys_sum},0,none,none", peak_rss_kib()).unwrap();
}
