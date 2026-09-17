CC ?= cc
CFLAGS ?= -O2 -std=c17 -Wall -Wextra -Wpedantic
MPLCONFIGDIR := $(CURDIR)/build/matplotlib
export MPLCONFIGDIR

.PHONY: all check quick campaign prime analyze clean

all: build/microbench

build/microbench: src/microbench.c
	mkdir -p build
	$(CC) $(CFLAGS) $< -o $@

check: build/microbench
	./build/microbench --self-test
	sh run.sh check
	python3 verify.py data/check --replay
	@echo "correction checks: OK"

quick: build/microbench
	mkdir -p data
	sh capture-environment.sh data/environment-quick.txt
	sh run.sh quick
	python3 verify.py data/quick
	python3 analyze.py data/quick --reports reports/quick --figures figures/quick

campaign: build/microbench
	mkdir -p data
	sh capture-environment.sh data/environment-campaign.txt
	sh run.sh campaign
	python3 verify.py data/campaign
	$(MAKE) analyze

# Contrôle exploratoire du premier passage à froid (README, section 3 bis).
prime: build/microbench
	mkdir -p data
	sh capture-environment.sh data/environment-prime.txt
	sh run.sh prime
	python3 verify.py data/prime
	$(MAKE) analyze

analyze:
	python3 analyze.py data/campaign --prime data/prime --reports reports/campaign --figures figures/campaign
	if [ -e data/campaign-v1/plan.csv ]; then \
		python3 analyze.py data/campaign-v1 --reports reports/campaign-v1; \
	fi
	for f in figures/campaign-*.pdf; do \
		pdffonts "$$f" 2>&1 | awk '/Mismatch/ || (NR > 2 && ($$(NF-4) != "yes" || /Type 3/)) { bad = 1 } END { exit bad }' \
			|| { echo "polices non conformes : $$f" >&2; exit 1; }; \
	done

clean:
	$(RM) -r build
