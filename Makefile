include .env


## Environment Variables

AWS_PROFILE="norse3"
AWS_REGION="eu-west-2"
IMAGE_NAME="norse3/aidr-bastion-service"
DOCKER_REGISTRY_BACKEND="557211737463.dkr.ecr.${AWS_REGION}.amazonaws.com"

.ONESHELL:
SHELL := /bin/bash

# Variables
PYTHON_VERSION := 3.12
VENV := .venv
PYTHON := $(VENV)/bin/python${PYTHON_VERSION}
PIP := $(VENV)/bin/pip

# Optional pip cache dir (user may override at runtime)
# e.g., `make run PIP_CACHE_DIR=/tmp/pip-cache`
PIP_CACHE_DIR ?=

ifdef PIP_CACHE_DIR
PIP_CACHE_OPT := --cache-dir $(PIP_CACHE_DIR)
endif

# Application variables
PYTHON_SOURCE_DIRS=app/

# Default target
.DEFAULT_GOAL := help

MAKE               := make --no-print-directory

DESCRIBE           := $(shell git describe --match "v*" --always --tags)
DESCRIBE_PARTS     := $(subst -, ,$(DESCRIBE))

VERSION_TAG        := $(word 1,$(DESCRIBE_PARTS))
COMMITS_SINCE_TAG  := $(word 2,$(DESCRIBE_PARTS))

VERSIONX            := $(subst v,,$(VERSION_TAG))
VERSION_PARTS      := $(subst ., ,$(VERSIONX))

MAJOR              := $(word 1,$(VERSION_PARTS))
MINOR              := $(word 2,$(VERSION_PARTS))
MICRO              := $(word 3,$(VERSION_PARTS))

NEXT_MAJOR         := $(shell echo $$(($(MAJOR)+1)))
NEXT_MINOR         := $(shell echo $$(($(MINOR)+1)))
NEXT_MICRO          = $(shell echo $$(($(MICRO)+$(COMMITS_SINCE_TAG))))

ifeq ($(strip $(COMMITS_SINCE_TAG)),)
CURRENT_VERSION_MICRO := $(MAJOR).$(MINOR).$(MICRO)
CURRENT_VERSION_MINOR := $(CURRENT_VERSION_MICRO)
CURRENT_VERSION_MAJOR := $(CURRENT_VERSION_MICRO)
else
CURRENT_VERSION_MICRO := $(MAJOR).$(MINOR).$(NEXT_MICRO)
CURRENT_VERSION_MINOR := $(MAJOR).$(NEXT_MINOR).0
CURRENT_VERSION_MAJOR := $(NEXT_MAJOR).0.0
endif

DATE                = $(shell date +'%d.%m.%Y')
TIME                = $(shell date +'%H:%M:%S')
COMMIT             := $(shell git rev-parse HEAD)
AUTHOR             := $(firstword $(subst @, ,$(shell git show --format="%aE" $(COMMIT))))
BRANCH_NAME        := $(shell git rev-parse --abbrev-ref HEAD)

TAG_MESSAGE         = "$(TIME) $(DATE) $(AUTHOR) $(BRANCH_NAME)"
COMMIT_MESSAGE     := $(shell git log --format=%B -n 1 $(COMMIT))

CURRENT_TAG_MICRO  := v$(CURRENT_VERSION_MICRO)
CURRENT_TAG_MINOR  := "v$(CURRENT_VERSION_MINOR)"
CURRENT_TAG_MAJOR  := "v$(CURRENT_VERSION_MAJOR)"

# --- Version commands ---
.PHONY: version
version: ## Prints the current version
	@echo "+ $@"
	@$(MAKE) version-micro

.PHONY: version-micro
version-micro:
	@echo "$(CURRENT_VERSION_MICRO)"

.PHONY: version-minor
version-minor:
	@echo "$(CURRENT_VERSION_MINOR)"

.PHONY: version-major
version-major:
	@echo "$(CURRENT_VERSION_MAJOR)"

# --- Tag commands ---
.PHONY: tag-micro
tag-micro:
	@echo "$(CURRENT_TAG_MICRO)"

.PHONY: tag-minor
tag-minor:
	@echo "$(CURRENT_TAG_MINOR)"

.PHONY: tag-major
tag-major:
	@echo "$(CURRENT_TAG_MAJOR)"

# -- Meta info ---
.PHONY: tag-message
tag-message:
	@echo "$(TAG_MESSAGE)"

