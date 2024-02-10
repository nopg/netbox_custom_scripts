pull:
	scp nicnb:/opt/netbox/netbox/scripts/circuit_adder.py ./scripts/
	scp nicnb:/opt/netbox/netbox/reports/report_circuit_validations.py ./reports/
	scp nicnb:/opt/netbox/netbox/local/tests/test_circuit_adder.py ./local/tests/
	scp nicnb:/opt/netbox/netbox/local/utils.py ./local/
	scp nicnb:/opt/netbox/netbox/local/main.py ./local/
	scp nicnb:/opt/netbox/netbox/local/validators.py ./local/

push_csv_tests:
	scp test_csvs/csv_bulk_circuits_test.csv nicnb:/opt/netbox/netbox/local/tests/

initial_push:
	@echo "If you want to run 'make push': "
	@echo "   .py files can be blank/empty before 'make push'"
	@echo "   chmod 777 on all filenames in this repo (ignore __init__.py)"
	@echo " -------------------------------------------------------------"
	@echo " YOU NEED THIS STRUCTURE ON NETBOX HOST: "
	@echo "   /opt/netbox/netbox/local/__init__.py"
	@echo "   /opt/netbox/netbox/local/tests/__init__.py"
	@echo "   /opt/netbox/netbox/scripts/circuit_adder.py"
	@echo "   /opt/netbox/netbox/reports/report_circuit_validations.py"
	@echo "   /opt/netbox/netbox/local/tests/test_circuit_adder.py"
	@echo "   /opt/netbox/netbox/local/validators.py"
	@echo " -------------------------------------------------------------"
