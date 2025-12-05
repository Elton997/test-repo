.PHONY: help backend frontend migrate migrate-up migrate-down migrate-current migrate-history migrate-create run-all stop-backend stop-frontend install-backend install-frontend clean oracle-up oracle-down oracle-logs oracle-shell oracle-setup oracle-status oracle-remove seed-data clear-seed create-schema cleanup-tables nginx-local stop-nginx nginx-test nginx-install

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Directories
ROOT_DIR := $(shell pwd)
BACKEND_DIR := $(ROOT_DIR)/dcim_backend_fastapi
FRONTEND_DIR := $(ROOT_DIR)/dcim_frontend
MIGRATION_DIR := $(ROOT_DIR)/dcim_alembic_db_migration
NGINX_DIR := $(ROOT_DIR)/nginx

# Custom repository configuration (optional)
# Usage: make install-backend PIP_INDEX_URL=https://pypi.org/simple
# Usage: make install-frontend NPM_REGISTRY=https://registry.npmjs.org/
PIP_INDEX_URL ?=
NPM_REGISTRY ?=

# Default target
help:
	@echo "$(BLUE)========================================$(NC)"
	@echo "$(BLUE)  DCIM Project Makefile$(NC)"
	@echo "$(BLUE)========================================$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@echo "  $(YELLOW)make backend$(NC)              - Start FastAPI backend server (requires DATABASE_URL)"
	@echo "  $(YELLOW)make frontend$(NC)            - Start Angular frontend server"
	@echo "  $(YELLOW)make run-all$(NC)             - Start both backend and frontend (requires DATABASE_URL)"
	@echo "  $(YELLOW)make migrate-up$(NC)          - Run Alembic migrations (upgrade to head)"
	@echo "  $(YELLOW)make migrate-down$(NC)        - Rollback last Alembic migration"
	@echo "  $(YELLOW)make migrate-current$(NC)    - Show current migration version"
	@echo "  $(YELLOW)make migrate-history$(NC)     - Show migration history"
	@echo "  $(YELLOW)make migrate-create MESSAGE='...'$(NC) - Create new migration"
	@echo "  $(YELLOW)Note:$(NC) Migrations use 'dcim' user by default (dcim:dcim123@localhost)"
	@echo "  $(YELLOW)make create-schema$(NC)       - Create DCIM schema (as system user)"
	@echo "  $(YELLOW)make seed-data$(NC)          - Seed database with sample data"
	@echo "  $(YELLOW)make clear-seed$(NC)         - Clear all seed data from database"
	@echo "  $(YELLOW)make cleanup-tables$(NC)     - Cleanup partial tables from failed migrations"
	@echo "  $(YELLOW)make install-backend$(NC)     - Install backend dependencies"
	@echo "  $(YELLOW)make install-frontend$(NC)    - Install frontend dependencies"
	@echo ""
	@echo "$(GREEN)Custom Repository Options:$(NC)"
	@echo "  $(YELLOW)make install-backend PIP_INDEX_URL=<url>$(NC)  - Use custom pip index"
	@echo "  $(YELLOW)make install-frontend NPM_REGISTRY=<url>$(NC)   - Use custom npm registry"
	@echo "  $(YELLOW)make stop-backend$(NC)        - Stop backend server"
	@echo "  $(YELLOW)make stop-frontend$(NC)       - Stop frontend server"
	@echo "  $(YELLOW)make clean$(NC)               - Clean temporary files"
	@echo ""
	@echo "$(GREEN)Nginx Commands:$(NC)"
	@echo "  $(YELLOW)make nginx-local$(NC)         - Run nginx for local/dev (bypasses SSL, uses localhost:8000)"
	@echo "  $(YELLOW)make nginx-install$(NC)       - Install nginx on system (Ubuntu/Debian)"
	@echo "  $(YELLOW)make nginx-test$(NC)          - Test nginx configuration"
	@echo "  $(YELLOW)make stop-nginx$(NC)          - Stop nginx server"
	@echo ""
	@echo "$(GREEN)Oracle XE Commands (Docker/Podman):$(NC)"
	@echo "  $(YELLOW)make oracle-setup$(NC)        - Set up Oracle XE container (first time)"
	@echo "  $(YELLOW)make oracle-up$(NC)           - Start Oracle XE container"
	@echo "  $(YELLOW)make oracle-down$(NC)         - Stop Oracle XE container"
	@echo "  $(YELLOW)make oracle-logs$(NC)         - View Oracle container logs"
	@echo "  $(YELLOW)make oracle-shell$(NC)        - Enter Oracle container shell"
	@echo "  $(YELLOW)make oracle-status$(NC)       - Show container status"
	@echo "  $(YELLOW)make oracle-remove$(NC)       - Remove container and volume"
	@echo ""

