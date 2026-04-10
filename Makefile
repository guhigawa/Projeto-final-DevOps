
.PHONY: help setup test test-unit test-integration test-functional test-vulnerability \
        test-security-bandit test-security-safety test-security-pipaudit test-security \
        test-security-trivy test-security-trivy-hub test-all \
        sonar-start sonar-stop sonar-status sonar-scan \
        dev staging prod clean clean-containers clean-prod clean-all zip

# Show list of commands available

help:
	@echo "Available commands"
	@echo "Development Environment:"
	@echo "make setup - Configure the virtual environment and install dependencies"
	@echo "make dev - deploy local environment with docker-compose.yml"
	@echo "make clean         - Remove cache files only"
	@echo "make clean-containers - Stop DEV + STAGING containers"
	@echo "make clean-prod    - Delete ALL production resources (K8s)"
	@echo "make clean-all     - Complete cleanup (cache + containers + prod)"
	@echo "Tests:"
	@echo "make test - run all tests (unit and integration)"
	@echo "make test-unit - Execute unit tests and validators test"
	@echo "make test-integration - execute integration tests"
	@echo "  make test-all       - Run ALL tests (unit + integration + functional)"
	@echo "SECURITY (Code):"
	@echo "  make test-security-bandit   - Bandit static analysis"
	@echo "  make test-security-safety   - Safety vulnerability scan"
	@echo "  make test-security-pipaudit - pip-audit check"
	@echo "  make test-security          - Run ALL code security tests"
	@echo "SECURITY (Containers):"
	@echo "  make test-security-trivy     - Scan local Docker images"
	@echo "SONARQUBE:"
	@echo "  make sonar-start     - Start SonarQube container"
	@echo "  make sonar-stop      - Stop SonarQube container"
	@echo "  make sonar-status    - Check SonarQube status"
	@echo "  make sonar-scan      - Run code analysis (set SONAR_TOKEN)"
	@echo " Environments:"
	@echo "make staging       - deploy staging environment(docker-compose)"
	@echo "make prod          - deploy production environment (Kubernetes)"
#initial configuration

setup:
	@echo "configuring virtual environment"
	python -m venv .venv
	@echo "virtual environment created"
	@echo ""
	@echo "Installing development dependencies"
	. .venv/bin/activate && pip install --upgrade pip
	. .venv/bin/activate && pip install -r requirements/development_requirements.txt
	@echo "dependencies installed"
	@echo ""
	@echo "Activate environment: source .venv/bin/activate"

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

test-all: test-unit test-integration test-functional test-security
	@echo "All tests passed"

test-security-bandit:
	@echo "Executing Bandit security tests"
	@. .venv/bin/activate && bandit -c .bandit -r user-service/ product-service/ --severity-level high || true

test-security-safety:
	@echo "Executing Safety vulnerability scan"
	@. .venv/bin/activate && safety check -r requirements/staging_requirements.txt || true

test-security-pipaudit:
	@echo "Executing pip-audit vulnerability scan"
	@. .venv/bin/activate && pip-audit -r requirements/staging_requirements.txt || true

test-security: test-security-bandit test-security-safety test-security-pipaudit
	@echo "All security tests completed"

test-security-trivy:
	@echo "Executing Trivy vulnerability scan on images"
	@echo "Scanning user-service image..."
	@trivy image --severity HIGH,CRITICAL --exit-code 0 --no-progress projeto_final-user-service:latest || true
	@echo ""
	@echo "Scanning product-service image..."
	@trivy image --severity HIGH,CRITICAL --exit-code 0 --no-progress projeto_final-product-service:latest || true

sonar-start:
	@echo "Starting SonarQube"
	@sudo sysctl -w vm.max_map_count=262144 > /dev/null 2>&1 || true
	@docker-compose -f docker-compose.sonarqube.yml up -d
	@echo "Waiting for SonarQube"
	@sleep 30
	@echo "SonarQube ready at http://localhost:9000 (admin/admin)"

sonar-stop:
	@echo "Stopping SonarQube"
	@docker-compose -f docker-compose.sonarqube.yml down
	@echo "SonarQube stopped"

sonar-scan:
	@echo "Running SonarQube analysis"
	@if [ -z "$(SONAR_TOKEN)" ]; then \
		echo "SONAR_TOKEN not set. Run: export SONAR_TOKEN=your_token"; \
		exit 1; \
	fi
	@echo "Ensuring pysonar is installed"
	@. .venv/bin/activate && pip install -q pysonar
	@echo "Running analysis..."
	@. .venv/bin/activate && pysonar \
		--sonar-host-url=http://localhost:9000 \
		--sonar-token=$(SONAR_TOKEN) \
		--sonar-project-key=projeto-final-devops
	@echo "SonarQube analysis completed"

#Environments
dev:
	@echo "Initializing dev environment"
	@cp requirements/development_requirements.txt user-service/requirements.txt
	@cp requirements/development_requirements.txt product-service/requirements.txt
	docker-compose -f docker-compose.yml build --no-cache
	docker-compose -f docker-compose.yml up -d

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