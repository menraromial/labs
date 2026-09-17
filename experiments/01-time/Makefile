CC ?= cc
CFLAGS ?= -O2 -std=c17 -Wall -Wextra -Wpedantic
SEED ?= 20260916

.PHONY: all check quick campaign clean

all: build/time_lab

build/time_lab: src/time_lab.c
	mkdir -p build
	$(CC) $(CFLAGS) $< -o $@

check: build/time_lab
	mkdir -p data
	./build/time_lab --output data/check.csv --pairs 20 --repetitions 1 --batch 10 --sleep-ms 1 --busy-ms 1 --seed $(SEED)
	test "$$(awk -F, '$$1 == "sleep" { print $$8 }' data/check.csv)" = "0"
	test "$$(awk -F, '$$1 == "sleep" { print ($$5 >= 1000000) }' data/check.csv)" = "1"
	@echo "correction checks: OK"

quick: build/time_lab
	mkdir -p data figures reports
	sh capture-environment.sh data/environment-quick.txt
	./build/time_lab --output data/quick.csv --pairs 1000 --repetitions 5 --batch 100 --sleep-ms 20 --busy-ms 10 --seed $(SEED)
	MPLCONFIGDIR=build/matplotlib python3 analyze.py data/quick.csv --summary reports/quick-summary.csv --figure figures/quick.png

campaign: build/time_lab
	mkdir -p data figures reports
	sh capture-environment.sh data/environment-campaign.txt
	./build/time_lab --output data/campaign.csv --pairs 50000 --repetitions 50 --batch 10000 --sleep-ms 100 --busy-ms 50 --seed $(SEED)
	MPLCONFIGDIR=build/matplotlib python3 analyze.py data/campaign.csv --summary reports/campaign-summary.csv --figure figures/campaign.png

clean:
	$(RM) -r build
