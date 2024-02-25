import sys

from extras.scripts import Script
from circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from dcim.models import Cable, Device, RearPort, FrontPort, Interface, RearPortTemplate, FrontPortTemplate, Site
from utilities.exceptions import AbortScript

from local import utils
from local.nice import NiceBulkCircuits, NiceStandardCircuit


def ct_checks(self):
	cts = CircuitTermination.objects.all()
	# ct = Circuit.objects.filter(cid="FRO2006510455GE FRO2006510466VRP")
	
	a = 0
	z = 0
	z_site = 0
	z_pn = 0
	a_site = 0
	a_pn = 0
	for obj in cts:
		if obj.term_side == 'A':
			z += 1
			if obj.site:
				a_site +=1
			if obj.provider_network:
				a_pn += 1
		if obj.term_side == 'Z':
			a += 1
			if obj.site:
				z_site +=1
			if obj.provider_network:
				z_pn += 1
	print(f"{a=}")
	print(f"{z=}")
	print(len(cts))
	print(f"{a_site=}")
	print(f"{a_pn=}")
	print(f"{z_site=}")
	print(f"{z_pn=}")
	self.log_info("HELLO")

def cable_checks():
	cables = []
	ccs = Circuit.objects.all()
	for c in ccs:
		if c.terminations.all():
			for term in c.terminations.all():
				cable = term.cable
				cables.append(cable)
	
	for c in cables:
		if c:
			if c.a_terminations:
				for a in c.a_terminations:
					print(f"side a: {type(a)}")
			if c.b_terminations:
				for b in c.b_terminations:
					print(f"side b: {type(b)}")

def term_types():
	cts = CircuitTermination.objects.all()
	for ct in cts:
		if ct.term_side == "Z":
			if ct.site:
				print(ct.circuit)
			# if ct.cable:
			# 	if ct.cable.a_terminations:
			# 		for a in ct.cable.a_terminations:
			# 			print(ct.circuit)
			# 			print(f"side a: {type(a)}")
			# 			print(ct.cable.id)
			# 	if ct.cable.b_terminations:
			# 		for b in ct.cable.b_terminations:
			# 			print(ct.circuit)
			# 			print(f"side b: {type(b)}")
			# 			print(ct.cable.id)

def rear_front_portnames():
	rears = RearPort.objects.all()
	fronts = FrontPort.objects.all()
	rear_templates = RearPortTemplate.objects.all()
	front_templates = FrontPortTemplate.objects.all()
	copper = 0
	sfp = 0
	lc = 0
	sc = 0
	for _type in (rears, fronts, rear_templates, front_templates):
		for obj in _type:
			if obj.type.upper() == "8P8C":
				copper +=1
			elif obj.type.upper() == "SFP":
				sfp +=1 
			elif obj.type.upper() == "LC":
				lc += 1
			elif obj.type.upper() == "SC":
				sc += 1
			else:
				print(obj.type)
			print(type(obj))
			print(obj.serialize_object())
	
	print(f"{copper=}, {sfp=}, {lc=}, {sc=}")

def pp_info():
	cts = CircuitTermination.objects.all()
	for ct in cts:
		if ct.pp_info:
			print(ct)
			print("\t", ct.pp_info)

def term_descrs():
	cts = CircuitTermination.objects.all()
	for ct in cts:
		if ct.description:
			print(ct.circuit.description)
			print(ct.description)
			print()

def my_test1(logger):
	myprovider = Provider.objects.get(name="myprovider1")
	myprovidernetwork = ProviderNetwork.objects.get(name="myprovidernetwork1")
	mytype = CircuitType.objects.get(name="mycircuittype1")
	mysite = Site.objects.get(name="mysite1")
	mypp = Device.objects.get(name="mypatchpanel1")
	mypp_port = RearPort.objects.get(name="Back1", device=mypp)
	mydevice = Device.objects.get(name="mydevice1")
	myinterface = Interface.objects.get(name="myinterface2", device=mydevice)
	data = {
		"cid": "my-test1-circuit",
		"description": "",
		"provider": myprovider,
		"circuit_type": mytype,
		"side_a_site": mysite,
		"side_z_providernetwork": myprovidernetwork,
		"pp": mypp,
		"pp_port": mypp_port,
		"device": mydevice,
		"interface": myinterface,
		"install_date": "2021-02-01",
		"termination_date": "2021-02-01",
		"cir": 0,
		"comments": "",
	}
	circuit = NiceStandardCircuit(logger, **data)
	circuit.create()

def my_test_bulk(logger):
	#filename = "local/tests/test_bulk_circuits.csv"	## Stuff doesn't exist in real DB
	#filename = "local/tests/gui_bulk_circuits_test.csv"
	filename = "local/tests/testing-gui_single_circuit.csv"
	#filename = "local/tests/test_bulk_circuits_malformed.csv"
	
	circuits = NiceBulkCircuits.from_csv(logger=logger, filename=filename, circuit_num=9)

	from rich.pretty import pprint
	pprint(circuits)

	for circuit in circuits:
		circuit.create()

def my_p2p_tests(logger):
	#filename = "local/tests/gui_bulk_circuits_test.csv"
	filename = "local/tests/testing-gui_single_circuit.csv"
	circuits = NiceBulkCircuits.from_csv(logger=logger, filename=filename, circuit_num=3)

	from rich.pretty import pprint
	pprint(circuits)

	for circuit in circuits:
		if isinstance(circuit, NiceStandardCircuit):
			print("no sir.")
			sys.exit()
		else:
			circuit.create()

def	my_pp_updater_tests(logger: Script):
	pp = Device.objects.get(name="mypatchpanel3")
	data = {
		"pp": pp,
		"old_frontport_name": "Front1",
		"new_frontport_name": "myFront 1",
		"old_rearport_name": "Back1",
		"new_rearport_name": "Rear1"
	}
	# data = {
	# 	"pp": pp,
	# 	"new_frontport_name": "Front1",
	# 	"old_frontport_name": "myFront 1",
	# 	"new_rearport_name": "Back1",
	# 	"old_rearport_name": "Rear1"
	# }
	_ = utils.pp_port_update(logger, **data)

def pp_port_descrs():
	rps = RearPort.objects.all()
	afps = FrontPort.objects.all()
	for rp in rps:
		if rp.description:
			print(f"rp: {rp},\trp-descr: {rp.description}")
			fps = rp.frontports.all()
			for fp in fps:
				print(f"myfp::--- {fp.description}")
	print("\n\n\n")
	for afp in afps:
		if afp.description:
			print(f"FP: {fp},\trp-descr: {fp.description}")
			print(f"myRp::--- {fp.rear_port.description}")

class Test(Script):
	class Meta:
		name = "misc tests"
		commit_default = False
		scheduling_enabled = False

	def run(self, data, commit=True):
		#ct_checks(self)
		#cable_checks()
		#term_types() 
		#rear_front_portnames()
		#pp_info()
		#term_descrs()
		#pp_port_descrs()
		#my_test1(self)
		
		my_test_bulk(logger=self)
		#my_p2p_tests(self)
		#my_pp_updater_tests(self)

