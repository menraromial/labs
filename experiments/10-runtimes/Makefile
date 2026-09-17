MPLCONFIGDIR := $(CURDIR)/build/matplotlib
export MPLCONFIGDIR
export GOCACHE := $(CURDIR)/build/go-cache
CFLAGS := -O2 -std=c17 -Wall -Wextra -Wpedantic
BINARIES := build/warm-c build/churn-c build/churn-go build/noop-c build/noop-c-static build/noop-rust \
	build/noop-go build/launch build/classes/Warm.class build/classes/Churn.class build/classes/Noop.class

.PHONY: all check quick campaign analyze clean

all: $(BINARIES)

build/warm-c: src/c/warm.c
	mkdir -p build
	gcc $(CFLAGS) $< -o $@

build/churn-c: src/c/churn.c
	mkdir -p build
	gcc $(CFLAGS) $< -o $@

build/noop-c: src/c/noop.c
	mkdir -p build
	gcc $(CFLAGS) $< -o $@

build/noop-c-static: src/c/noop.c
	mkdir -p build
	gcc $(CFLAGS) -static $< -o $@

build/launch: src/c/launch.c
	mkdir -p build
	gcc $(CFLAGS) $< -o $@

build/noop-rust: src/rust/noop.rs
	mkdir -p build
	rustc --edition 2021 -C opt-level=3 $< -o $@

build/churn-go: src/go/churn.go
	mkdir -p build
	go build -trimpath -o $@ $<

build/noop-go: src/go/noop.go
	mkdir -p build
	go build -trimpath -o $@ $<

build/classes/%.class: src/java/%.java
	mkdir -p build/classes
	javac --release 17 -d build/classes $<

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

clean:
	$(RM) -r build
