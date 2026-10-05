# Kantyna — build, test and deploy helpers

REGISTRY  ?= 574921529806.dkr.ecr.eu-central-1.amazonaws.com
AWS_REGION ?= eu-central-1
VERSION   ?= 0.0.0-dev
VARIANT   ?= stable
PLATFORM  ?= linux/amd64
SERVICES  := orders-api payments worker web loadgen

CHART     := deploy/helm/kantyna
NAMESPACE ?= kantyna

# Extra tag for non-stable variants, e.g. 1.1.0-receipt-v2
ifneq ($(VARIANT),stable)
VARIANT_TAG := $(VERSION)-$(VARIANT)
endif

.PHONY: help build push ecr-login test test-orders-api test-payments \
        compose-up compose-down helm-lint helm-template legacy-build

help:
	@echo "Targets: build push ecr-login test compose-up compose-down helm-lint helm-template legacy-build"
	@echo "Vars:    REGISTRY=$(REGISTRY) VERSION=$(VERSION) VARIANT=$(VARIANT) PLATFORM=$(PLATFORM)"

build:
	@set -e; for svc in $(SERVICES); do \
	  echo ">> building kantyna/$$svc:$(VERSION) ($(VARIANT), $(PLATFORM))"; \
	  docker build --platform $(PLATFORM) \
	    --build-arg APP_VERSION=$(VERSION) \
	    --build-arg APP_VARIANT=$(VARIANT) \
	    -t $(REGISTRY)/kantyna/$$svc:$(VERSION) \
	    $(if $(VARIANT_TAG),-t $(REGISTRY)/kantyna/$$svc:$(VARIANT_TAG)) \
	    ./$$svc; \
	done

push:
	@set -e; for svc in $(SERVICES); do \
	  docker push $(REGISTRY)/kantyna/$$svc:$(VERSION); \
	  $(if $(VARIANT_TAG),docker push $(REGISTRY)/kantyna/$$svc:$(VARIANT_TAG);) \
	done

ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | \
	  docker login --username AWS --password-stdin $(REGISTRY)

test: test-orders-api test-payments

test-orders-api:
	cd orders-api && uv run pytest -q

test-payments:
	docker run --rm -v "$(CURDIR)/payments:/src" -w /src golang:1.23 go test ./...

compose-up:
	APP_VERSION=$(VERSION) APP_VARIANT=$(VARIANT) docker compose up -d --build

compose-down:
	docker compose down -v

helm-lint:
	helm lint $(CHART)

helm-template:
	helm template kantyna $(CHART) --namespace $(NAMESPACE) \
	  --set global.imageRegistry=$(REGISTRY) \
	  --set global.imageTag=$(VERSION)

legacy-build:
	docker build --platform $(PLATFORM) \
	  --build-arg APP_VERSION=$(VERSION) \
	  --build-arg APP_VARIANT=$(VARIANT) \
	  -f orders-api/Dockerfile.legacy \
	  -t $(REGISTRY)/kantyna/orders-api:$(VERSION)-legacy \
	  ./orders-api
