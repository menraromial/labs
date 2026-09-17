CSTD := -std=c17 -Wall -Wextra -Wpedantic
LEVELS := O0 O1 O2 O3
COMPILERS := gcc clang
BINARIES := $(foreach c,$(COMPILERS),$(LEVELS:%=build/bench-$(c)-%))
MPLCONFIGDIR := $(CURDIR)/build/matplotlib
export MPLCONFIGDIR

.PHONY: all check quick campaign analyze assembly clean

all: $(BINARIES)

# Le harnais est compilé une seule fois, par GCC à -O2 : seuls le compilateur
# et le niveau d'optimisation des noyaux varient d'un binaire à l'autre.
build/harness.o: src/harness.c src/kernels.h
	mkdir -p build
	gcc -O2 $(CSTD) -c $< -o $@

build/kernels-gcc-%.o: src/kernels.c src/kernels.h
	mkdir -p build
	gcc -$* $(CSTD) -DKERNEL_OPT='"gcc-$*"' -c $< -o $@

build/kernels-clang-%.o: src/kernels.c src/kernels.h
	mkdir -p build
	clang -$* $(CSTD) -DKERNEL_OPT='"clang-$*"' -c $< -o $@

build/bench-%: build/harness.o build/kernels-%.o
	gcc $^ -o $@

assembly: $(BINARIES)
	python3 disasm.py $(BINARIES) --reports reports

check: $(BINARIES)
	for binary in $(BINARIES); do ./$$binary --self-test || exit 1; done
	sh run.sh check
	python3 verify.py data/check --replay
	@echo "correction checks: OK"

quick: $(BINARIES)
	mkdir -p data
	sh capture-environment.sh data/environment-quick.txt
	sh run.sh quick
	python3 verify.py data/quick
	python3 disasm.py $(BINARIES) --reports reports
	python3 analyze.py data/quick --assembly reports/assembly.csv --reports reports/quick --figures figures/quick

campaign: $(BINARIES)
	mkdir -p data
	sh capture-environment.sh data/environment-campaign.txt
	sh run.sh campaign
	python3 verify.py data/campaign
	$(MAKE) analyze

analyze: assembly
	python3 analyze.py data/campaign --assembly reports/assembly.csv --reports reports/campaign --figures figures/campaign
	for f in figures/campaign-*.pdf; do \
		pdffonts "$$f" 2>&1 | awk '/Mismatch/ || (NR > 2 && ($$(NF-4) != "yes" || /Type 3/)) { bad = 1 } END { exit bad }' \
			|| { echo "polices non conformes : $$f" >&2; exit 1; }; \
	done

clean:
	$(RM) -r build