.PHONY: commit-message
commit-message:
	@echo "$(COMMIT_MESSAGE)"


.PHONY: help
.DEFAULT: help

TAGVERSION := $(shell git describe --tags) 
VERSION := $(shell git describe --tags)_rev.$(shell git rev-parse --short HEAD)

globstar: ## static analysis on codebase
	bash -c "globstar check"

#--- Help ---
help:
	@echo "+ $@"
	@echo Makefile targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' Makefile | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo

clean: ## Removes cached artifacts
	@echo "+ $@"
	rm -rf .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +

reformat:
	black $(PYTHON_SOURCE_DIRS)

# Create the virtual environment if it doesn't exist
setup:
	@echo "+ $@"
	@echo ">>> Creating virtual environment..."
	python${PYTHON_VERSION} -m venv $(VENV)
	source $(VENV)/bin/activate
	$(PIP) install --upgrade pip $(PIP_CACHE_OPT)
# dev requirements; testing, audting and formatting
	$(PIP) install -r requirements.dev $(PIP_CACHE_OPT)
# requirements
	$(PIP) install -r requirements.txt $(PIP_CACHE_OPT)
	@echo ">>> Virtual environment setup complete."

pip-audit:
	@echo "+ $@"
	pip-audit
 
audit: pip-audit globstar
	@echo "+ $@"

test: clean ## Runs pytest on source
	@echo "+ $@"
	@echo "Running unit tests + $@"
	source $(VENV)/bin/activate
	$(PYTHON) -m pytest -s -v

test-api: ## Runs bruno tests for testing API endpoints
	@echo "Running integration tests via Bruno + $@"
	@echo "please ensure that the service is running"
	@bash -c "cd frontend/aegis && bru run --env dev"

test-all: test test-api
	@echo "+ $@"

build-image: ## builds the application image
	@echo "+ $@ - ${CURRENT_TAG_MICRO}" 
	@echo "building image"
	@printf "\033[32m\xE2\x9c\x93 docker pull latest images\n\033[0m"
	@docker pull python:3.12-slim
	@printf "\033[32m\xE2\x9c\x93 Build the docker image\n\033[0m"
	$(eval BUILDER_IMAGE=$(shell docker inspect --format='{{index .RepoDigests 0}}' debian:bookworm-slim))
	@export DOCKER_CONTENT_TRUST=1
	@export DOCKER_BUILDKIT=1
	@TAGGED_VERSION=${CURRENT_TAG_MICRO} IMAGE_NAME=${IMAGE_NAME} docker compose build --build-arg 'BUILDTIME_VERSION_ARG=${CURRENT_TAG_MICRO}'
	@docker tag docker.io/${IMAGE_NAME}:${CURRENT_TAG_MICRO} docker.io/${IMAGE_NAME}:latest

authenticate-aws:
	@echo "+ $@"
	@echo "authenticating with AWS for S3 bucket"
	bash -c -i "aws ecr get-login-password --region ${AWS_REGION} --profile ${AWS_PROFILE} | docker login --username AWS --password-stdin ${DOCKER_REGISTRY_BACKEND}"

push-image: authenticate-aws ## pushes the built container to AWS ECR
	@echo "+ $@"
	@echo "tagging the docker image as latest"
	@docker tag docker.io/${IMAGE_NAME}:latest ${DOCKER_REGISTRY_BACKEND}/${IMAGE_NAME}:latest
	@docker tag docker.io/${IMAGE_NAME}:latest ${DOCKER_REGISTRY_BACKEND}/${IMAGE_NAME}:${CURRENT_TAG_MICRO}
	@echo "tagged image as latest, now pushing the image"
	@docker push ${DOCKER_REGISTRY_BACKEND}/${IMAGE_NAME}:latest
	@echo "pushing the versioned image"
	@docker push ${DOCKER_REGISTRY_BACKEND}/${IMAGE_NAME}:${CURRENT_TAG_MICRO}

deploy: build-image push-image ## Builds the image and pushes to ECR
	@echo "+ $@"
	@echo "deployed to ECR"

start: ## Starts the app
	@echo "+ $@"
	source $(VENV)/bin/activate
	VERSION=${CURRENT_TAG_MICRO} python ./server.py

start-litellm-proxy: ## Starts LiteLLM proxy
	@echo "+ $@"
	source $(VENV)/bin/activate
	litellm --config ./litellm/config.yaml --debug --port 32539

start-stack:
	@echo "+ $@"
	@docker compose up