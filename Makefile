# Thin wrappers over existing tools only — no unified Python operator CLI.
# See README "Operator shortcuts".
.PHONY: simple status validate surface test smoke check mobile-vit-venv clean-mobile-vit-venv hooks

PY ?= python3
CONFIG_JSON = config/selection.json config/selection_extensions.json \
	config/selection_verification_commands.json config/targets.json
MOBILE_VIT_VENV = artifacts/mobile_vit/venv

simple: status validate smoke

status:
	@jq -r '"top_level_goal: " + .top_level_goal, "current_priority: " + .current_priority, "current_priority_source_artifact: " + .current_priority_source_artifact' config/selection.json

validate:
	jq empty $(CONFIG_JSON)

surface:
	$(PY) -m unittest tests.contract.test_tracked_tool_dependency_boundary -q

test:
	$(PY) -m unittest discover -s tests/contract -q

smoke:
	$(PY) src/tools/run_results_reproduction.py --dry-run

check: validate surface test

mobile-vit-venv:
	$(PY) -m venv $(MOBILE_VIT_VENV)
	$(MOBILE_VIT_VENV)/bin/python -m pip install -U pip
	$(MOBILE_VIT_VENV)/bin/python -m pip install -r requirements/mobile_vit.txt

clean-mobile-vit-venv:
	rm -rf $(MOBILE_VIT_VENV)

hooks:
	@echo "Enable the versioned pre-commit hook once per checkout:"
	@echo "  git config core.hooksPath .githooks"
