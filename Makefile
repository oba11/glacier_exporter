DOCKER_IMAGE_NAME ?= oba11/s3-exporter
DOCKER_IMAGE_TAG  ?= $(shell git rev-parse --abbrev-ref HEAD)

ifeq ($(origin CI),undefined)
command = $()
else
command = @docker exec s3-exporter
endif

.PHONY: flake
flake:
	$(command) flake8 --statistics app.py

.PHONY: lint
lint:
	$(command) pylint app.py

.PHONY: build
build:
	@echo ">> building docker image '${DOCKER_IMAGE_NAME}'"
	@docker build -t "${DOCKER_IMAGE_NAME}" .

.PHONY: run
run: build stop
	@echo ">> running s3-exporter docker container"
	@docker run -d --name s3-exporter "${DOCKER_IMAGE_NAME}" sleep 3600

.PHONY: stop
stop:
	@echo ">> cleaning up s3-exporter docker container"
	@docker rm -f s3-exporter 2> /dev/null || true

.PHONY: docker-push
docker-push:
	@echo ">> building docker image '${DOCKER_IMAGE_NAME}' without dev requirements"
	@docker build --build-arg dev_req="" -t "${DOCKER_IMAGE_NAME}" .
	@echo ">> pushing image"
	@docker tag "${DOCKER_IMAGE_NAME}" "$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)"
	@docker push "$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)"
