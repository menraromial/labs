CFLAGS := -O2 -std=c17 -Wall -Wextra -Wpedantic
MPLCONFIGDIR := $(CURDIR)/build/matplotlib
export MPLCONFIGDIR
SCRATCH := $(CURDIR)/build/scratch
SELF_TEST_TMPFS := /dev/shm/labs-d2-self-test

.PHONY: all check quick campaign analyze clean

all: build/files

build/files: src/files.c
	mkdir -p build
	gcc $(CFLAGS) $< -o $@

check: build/files
	mkdir -p $(SCRATCH) $(SELF_TEST_TMPFS)
	./build/files --create-read-file $(SCRATCH)/self-test.dat --file-mib 4
	./build/files --self-test --read-file $(SCRATCH)/self-test.dat --scratch $(SCRATCH) \
		--tmpfs $(SELF_TEST_TMPFS) --file-mib 4 --ops 256; \
		status=$$?; rm -rf $(SELF_TEST_TMPFS) $(SCRATCH)/self-test.dat $(SCRATCH)/append-* $(SCRATCH)/overwrite-*; \
		exit $$status
	sh run.sh check
	python3 verify.py data/check
	@echo "correction checks: OK"

quick: build/files
	mkdir -p data
	sh capture-environment.sh data/environment-quick.txt
	sh run.sh quick
	python3 verify.py data/quick
	python3 analyze.py data/quick --reports reports/quick --figures figures/quick

campaign: build/files
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

# Retire aussi les fichiers de travail (dont le fichier lu de 256 Mio) de build/scratch.
clean:
	$(RM) -r build
