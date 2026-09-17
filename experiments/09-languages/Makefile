MPLCONFIGDIR := $(CURDIR)/build/matplotlib
export MPLCONFIGDIR
# Une seule bibliothèque BLAS en fil unique : réglage par processus, pas global.
export OPENBLAS_NUM_THREADS := 1
GOFLAGS := -trimpath
export GOCACHE := $(CURDIR)/build/go-cache

CFLAGS := -std=c17 -Wall -Wextra -Wpedantic
BINARIES := build/bench-c-O2 build/bench-c-O3 build/bench-rust build/bench-go build/launch

.PHONY: all check quick campaign analyze assembly clean

all: $(BINARIES)

build/bench-c-O2: src/c/bench.c
	mkdir -p build
	gcc -O2 $(CFLAGS) $< -o $@

build/bench-c-O3: src/c/bench.c
	mkdir -p build
	gcc -O3 $(CFLAGS) $< -o $@

build/bench-rust: src/rust/bench.rs
	mkdir -p build
	rustc --edition 2021 -C opt-level=3 $< -o $@

build/bench-go: src/go/bench.go
	mkdir -p build
	go build $(GOFLAGS) -o $@ $<

build/launch: src/c/launch.c
	mkdir -p build
	gcc -O2 $(CFLAGS) $< -o $@

assembly: $(BINARIES)
	python3 disasm.py --reports reports

check: all
	sh run.sh check
	python3 verify.py data/check
	@echo "correction checks: OK"

quick: all
	mkdir -p data
	sh capture-environment.sh data/environment-quick.txt
	sh run.sh quick
	python3 verify.py data/quick
	python3 analyze.py data/quick --reports reports/quick --figures figures/quick

campaign: all
	mkdir -p data
	sh capture-environment.sh data/environment-campaign.txt
	sh run.sh campaign
	python3 verify.py data/campaign
	$(MAKE) analyze

analyze:
	python3 analyze.py data/campaign --reports reports/campaign --figures figures/campaign
	for f in figures/campaign-*.pdf; do \
		pdffonts "$$f" 2>&1 | awk '/Mismatch/ || (NR > 2 && ($$(NF-4) != "yes" || /Type 3/)) { bad = 1 } END { exit bad }' \
			|| { echo "polices non conformes : $$f" >&2; exit 1; }; \
	done

# Retire aussi le fichier d'entrée de 32 Mio et le cache de Go.
clean:
	$(RM) -r build
