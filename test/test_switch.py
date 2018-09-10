import unittest

from hamcrest import assert_that, is_, has_items

from snmp.oid_store import is_a_descendant
from snmp.switch import SwitchOIDStore, switchIfDescr, switchCdpCacheDeviceId


class SwitchOIDStoreTest(unittest.TestCase):

    def test_every_port_has_the_appropriate_SNMP_values(self):
        switch = SwitchOIDStore(
            ports=[
                {'GigabitEthernet0/1': 'PS-T001-010.0'},
                {'GigabitEthernet0/2': 'PS-T001-020.0'},
                {'GigabitEthernet0/3': 'PS-T001-030.0'},
                {'GigabitEthernet0/4': 'PS-T001-040.0'},
                {'TenGigabitEthernet0/1': 'Uplink'}
            ])
        descriptions = []

        oid = switchIfDescr
        while True:
            oid, value = switch.get_next(oid)
            if is_a_descendant(oid, switchIfDescr):
                descriptions.append(value)
            else:
                break

        assert_that(
            descriptions,
            has_items(
                'GigabitEthernet0/1',
                'GigabitEthernet0/2',
                'GigabitEthernet0/3',
                'GigabitEthernet0/4',
                'TenGigabitEthernet0/1',
            )
        )

    def test_that_requesting_switchCdpCacheDeviceId_calls_request_device_id(self):

        def function_mock(name):
            return ('awesome', name)

        switch = SwitchOIDStore(
            ports=[{'GigabitEthernet0/1': 'PS-T001-010.0'}],
            device_id_for_name_hook=function_mock)

        oid, value = switch.get_next(switchCdpCacheDeviceId)

        assert_that(value, is_(('awesome', 'PS-T001-010.0')))
