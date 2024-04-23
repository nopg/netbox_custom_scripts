NETBOX_ROOT = /opt/netbox
PY_INIT_FILES = $(NETBOX_ROOT)/netbox/local/__init__.py $(NETBOX_ROOT)/netbox/scripts/__init__.py $(NETBOX_ROOT)/netbox/reports/__init__.py
MANUAL_UPGRADE := true

install:
	@echo ""
	@if [ "$(shell id -u)" -ne "0" ]; then \
		echo "Error: This command must be run as root."; \
		exit 1; \
	fi
	@mkdir -p $(NETBOX_ROOT)/netbox/scripts
	@mkdir -p $(NETBOX_ROOT)/netbox/reports
	@mkdir -p $(NETBOX_ROOT)/netbox/local/tests
	@echo "Created Directories"

	@for file in $(PY_INIT_FILES); do \
		if [ ! -e "$$file" ]; then \
			touch "$$file"; \
			echo "\tCreated $$file"; \
		fi \
	done
	@echo "Validated/Created __init__.py files"

	$(eval MANUAL_UPGRADE := false)
	@$(MAKE) --no-print-directory MANUAL_UPGRADE=false upgrade
	
	@echo "Updating Permissions.."
	@make -s update_permissions

	@echo ""
	@echo "Install Complete!"
	@echo "Make sure you update /netbox/local/display_fields.py with your bun_root_path!"
	@echo ""

upgrade:
	@if [ "$(shell id -u)" -ne "0" ]; then \
		echo "Error: This command must be run as root."; \
		exit 1; \
	fi
	
	@echo "Copying files.."
	@cp ./scripts/nice_circuit_scripts.py $(NETBOX_ROOT)/netbox/scripts/
	@cp ./reports/nice_reports.py $(NETBOX_ROOT)/netbox/reports/
	@cp ./local/tests/test_nice_circuit_scripts.py $(NETBOX_ROOT)/netbox/local/tests/
	@cp ./local/display_fields.py $(NETBOX_ROOT)/netbox/local/
	@cp ./local/nice_circuits.py $(NETBOX_ROOT)/netbox/local/
	@cp ./local/utils.py $(NETBOX_ROOT)/netbox/local/
	@cp ./local/validators.py $(NETBOX_ROOT)/netbox/local/
	@echo "Successfully copied files."

	@if [ "$(MANUAL_UPGRADE)" = "true" ]; then \
		echo "Updating Permissions.."; \
		make --no-print-directory update_permissions; \
		echo ""; \
		echo "Upgrade Complete!"; \
		echo "Make sure you update /netbox/local/display_fields.py with your bun_root_path!"; \
		echo ""; \
	fi 

update_permissions:
	@if [ "$(shell id -u)" -ne "0" ]; then \
		echo "Error: This command must be run as root."; \
		exit 1; \
	fi
	@chown --recursive netbox $(NETBOX_ROOT)/netbox/local
	@chown --recursive netbox $(NETBOX_ROOT)/netbox/scripts
	@chown --recursive netbox $(NETBOX_ROOT)/netbox/reports
