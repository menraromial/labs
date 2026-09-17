// E2, partie 3 : allocation continue à ensemble vivant fixe en JavaScript (Node, V8).
// Même protocole que src/c/churn.c ; collectes observées par PerformanceObserver.

import { readFileSync, writeFileSync } from "node:fs";
import { PerformanceObserver } from "node:perf_hooks";

const opt = { "--live-log2": "20", "--batch-log2": "13", "--batches": "1024" };
for (let i = 2; i + 1 < process.argv.length; i += 2) opt[process.argv[i]] = process.argv[i + 1];
const live = 2 ** Number(opt["--live-log2"]);
const batch = 2 ** Number(opt["--batch-log2"]);
const batches = Number(opt["--batches"]);

let gcCount = 0;
let gcDuration = 0;
let measuring = false;
const observer = new PerformanceObserver((list) => {
  for (const entry of list.getEntries()) {
    if (measuring) {
      gcCount += 1;
      gcDuration += entry.duration;
    }
  }
});
observer.observe({ entryTypes: ["gc"] });

function make(i) {
  return { key: i, a: 2 * i + 1, b: 3 * i + 2 };
}

const ring = new Array(live);
let i = 0;
for (; i < live; i++) ring[i] = make(i);

// Les entrées de collecte sont livrées de façon asynchrone : on laisse passer celles du
// remplissage avant d'ouvrir la fenêtre, et celles de la mesure avant de la fermer.
await new Promise((resolve) => setTimeout(resolve, 50));
measuring = true;
const elapsed = new Array(batches);
const start = process.hrtime.bigint();
for (let k = 0; k < batches; k++) {
  const t0 = process.hrtime.bigint();
  for (let j = 0; j < batch; j++) {
    ring[i % live] = make(i);
    i++;
  }
  elapsed[k] = process.hrtime.bigint() - t0;
}
const total = process.hrtime.bigint() - start;
await new Promise((resolve) => setTimeout(resolve, 50));
measuring = false;
observer.disconnect();

let checksum = 0;
for (const o of ring) checksum += o.key + o.a + o.b;
const status = readFileSync("/proc/self/status", "utf8");
const rss = Number((status.match(/VmHWM:\s+(\d+)/) ?? [0, -1])[1]);
const allowedCpus = (readFileSync("/proc/self/status", "utf8").match(/Cpus_allowed_list:\s+(\S+)/) ?? [0, "inconnu"])[1].replaceAll(",", ";");
const lines = ["run_id,mode,batch,operations,elapsed_ns"];
for (let k = 0; k < batches; k++) lines.push(`${opt["--run-id"]},${opt["--mode"]},${k},${batch},${elapsed[k]}`);
writeFileSync(opt["--output"], lines.join("\n") + "\n");
writeFileSync(opt["--meta"], "run_id,mode,runtime,total_ns,operations,checksum,gc_count,gc_pause_ns,peak_rss_kib,cpus_allowed\n" +
  `${opt["--run-id"]},${opt["--mode"]},node ${process.version},${total},${batches * batch},${checksum},${gcCount},` +
  `${Math.round(gcDuration * 1e6)},${rss},${allowedCpus}\n`);
