// E2, partie 2 : trajectoire d'échauffement en JavaScript (Node, moteur V8). Même protocole
// que src/c/warm.c. Les nombres de JavaScript sont des flottants de 64 bits : la chaîne de
// hachage entière s'écrit avec BigInt, qui alloue un objet par opération (différence
// inévitable, comme la réduction « & MASK » de Python). Le produit scalaire est identique.

import { readFileSync, writeFileSync } from "node:fs";

const K = 0x9e3779b97f4a7c15n;

function hashChain(u, n, h) {
  for (let i = 0; i < n; i++) {
    h = BigInt.asUintN(64, (h ^ u[i]) * K);
  }
  return h;
}

function dot(a, b, n) {
  let s = 0.0;
  for (let i = 0; i < n; i++) {
    s += a[i] * b[i];
  }
  return s;
}

const opt = {};
for (let i = 2; i + 1 < process.argv.length; i += 2) opt[process.argv[i]] = process.argv[i + 1];
const n = 1 << Number(opt["--n-log2"] ?? 16);
const steps = Number(opt["--steps"] ?? 300);
const mode = opt["--mode"];
const runId = opt["--run-id"];

const bytes = readFileSync(opt["--input"]);
const u = new BigUint64Array(bytes.buffer, bytes.byteOffset, 2 * n).slice();
const a = new Float64Array(n);
const b = new Float64Array(n);
const scale = 2 ** -53;
for (let i = 0; i < n; i++) {
  a[i] = Number(u[i] >> 11n) * scale;
  b[i] = Number(u[n + i] >> 11n) * scale;
}

const elapsed = new BigUint64Array(2 * steps);
const result = new Array(2 * steps);
const bits = new DataView(new ArrayBuffer(8));
for (let s = 0; s < steps; s++) {
  const t0 = process.hrtime.bigint();
  result[2 * s] = hashChain(u, n, 0n);
  const t1 = process.hrtime.bigint();
  const d = dot(a, b, n);
  const t2 = process.hrtime.bigint();
  bits.setFloat64(0, d, true);
  result[2 * s + 1] = bits.getBigUint64(0, true);
  elapsed[2 * s] = t1 - t0;
  elapsed[2 * s + 1] = t2 - t1;
}

const lines = ["run_id,mode,step,workload,elements,elapsed_ns,result,cpu"];
for (let s = 0; s < 2 * steps; s++) {
  lines.push(`${runId},${mode},${Math.floor(s / 2)},${s % 2 ? "dot" : "hash_chain"},${n},${elapsed[s]},` +
    `${result[s].toString(16).padStart(16, "0")},-1`);
}
writeFileSync(opt["--output"], lines.join("\n") + "\n");
const jitless = process.execArgv.includes("--jitless");
const allowedCpus = (readFileSync("/proc/self/status", "utf8").match(/Cpus_allowed_list:\s+(\S+)/) ?? [0, "inconnu"])[1].replaceAll(",", ";");
writeFileSync(opt["--meta"], `run_id,mode,runtime,jit,cpus_allowed\n${runId},${mode},node ${process.version} v8 ` +
  `${process.versions.v8},${jitless ? "disabled" : "enabled"},${allowedCpus}\n`);
