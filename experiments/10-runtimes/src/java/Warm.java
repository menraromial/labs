// E2, partie 2 : trajectoire d'échauffement en Java (HotSpot). Mêmes boucles et même
// protocole que src/c/warm.c : à chaque pas, chaîne de hachage puis produit scalaire strict.

import java.io.IOException;
import java.io.PrintWriter;
import java.lang.management.ManagementFactory;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;

public final class Warm {
    static final long K = 0x9e3779b97f4a7c15L;

    static long hashChain(long[] u, int n, long h) {
        for (int i = 0; i < n; i++) {
            h = (h ^ u[i]) * K;
        }
        return h;
    }

    static double dot(double[] a, double[] b, int n) {
        double s = 0.0;
        for (int i = 0; i < n; i++) {
            s += a[i] * b[i];
        }
        return s;
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
        int n = 1 << Integer.parseInt(opt.getOrDefault("--n-log2", "16"));
        int steps = Integer.parseInt(opt.getOrDefault("--steps", "300"));
        String mode = opt.get("--mode");
        long runId = Long.parseLong(opt.get("--run-id"));

        ByteBuffer raw = ByteBuffer.wrap(Files.readAllBytes(Path.of(opt.get("--input")))).order(ByteOrder.LITTLE_ENDIAN);
        long[] u = new long[2 * n];
        raw.asLongBuffer().get(u, 0, 2 * n);
        double[] a = new double[n];
        double[] b = new double[n];
        for (int i = 0; i < n; i++) {
            a[i] = (double) (u[i] >>> 11) * 0x1.0p-53;
            b[i] = (double) (u[n + i] >>> 11) * 0x1.0p-53;
        }
        long[] elapsed = new long[2 * steps];
        long[] result = new long[2 * steps];
        for (int s = 0; s < steps; s++) {
            long t0 = System.nanoTime();
            result[2 * s] = hashChain(u, n, 0);
            long t1 = System.nanoTime();
            double d = dot(a, b, n);
            long t2 = System.nanoTime();
            result[2 * s + 1] = Double.doubleToRawLongBits(d);
            elapsed[2 * s] = t1 - t0;
            elapsed[2 * s + 1] = t2 - t1;
        }
        try (PrintWriter out = new PrintWriter(opt.get("--output"))) {
            out.println("run_id,mode,step,workload,elements,elapsed_ns,result,cpu");
            for (int s = 0; s < 2 * steps; s++) {
                out.printf("%d,%s,%d,%s,%d,%d,%016x,-1%n", runId, mode, s / 2, s % 2 == 1 ? "dot" : "hash_chain",
                        n, elapsed[s], result[s]);
            }
        }
        String arguments = String.join(" ", ManagementFactory.getRuntimeMXBean().getInputArguments());
        try (PrintWriter meta = new PrintWriter(opt.get("--meta"))) {
            meta.println("run_id,mode,runtime,jit,cpus_allowed");
            meta.printf("%d,%s,java %s,%s,%s%n", runId, mode, System.getProperty("java.vm.version"),
                    arguments.contains("-Xint") ? "disabled" : "enabled", allowedCpus());
        }
    }
}
