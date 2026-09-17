// E2, partie 3 : allocation continue à ensemble vivant fixe en Java. Même protocole que
// src/c/churn.c ; le collecteur est choisi par option de la seule JVM (G1 ou Serial).

import java.io.IOException;
import java.io.PrintWriter;
import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;

public final class Churn {
    static final class Obj {
        final long key;
        final long a;
        final long b;

        Obj(long i) {
            key = i;
            a = 2 * i + 1;
            b = 3 * i + 2;
        }
    }

    static long[] gcTotals() {
        long count = 0;
        long millis = 0;
        for (GarbageCollectorMXBean bean : ManagementFactory.getGarbageCollectorMXBeans()) {
            count += Math.max(0, bean.getCollectionCount());
            millis += Math.max(0, bean.getCollectionTime());
        }
        return new long[] {count, millis};
    }

    static long peakRssKib() throws IOException {
        for (String line : Files.readAllLines(Path.of("/proc/self/status"))) {
            if (line.startsWith("VmHWM:")) {
                return Long.parseLong(line.split("\\s+")[1]);
            }
        }
        return -1;
    }

    static String allowedCpus() throws IOException {
        for (String line : Files.readAllLines(Path.of("/proc/self/status"))) {
            if (line.startsWith("Cpus_allowed_list:")) {
                return line.substring(line.indexOf(':') + 1).trim().replace(',', ';');
            }
        }
        return "inconnu";
    }

    public static void main(String[] args) throws IOException {
        HashMap<String, String> opt = new HashMap<>();
        for (int i = 0; i + 1 < args.length; i += 2) {
            opt.put(args[i], args[i + 1]);
        }
        int live = 1 << Integer.parseInt(opt.getOrDefault("--live-log2", "20"));
        int batch = 1 << Integer.parseInt(opt.getOrDefault("--batch-log2", "13"));
        int batches = Integer.parseInt(opt.getOrDefault("--batches", "1024"));
        String runId = opt.get("--run-id");
        String mode = opt.get("--mode");

        Obj[] ring = new Obj[live];
        long i = 0;
        for (; i < live; i++) {
            ring[(int) i] = new Obj(i);
        }
        long[] elapsed = new long[batches];
        long[] before = gcTotals();
        long start = System.nanoTime();
        for (int k = 0; k < batches; k++) {
            long t0 = System.nanoTime();
            for (int j = 0; j < batch; j++) {
                ring[(int) (i & (live - 1))] = new Obj(i);
                i++;
            }
            elapsed[k] = System.nanoTime() - t0;
        }
        long total = System.nanoTime() - start;
        long[] after = gcTotals();
        long checksum = 0;
        for (Obj o : ring) {
            checksum += o.key + o.a + o.b;
        }

        try (PrintWriter out = new PrintWriter(opt.get("--output"))) {
            out.println("run_id,mode,batch,operations,elapsed_ns");
            for (int k = 0; k < batches; k++) {
                out.printf("%s,%s,%d,%d,%d%n", runId, mode, k, batch, elapsed[k]);
            }
        }
        String collectors = String.join("+", ManagementFactory.getGarbageCollectorMXBeans().stream()
                .map(GarbageCollectorMXBean::getName).map(n -> n.replace(' ', '_')).toList());
        try (PrintWriter meta = new PrintWriter(opt.get("--meta"))) {
            meta.println("run_id,mode,runtime,total_ns,operations,checksum,gc_count,gc_pause_ns,peak_rss_kib,cpus_allowed");
            meta.printf("%s,%s,java %s %s,%d,%d,%s,%d,%d,%d,%s%n", runId, mode, System.getProperty("java.vm.version"),
                    collectors, total, (long) batches * batch, Long.toUnsignedString(checksum), after[0] - before[0],
                    (after[1] - before[1]) * 1_000_000L, peakRssKib(), allowedCpus());
        }
    }
}
