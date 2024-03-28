pull:
	scp nicnb:/opt/netbox/netbox/scripts/nice_circuit_scripts.py ./scripts/
	scp nicnb:/opt/netbox/netbox/reports/nice_reports.py ./reports/
	scp nicnb:/opt/netbox/netbox/local/tests/test_nice_circuit_scripts.py ./local/tests/
	scp nicnb:/opt/netbox/netbox/local/display_fields.py ./local/
	scp nicnb:/opt/netbox/netbox/local/nice_circuits.py ./local/
	scp nicnb:/opt/netbox/netbox/local/utils.py ./local/
	scp nicnb:/opt/netbox/netbox/local/validators.py ./local/

	scp nicnb:/opt/netbox/netbox/scripts/testing.py ./runscript-testing/

push_csv_tests:
	scp ./local/tests/test_bulk_circuits.csv nicnb:/opt/netbox/netbox/local/tests/
	scp ./local/tests/test_bulk_circuits_fail.csv nicnb:/opt/netbox/netbox/local/tests/
	scp runscript-testing/csv-runscript-circuits.csv nicnb:/opt/netbox/netbox/local/tests/

remember:
	@echo "If you want to run 'make push': "
	@echo "   .py files can be blank/empty before 'make push'"
	@echo "   chown netbox on all filenames in this repo "
	@echo " -------------------------------------------------------------"
	@echo " YOU NEED THIS STRUCTURE ON NETBOX HOST: "
	@echo "   /opt/netbox/netbox/local/__init__.py"
	@echo "   /opt/netbox/netbox/local/tests/__init__.py"
	@echo "   /opt/netbox/netbox/scripts/nice_circuit_scripts.py"
	@echo "   /opt/netbox/netbox/reports/nice_reports.py"
	@echo "   /opt/netbox/netbox/local/tests/test_nice_circuit_scripts.py"
	@echo "   /opt/netbox/netbox/local/display_fields.py"
	@echo "   /opt/netbox/netbox/local/nice_circuits.py"
	@echo "   /opt/netbox/netbox/local/utils.py"
	@echo "   /opt/netbox/netbox/local/validators.py"
	@echo " -------------------------------------------------------------"
	@echo " Change to test config	export NETBOX_CONFIGURATION=netbox.configuration_testing "
	@echo " Ensure db permissions	ALTER DATABASE netbox OWNER TO netbox; "
	@echo " 			ALTER USER netbox CREATEDB; "
	@echo " Run Test		./manage.py test local.tests --keepdb -v 2 "
