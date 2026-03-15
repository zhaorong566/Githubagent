.PHONY: install test lint run-chat help

help:          ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install:       ## Install dependencies
	pip install -r requirements.txt

install-dev:   ## Install dependencies + dev extras
	pip install -r requirements.txt pytest

test:          ## Run the test suite
	python -m pytest tests/ -v

chat:          ## Start the interactive chat CLI
	python main.py chat

issue:         ## Analyse an issue: make issue N=42
	python main.py issue $(N)

pr-desc:       ## Generate PR description: make pr-desc N=18
	python main.py pr-desc $(N)

review:        ## Review a PR: make review N=18
	python main.py review $(N)
