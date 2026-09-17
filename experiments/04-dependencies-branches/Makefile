CSTD := -std=c17 -Wall -Wextra -Wpedantic
BUILDS := gcc-scalar gcc-O2 gcc-O3-v3 clang-scalar clang-O2 clang-O3-v3
BINARIES := $(BUILDS:%=build/bench-%)
MPLCONFIGDIR := $(CURDIR)/build/matplotlib
export MPLCONFIGDIR

# Options des noyaux. « scalar » interdit la vectorisation ; chez GCC, il interdit
# aussi la conversion des if en instructions conditionnelles (cmov). Clang n'offre
# pas d'option documentée équivalente : sa version scalaire garde ses cmov.
FLAGS_gcc-scalar := -O2 -fno-tree-vectorize -fno-if-conversion -fno-if-conversion2
FLAGS_gcc-O2 := -O2
FLAGS_gcc-O3-v3 := -O3 -march=x86-64-v3
FLAGS_clang-scalar := -O2 -fno-vectorize -fno-slp-vectorize
FLAGS_clang-O2 := -O2
FLAGS_clang-O3-v3 := -O3 -march=x86-64-v3

.PHONY: all check quick campaign analyze assembly clean

all: $(BINARIES)

# Le harnais est compilé une seule fois, par GCC à -O2, pour le x86-64 de base.
build/harness.o: src/harness.c src/kernels.h
	mkdir -p build
	gcc -O2 $(CSTD) -c $< -o $@

build/kernels-gcc-%.o: src/kernels.c src/kernels.h
	mkdir -p build
	gcc $(FLAGS_gcc-$*) $(CSTD) -DKERNEL_BUILD='"gcc-$*"' -c $< -o $@

build/kernels-clang-%.o: src/kernels.c src/kernels.h
	mkdir -p build
	clang $(FLAGS_clang-$*) $(CSTD) -DKERNEL_BUILD='"clang-$*"' -c $< -o $@

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
