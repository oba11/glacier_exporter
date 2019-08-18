DOCKER_IMAGE_NAME ?= s3-exporter
DOCKER_IMAGE_TAG  ?= $(shell git rev-parse --abbrev-ref HEAD)

.PHONY: docker-build
docker-build:
	@echo ">> building docker image '${DOCKER_IMAGE_NAME}'"
	@docker build -t "${DOCKER_IMAGE_NAME}" .

.PHONY: flake
flake:
	@flake8 --statistics app.py

.PHONY: lint
lint:
	@pylint app.py

.PHONY: docker-push
docker-push:
	@echo ">> building docker image '${DOCKER_IMAGE_NAME}' without dev requirements"
	@docker build --build-arg dev_req="" -t "${DOCKER_IMAGE_NAME}" .
	@echo ">> pushing image"
	@docker tag "${DOCKER_IMAGE_NAME}" oba11/"$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)"
	@docker push oba11/"$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)"
