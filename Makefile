.PHONY: hooks test secrets secrets-history lint-yaml verify requirements

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

# Lock the tools the workflows install, with hashes, choosing only releases at least 14 days old. Needs pip-tools
# and pip 26 or newer; run it with Python 3.14, the version the Semgrep job uses.
requirements:
	cd .github/requirements && for f in ci semgrep; do \
	  python3 -m piptools compile --quiet --generate-hashes --allow-unsafe --strip-extras --no-emit-index-url \
	    --pip-args '--uploaded-prior-to P14D' $$f.in; \
	done
