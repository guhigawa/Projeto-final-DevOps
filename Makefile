
.PHONY: help setup test test-unit test-integration test-functional test-vulnerability dev staging prod clean

# Show list of commands available

help:
	@echo "Available commands"
	@echo "Development Environment:"
	@echo "make setup - Configure the virtual environment and install dependencies"
	@echo "make dev - deploy local environment with docker-compose.yml"
	@echo "  make clean         - Remove cache files only"
	@echo "  make clean-containers - Stop DEV + STAGING containers"
	@echo "  make clean-prod    - Delete ALL production resources (K8s)"
	@echo "  make clean-all     - Complete cleanup (cache + containers + prod)"
	@echo ""
	@echo "Tests:"
	@echo "make test - run all tests (unit and integration)"
	@echo "make test-unit - Execute unit tests and validators test"
	@echo "make test-integration - execute integration tests"
	@echo "make test-vulnerability - Execute security tests (bandit, safety)"
	@echo ""
	@echo " Environments:"
	@echo "    make staging       - deploy staging environment(docker-compose)"
	@echo "    make prod          - deploy production environment (Kubernetes)"
	@echo ""

#initial configuration

setup:
	@echo "configuring virtual environment"
	python -m venv venv
	@echo "virtual environment created"
	@echo ""
	@echo "Installing development dependencies"
	. venv/bin/activate && pip install -r requirements/development_requirements.txt
	@echo "dependencies installed"
	@echo ""
	@echo "Activate environment: source venv/bin/activate"

#tests
test-unit:
	@echo "Executing unit and validators tests"
	@./scripts/test/run-unit-tests.sh

test-integration:
	@echo "Executing integration tests"
	@./scripts/test/run-integration-test.sh

test-functional:
	@echo "Executing functional tests"
	@./scripts/staging/run-functional-tests.sh

test-vulnerability:
	@echo "Executing security tests"
	@. venv/bin/activate && bandit -r user-service/ product-service/ || true
	@. venv/bin/activate && safety check -r requirements/development_requirements.txt || true

#Environments
dev:
	@echo "Initializing dev environment"
	@cp requirements/development_requirements.txt user-service/requirements.txt
	@cp requirements/development_requirements.txt product-service/requirements.txt
	docker-compose -f docker-compose.yml up -d --build

staging:
	@echo "Initializing staging environment"
	@./scripts/staging/deploy-staging.sh

prod:
	@echo "Deploy production environment"
	@echo "1. Build: ./scripts/prod/build-prod.sh"
	@echo "2. Deploy K8s: ./scripts/prod/deploy-prod.sh"
	@echo ""
	@echo "Execute manually the commands above or the following:"
	@echo "./scripts/prod/build-prod.sh && ./scripts/prod/deploy-prod.sh"

#Clean temporary files
clean:
	@echo "Cleaning temporary files"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov 2>/dev/null || true
	@echo "Clean finished"

# Clean containers
clean-containers:
	@echo "Stopping DEV and STAGING containers"
	@docker-compose -f docker-compose.yml down 2>/dev/null || true
	@docker-compose -f docker-compose.staging.yml --env-file .env.staging down -v 2>/dev/null || true
	@echo "Containers stopped"

# clean production
clean-prod:
	@echo "WARNING: This will delete ALL production resources"
	@read -p "Type 'DELETE PROD' to confirm: " confirm; \
	if [ "$$confirm" = "DELETE PROD" ]; then \
		echo "Deleting production pods"; \
		microk8s kubectl delete namespace projeto-final 2>/dev/null || true; \
		echo "Production cleaned"; \
	else \
		echo "Cancelled"; \
	fi


# Clean everything
clean-all: clean clean-containers clean-prod
	@echo "Full cleanup completed"

#zip
zip:
	@echo "Creating clean ZIP"
	@./scripts/utils/create-clean-zip.sh