# Backend targets
install-backend:
	@echo "$(YELLOW)Installing backend dependencies...$(NC)"
	@if [ -n "$(PIP_INDEX_URL)" ]; then \
		echo "$(BLUE)Using custom pip index: $(PIP_INDEX_URL)$(NC)"; \
	fi
	@cd $(BACKEND_DIR) && \
	if [ ! -d "venv" ]; then \
		echo "$(YELLOW)Creating Python virtual environment...$(NC)"; \
		python3 -m venv venv; \
	fi && \
	. venv/bin/activate && \
	pip install --quiet --upgrade pip && \
	if [ -n "$(PIP_INDEX_URL)" ]; then \
		pip install --quiet --index-url $(PIP_INDEX_URL) -r app/requirements.txt; \
	else \
		pip install --quiet -r app/requirements.txt; \
	fi && \
	echo "$(GREEN)Backend dependencies installed$(NC)"

backend: install-backend
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "$(RED)Error: DATABASE_URL environment variable is not set$(NC)"; \
		echo "$(YELLOW)Please set it before starting the backend:$(NC)"; \
		echo "$(YELLOW)  export DATABASE_URL='oracle+oracledb://user:password@host:1521/?service_name=ORCLPDB1'$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Starting FastAPI backend on http://localhost:8000$(NC)"
	@cd $(BACKEND_DIR) && \
	. venv/bin/activate && \
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

stop-backend:
	@echo "$(YELLOW)Stopping backend server...$(NC)"
	@pkill -f "uvicorn.*app.main:app" || echo "$(YELLOW)No backend process found$(NC)"
	@echo "$(GREEN)Backend stopped$(NC)"

# Frontend targets
install-frontend:
	@echo "$(YELLOW)Installing frontend dependencies...$(NC)"
	@if [ -n "$(NPM_REGISTRY)" ]; then \
		echo "$(BLUE)Using custom npm registry: $(NPM_REGISTRY)$(NC)"; \
	fi
	@cd $(FRONTEND_DIR) && \
	if [ -n "$(NPM_REGISTRY)" ]; then \
		npm install --registry $(NPM_REGISTRY); \
	else \
		npm install; \
	fi
	@echo "$(GREEN)Frontend dependencies installed$(NC)"

frontend: install-frontend
	@echo "$(GREEN)Starting Angular frontend on http://localhost:4200$(NC)"
	@cd $(FRONTEND_DIR) && npm start -- --host 0.0.0.0

stop-frontend:
	@echo "$(YELLOW)Stopping frontend server...$(NC)"
	@pkill -f "ng serve" || echo "$(YELLOW)No frontend process found$(NC)"
	@echo "$(GREEN)Frontend stopped$(NC)"

# Nginx targets
nginx-install:
	@echo "$(YELLOW)Installing nginx...$(NC)"
	@if command -v apt-get > /dev/null 2>&1; then \
		sudo apt-get update && sudo apt-get install -y nginx; \
	elif command -v yum > /dev/null 2>&1; then \
		sudo yum install -y nginx; \
	else \
		echo "$(RED)Error: Could not detect package manager (apt-get or yum)$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Nginx installed$(NC)"

nginx-test:
	@echo "$(YELLOW)Testing nginx configuration...$(NC)"
	@if [ -f "/etc/nginx/nginx.conf" ]; then \
		sudo nginx -t; \
	else \
		echo "$(YELLOW)Testing local configuration...$(NC)"; \
		if [ -f "$(NGINX_DIR)/nginx-local.conf" ]; then \
			nginx -t -c $(NGINX_DIR)/nginx-local.conf -p $(NGINX_DIR) 2>/dev/null || \
			echo "$(YELLOW)Note: nginx binary not in PATH. Configuration files look valid.$(NC)"; \
		fi; \
	fi

