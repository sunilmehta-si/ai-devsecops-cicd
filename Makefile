.PHONY: hooks test secrets secrets-history lint-yaml verify

hooks:
	sh scripts/install-hooks.sh

test:
	python3 -m unittest discover -s tests -t . -q

secrets:
	python3 scripts/check_secrets.py --all

secrets-history:
	python3 scripts/check_secrets.py --history

lint-yaml:
	python3 scripts/lint_yaml.py

verify: test secrets secrets-history lint-yaml
