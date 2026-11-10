PYTHON ?= python3
.PHONY: all test art package check
all:
	$(MAKE) -C application all
test:
	bash application/scripts/RUN_VERIFICATION.sh
art:
	$(PYTHON) -B presentation/build_readme_art.py
package:
	$(PYTHON) -B maintainer/package_release.py
check: package
	$(PYTHON) -B maintainer/check_release.py
