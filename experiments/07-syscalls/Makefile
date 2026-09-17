CFLAGS := -O2 -std=c17 -Wall -Wextra -Wpedantic
MPLCONFIGDIR := $(CURDIR)/build/matplotlib
export MPLCONFIGDIR

.PHONY: all check quick campaign analyze clean

all: build/syscalls

build/syscalls: src/syscalls.c
	mkdir -p build
	gcc $(CFLAGS) $< -o $@

check: build/syscalls
	./build/syscalls --self-test
	sh run.sh check
	python3 verify.py data/check
	@echo "correction checks: OK"

quick: build/syscalls
	mkdir -p data
	sh capture-environment.sh data/environment-quick.txt
	sh run.sh quick
	python3 verify.py data/quick
	python3 analyze.py data/quick --reports reports/quick --figures figures/quick

campaign: build/syscalls
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