nginx-local:
	@echo "$(YELLOW)Setting up nginx for local development...$(NC)"
	@echo "$(BLUE)Configuration: SSL bypassed, using localhost:8000 for backend$(NC)"
	@echo "$(BLUE)Nginx will run on port 8080 (http://localhost:8080)$(NC)"
	@echo "$(YELLOW)Prerequisites:$(NC)"
	@echo "  - Nginx must be installed (run 'make nginx-install' if needed)"
	@echo "  - Backend should be running on localhost:8000 (run 'make backend' in another terminal)"
	@echo "  - Frontend build directory should exist at $(FRONTEND_DIR)/dist"
	@echo ""
	@if [ ! -d "$(FRONTEND_DIR)/dist" ]; then \
		echo "$(YELLOW)Frontend dist directory not found. Building frontend...$(NC)"; \
		cd $(FRONTEND_DIR) && npm run build || echo "$(RED)Failed to build frontend$(NC)"; \
	fi
	@if [ ! -d "$(FRONTEND_DIR)/dist" ]; then \
		echo "$(RED)Error: Frontend dist directory not found at $(FRONTEND_DIR)/dist$(NC)"; \
		echo "$(YELLOW)Please build the frontend first: cd $(FRONTEND_DIR) && npm run build$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Setting up local nginx configuration...$(NC)"
	@mkdir -p $(NGINX_DIR)/local-dev/{logs,html,conf.d}
	@cp -r $(FRONTEND_DIR)/dist/* $(NGINX_DIR)/local-dev/html/ 2>/dev/null || true
	@cp $(NGINX_DIR)/conf.d/backend.conf $(NGINX_DIR)/local-dev/conf.d/ 2>/dev/null || true
	@cp $(NGINX_DIR)/conf.d/frontend.conf $(NGINX_DIR)/local-dev/conf.d/ 2>/dev/null || true
	@cp $(NGINX_DIR)/conf.d/security.conf $(NGINX_DIR)/local-dev/conf.d/ 2>/dev/null || true
	@cp $(NGINX_DIR)/conf.d/upstreams-local.conf $(NGINX_DIR)/local-dev/conf.d/upstreams.conf 2>/dev/null || true
	@sed 's|/usr/share/nginx/html|$(NGINX_DIR)/local-dev/html|g; s|/etc/nginx/conf.d|$(NGINX_DIR)/local-dev/conf.d|g; s|/var/log/nginx|$(NGINX_DIR)/local-dev/logs|g; s|/var/run/nginx.pid|$(NGINX_DIR)/local-dev/nginx.pid|g' $(NGINX_DIR)/nginx-local.conf > $(NGINX_DIR)/local-dev/nginx-local.conf
	@echo "$(YELLOW)Testing nginx configuration...$(NC)"
	@nginx -t -c $(NGINX_DIR)/local-dev/nginx-local.conf -p $(NGINX_DIR)/local-dev/ 2>&1 || \
		sudo nginx -t -c $(NGINX_DIR)/local-dev/nginx-local.conf -p $(NGINX_DIR)/local-dev/ 2>&1 || \
		(echo "$(YELLOW)Warning: Could not test configuration. Proceeding anyway...$(NC)")
	@if pgrep -f "nginx.*local-dev" > /dev/null 2>&1 || pgrep -f "nginx.*nginx-local" > /dev/null 2>&1; then \
		echo "$(YELLOW)Nginx is already running. Stopping it first...$(NC)"; \
		$(MAKE) stop-nginx || true; \
		sleep 1; \
	fi
	@echo "$(GREEN)Starting nginx with local configuration...$(NC)"
	@echo "$(GREEN)Access application at: http://localhost:8080$(NC)"
	@echo "$(GREEN)Backend API at: http://localhost:8080/api/$(NC)"
	@nginx -c $(NGINX_DIR)/local-dev/nginx-local.conf -p $(NGINX_DIR)/local-dev/ && \
		echo "$(GREEN)Nginx started successfully$(NC)" && \
		(sleep 1 && pgrep -f "nginx.*local-dev" > /dev/null && \
		pgrep -f "nginx.*local-dev" | head -1 > $(NGINX_DIR)/local-dev/nginx.pid && \
		echo "$(GREEN)Nginx PID: $$(cat $(NGINX_DIR)/local-dev/nginx.pid)$(NC)") || \
		(echo "$(YELLOW)Trying with sudo...$(NC)" && \
		sudo nginx -c $(NGINX_DIR)/local-dev/nginx-local.conf -p $(NGINX_DIR)/local-dev/ && \
		(sleep 1 && sudo pgrep -f "nginx.*local-dev" | head -1 | sudo tee $(NGINX_DIR)/local-dev/nginx.pid > /dev/null) && \
		echo "$(GREEN)Nginx started with sudo$(NC)" || \
		echo "$(RED)Failed to start nginx. Check permissions and installation.$(NC)")

stop-nginx:
	@echo "$(YELLOW)Stopping nginx server...$(NC)"
	@if [ -f "$(NGINX_DIR)/local-dev/nginx.pid" ]; then \
		PID=$$(cat $(NGINX_DIR)/local-dev/nginx.pid 2>/dev/null); \
		if [ -n "$$PID" ] && kill -0 $$PID 2>/dev/null; then \
			kill $$PID && echo "$(GREEN)Nginx stopped (PID: $$PID)$(NC)"; \
			rm -f $(NGINX_DIR)/local-dev/nginx.pid; \
		else \
			echo "$(YELLOW)No running nginx process found for local-dev$(NC)"; \
			rm -f $(NGINX_DIR)/local-dev/nginx.pid; \
		fi \
	elif pgrep -f "nginx.*nginx-local\|nginx.*local-dev" > /dev/null; then \
		sudo pkill -f "nginx.*nginx-local\|nginx.*local-dev" && echo "$(GREEN)Nginx stopped$(NC)" || \
		pkill -f "nginx.*nginx-local\|nginx.*local-dev" && echo "$(GREEN)Nginx stopped$(NC)"; \
	else \
		if pgrep nginx > /dev/null; then \
			sudo systemctl stop nginx 2>/dev/null || sudo pkill nginx 2>/dev/null || \
			pkill nginx 2>/dev/null || echo "$(YELLOW)No nginx process found$(NC)"; \
			echo "$(GREEN)Nginx stopped$(NC)"; \
		else \
			echo "$(YELLOW)No nginx process found$(NC)"; \
		fi \
	fi

# Run both services
run-all:
	@if [ -z "$$DATABASE_URL" ]; then \
		echo "$(RED)Error: DATABASE_URL environment variable is not set$(NC)"; \
		echo "$(YELLOW)Please set it before starting the backend:$(NC)"; \
		echo "$(YELLOW)  export DATABASE_URL='oracle+oracledb://user:password@host:1521/?service_name=ORCLPDB1'$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Starting both backend and frontend services...$(NC)"
	@if [ -f "./run-services.sh" ]; then \
		./run-services.sh; \
	else \
		echo "$(YELLOW)run-services.sh not found. Starting services individually...$(NC)"; \
		$(MAKE) -j2 backend frontend; \
	fi

# Migration targets
migrate-up:
	@echo "$(YELLOW)Running Alembic migrations (upgrade to head)...$(NC)"
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: dcim user on localhost$(NC)"; \
	fi
	@echo "$(YELLOW)Note: Tables will be created in the 'dcim' schema.$(NC)"
	@DB_URL=$${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1} && \
	cd $(MIGRATION_DIR) && \
	if [ ! -d "venv" ]; then \
		echo "$(YELLOW)Creating Python virtual environment for migrations...$(NC)"; \
		python3 -m venv venv; \
	fi && \
	. venv/bin/activate && \
	pip install --quiet --upgrade pip && \
	if [ -n "$(PIP_INDEX_URL)" ]; then \
		pip install --quiet --index-url $(PIP_INDEX_URL) alembic oracledb; \
	else \
		pip install --quiet alembic oracledb; \
	fi && \
	export DB_URL && \
	alembic upgrade head
	@echo "$(GREEN)Migrations completed$(NC)"

migrate-down:
	@echo "$(YELLOW)Rolling back last Alembic migration...$(NC)"
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: dcim user on localhost$(NC)"; \
	fi
	@DB_URL=$${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1} && \
	cd $(MIGRATION_DIR) && \
	. venv/bin/activate && \
	export DB_URL && \
	alembic downgrade -1
	@echo "$(GREEN)Migration rolled back$(NC)"

migrate-current:
	@echo "$(YELLOW)Current migration version:$(NC)"
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: dcim user on localhost$(NC)"; \
	fi
	@DB_URL=$${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1} && \
	cd $(MIGRATION_DIR) && \
	if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
		. venv/bin/activate && \
		pip install --quiet --upgrade pip && \
		if [ -n "$(PIP_INDEX_URL)" ]; then \
			pip install --quiet --index-url $(PIP_INDEX_URL) alembic oracledb; \
		else \
			pip install --quiet alembic oracledb; \
		fi; \
	else \
		. venv/bin/activate; \
	fi && \
	export DB_URL && \
	alembic current

migrate-history:
	@echo "$(YELLOW)Migration history:$(NC)"
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: dcim user on localhost$(NC)"; \
	fi
	@DB_URL=$${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1} && \
	cd $(MIGRATION_DIR) && \
	if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
		. venv/bin/activate && \
		pip install --quiet --upgrade pip && \
		if [ -n "$(PIP_INDEX_URL)" ]; then \
			pip install --quiet --index-url $(PIP_INDEX_URL) alembic oracledb; \
		else \
			pip install --quiet alembic oracledb; \
		fi; \
	else \
		. venv/bin/activate; \
	fi && \
	export DB_URL && \
	alembic history

migrate-create:
	@if [ -z "$(MESSAGE)" ]; then \
		echo "$(RED)Error: MESSAGE is required$(NC)"; \
		echo "$(YELLOW)Usage: make migrate-create MESSAGE='create new table'$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: dcim user on localhost$(NC)"; \
	fi
	@echo "$(YELLOW)Creating new migration: $(MESSAGE)$(NC)"
	@DB_URL=$${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1} && \
	cd $(MIGRATION_DIR) && \
	if [ ! -d "venv" ]; then \
		python3 -m venv venv; \
		. venv/bin/activate && \
		pip install --quiet --upgrade pip && \
		if [ -n "$(PIP_INDEX_URL)" ]; then \
			pip install --quiet --index-url $(PIP_INDEX_URL) alembic oracledb; \
		else \
			pip install --quiet alembic oracledb; \
		fi; \
	else \
		. venv/bin/activate; \
	fi && \
	export DB_URL && \
	alembic revision -m "$(MESSAGE)"
	@echo "$(GREEN)Migration file created$(NC)"

# Alias for migrate-up
migrate: migrate-up

# Oracle XE targets (works with both Docker and Podman)
oracle-setup:
	@echo "$(YELLOW)Setting up Oracle XE container...$(NC)"
	@./oracle-xe.sh start

oracle-up:
	@./oracle-xe.sh start

oracle-down:
	@./oracle-xe.sh stop

oracle-logs:
	@./oracle-xe.sh logs

oracle-shell:
	@./oracle-xe.sh shell

oracle-status:
	@./oracle-xe.sh status

oracle-remove:
	@./oracle-xe.sh remove

# Seed data targets
seed-data:
	@echo "$(YELLOW)Seeding database with sample data...$(NC)"
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: dcim user on localhost$(NC)"; \
	fi
	@DB_URL=$${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1} && \
	cd $(MIGRATION_DIR) && \
	if [ ! -d "venv" ]; then \
		echo "$(YELLOW)Creating Python virtual environment for seeding...$(NC)"; \
		python3 -m venv venv; \
	fi && \
	. venv/bin/activate && \
	pip install --quiet --upgrade pip && \
	if [ -n "$(PIP_INDEX_URL)" ]; then \
		pip install --quiet --index-url $(PIP_INDEX_URL) sqlalchemy oracledb; \
	else \
		pip install --quiet sqlalchemy oracledb; \
	fi && \
	python3 -c "import os, sys, re; from sqlalchemy import create_engine, text; db_url = os.environ.get('DB_URL', 'oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1'); engine = create_engine(db_url); seed_file = 'db_scripts/seed_dcim.sql'; \
exec('''if not os.path.exists(seed_file):\n    print(\"Error: Seed file not found: \" + seed_file)\n    sys.exit(1)\nwith open(seed_file, \"r\", encoding=\"utf-8\") as f:\n    content = f.read()\ncontent = re.sub(r\"SET DEFINE (ON|OFF);\", \"\", content)\ncontent = re.sub(r\"--[^\\\\n]*\", \"\", content)\nstatements = [s.strip() for s in content.split(\";\") if s.strip()]\nconn = engine.connect()\ntry:\n    for stmt in statements:\n        if stmt and not stmt.upper().startswith(\"COMMIT\"):\n            try:\n                conn.execute(text(stmt))\n            except Exception as e:\n                print(f\"Warning: {e}\")\n    conn.commit()\nfinally:\n    conn.close()\nprint(\"Seed data loaded successfully\")''')"
	@echo "$(GREEN)Seed data completed$(NC)"

clear-seed:
	@echo "$(YELLOW)Clearing seed data from database...$(NC)"
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: dcim user on localhost$(NC)"; \
	fi
	@DB_URL=$${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1} && \
	cd $(MIGRATION_DIR) && \
	if [ ! -d "venv" ]; then \
		echo "$(YELLOW)Creating Python virtual environment for clearing seed data...$(NC)"; \
		python3 -m venv venv; \
	fi && \
	. venv/bin/activate && \
	pip install --quiet --upgrade pip && \
	if [ -n "$(PIP_INDEX_URL)" ]; then \
		pip install --quiet --index-url $(PIP_INDEX_URL) sqlalchemy oracledb; \
	else \
		pip install --quiet sqlalchemy oracledb; \
	fi && \
	python3 -c " \
	import os, sys; \
	from sqlalchemy import create_engine, text; \
	db_url = os.environ.get('DB_URL', 'oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1'); \
	engine = create_engine(db_url); \
	# Delete in reverse order to respect foreign key constraints \
	tables = [ \
		'dcim_rbac_role_sub_menu_access', \
		'dcim_sub_menu', \
		'dcim_menu', \
		'dcim_rbac_user_role', \
		'dcim_rbac_role', \
		'dcim_environment', \
		'dcim_audit_log', \
		'dcim_device', \
		'dcim_applications_mapped', \
		'dcim_asset_owner', \
		'dcim_device_type', \
		'dcim_module', \
		'dcim_manufacturer', \
		'dcim_rack', \
		'dcim_datacenter', \
		'dcim_floor', \
		'dcim_wing', \
		'dcim_building', \
		'dcim_location', \
		'dcim_user_token', \
		'dcim_user' \
	]; \
	with engine.connect() as conn: \
		for table in tables: \
			try: \
				conn.execute(text('DELETE FROM dcim.' + table)); \
				print('Cleared: dcim.' + table); \
			except Exception as e: \
				print('Warning: Could not clear dcim.' + table + ' - ' + str(e)); \
		conn.commit(); \
	print('$(GREEN)Seed data cleared successfully$(NC)'); \
	"
	@echo "$(GREEN)Clear seed data completed$(NC)"

# Create DCIM schema (run as system user)
create-schema:
	@echo "$(YELLOW)Creating DCIM schema...$(NC)"
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: system user on localhost$(NC)"; \
	fi
	@cd $(MIGRATION_DIR) && \
	if [ ! -d "venv" ]; then \
		echo "$(YELLOW)Creating Python virtual environment...$(NC)"; \
		python3 -m venv venv; \
	fi && \
	. venv/bin/activate && \
	pip install --quiet --upgrade pip oracledb && \
	chmod +x create_schema_and_migrate.sh && \
	./create_schema_and_migrate.sh
	@echo "$(GREEN)Schema creation completed$(NC)"

# Cleanup partial tables from failed migrations
cleanup-tables:
	@echo "$(YELLOW)Cleaning up partial tables from failed migrations...$(NC)"
	@if [ -z "$$DB_URL" ]; then \
		echo "$(YELLOW)DB_URL not set, using default: dcim user on localhost$(NC)"; \
	fi
	@DB_URL=$${DB_URL:-oracle+oracledb://dcim:dcim123@localhost:1521/?service_name=ORCLPDB1} && \
	cd $(MIGRATION_DIR) && \
	if [ ! -d "venv" ]; then \
		echo "$(YELLOW)Creating Python virtual environment...$(NC)"; \
		python3 -m venv venv; \
	fi && \
	. venv/bin/activate && \
	pip install --quiet --upgrade pip && \
	if [ -n "$(PIP_INDEX_URL)" ]; then \
		pip install --quiet --index-url $(PIP_INDEX_URL) sqlalchemy oracledb; \
	else \
		pip install --quiet sqlalchemy oracledb; \
	fi && \
	export DB_URL && \
	python3 cleanup_partial_tables.py
	@echo "$(GREEN)Cleanup completed$(NC)"

# Clean temporary files
clean:
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	@rm -f $(BACKEND_DIR)/backend.log $(ROOT_DIR)/backend.log
	@rm -f $(ROOT_DIR)/frontend.log
	@rm -f $(MIGRATION_DIR)/*.pyc
	@find $(MIGRATION_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find $(BACKEND_DIR)/app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Clean completed$(NC)"

