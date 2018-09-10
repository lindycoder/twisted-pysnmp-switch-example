import unittest

from flexmock import flexmock, flexmock_teardown
from mock import sentinel
from pyasn1.type.univ import OctetString, Integer
from pysnmp.proto.rfc1902 import ObjectName, ObjectSyntax, SimpleSyntax
from pysnmp.proto.rfc1905 import PDUs, ResponsePDU, VarBindList, VarBind, _BindValue, \
    NoSuchInstance

from snmp import service
from snmp.oid_store import OIDStore, UnknownOID, NoNextOID
from snmp.service import SnmpService, SNMP_ERR_genErr, SNMP_ERR_noSuchName
from test import CapturingMatcher, TraversableMessage

# snmpget -v2c -c community localhost:10610 .1.1
MSG_SNMP_GET = (b'0%\x02\x01\x01\x04\tcommunity\xa0\x15\x02\x04$=W\xfd\x02\x01\x00\x02\x01'
                b'\x000\x070\x05\x06\x01)\x05\x00')

# snmpset -v2c -c community localhost:10610 .1.1 i 5
MSG_SNMP_SET = (b'0&\x02\x01\x01\x04\tcommunity\xa3\x16\x02\x04ce\xd84\x02\x01\x00\x02\x01'
                b'\x000\x080\x06\x06\x01)\x02\x01\x05')

# snmpwalk -v2c -c community localhost:10610 .1.1
MSG_SNMP_WALK = (b'0%\x02\x01\x01\x04\tcommunity\xa1\x15\x02\x04!\xe521\x02\x01\x00\x02\x01'
                 b'\x000\x070\x05\x06\x01)\x05\x00')

# snmpbulkget -v2c -c community localhost:10610 1.1 1.2
MSG_SNMP_BULK_GET = (b"0,\x02\x01\x01\x04\tcommunity\xa5\x1c\x02\x04\'\x0c\xcfj\x02\x01"
                     b"\x00\x02\x01\n0\x0e0\x05\x06\x01)\x05\x000\x05\x06\x01*\x05\x00")

# snmpget -v2c -c wrong_community localhost:10610 .1.1
MSG_SNMP_WRONG_COMM = (b'0+\x02\x01\x01\x04\x0fwrong_community\xa0\x15\x02\x04d\xab\xdb\xcc\x02'
                       b'\x01\x00\x02\x01\x000\x070\x05\x06\x01)\x05\x00')


class SnmpServiceMessageReceivedTest(unittest.TestCase):
    def setUp(self):
        self.datastore = flexmock(OIDStore())
        self.service = SnmpService("ip", self.datastore, "community")

        self.capture_matcher = CapturingMatcher()
        self.transport_dispatcher = flexmock()
        self._mock_encoder()
        self.transport_dispatcher.should_receive("sendMessage")\
            .with_args(sentinel.encoded_message,
                       sentinel.transport_domain,
                       sentinel.transport_address)

    def tearDown(self):
        flexmock_teardown()

    def _mock_encoder(self):
        encoder = flexmock()
        flexmock(service).should_receive("encoder").and_return(encoder)
        encoder.should_receive("encode").with_args(self.capture_matcher) \
            .and_return(sentinel.encoded_message)

    def test_get(self):
        self.datastore.should_receive('get').with_args((1, 1)) \
            .and_return((1, 1), OctetString('test'))

        self.service.message_received(self.transport_dispatcher,
                                      sentinel.transport_domain,
                                      sentinel.transport_address,
                                      MSG_SNMP_GET)

        varbindlist = TraversableMessage(self.capture_matcher.obj)[PDUs][ResponsePDU][VarBindList]
        self.assertEqual(varbindlist[VarBind][ObjectName].value, (1, 1))
        self.assertEqual(
            varbindlist[VarBind][_BindValue][ObjectSyntax][SimpleSyntax][OctetString].value,
            OctetString("test"))

    def test_get_when_inexistent_oid_requested(self):
        self.datastore.should_receive('get').with_args((1, 1)).and_raise(UnknownOID((1, 1)))

        self.service.message_received(self.transport_dispatcher,
                                      sentinel.transport_domain,
                                      sentinel.transport_address,
                                      MSG_SNMP_GET)

        varbindlist = TraversableMessage(self.capture_matcher.obj)[PDUs][ResponsePDU][VarBindList]
        self.assertEqual(varbindlist[VarBind][ObjectName].value, (1, 1))
        self.assertEqual(varbindlist[VarBind][NoSuchInstance].value, NoSuchInstance())

    def test_set(self):
        self.datastore.should_receive('set').with_args((1, 1), Integer(5))

        self.service.message_received(self.transport_dispatcher,
                                      sentinel.transport_domain,
                                      sentinel.transport_address,
                                      MSG_SNMP_SET)

        varbindlist = TraversableMessage(self.capture_matcher.obj)[PDUs][ResponsePDU][VarBindList]
        self.assertEqual(varbindlist[VarBind][ObjectName].value, (1, 1))
        self.assertEqual(
            varbindlist[VarBind][_BindValue][ObjectSyntax][SimpleSyntax][Integer].value,
            Integer(5))

    def test_set_with_unknown_oid(self):
        self.datastore.should_receive('set').with_args((1, 1), Integer(5)) \
            .and_raise(UnknownOID((1, 1)))

        self.service.message_received(self.transport_dispatcher,
                                      sentinel.transport_domain,
                                      sentinel.transport_address,
                                      MSG_SNMP_SET)

        varbindlist = TraversableMessage(self.capture_matcher.obj)[PDUs][ResponsePDU][VarBindList]
        self.assertEqual(varbindlist[VarBind][ObjectName].value, (1, 1))
        self.assertEqual(varbindlist[VarBind][NoSuchInstance].value, NoSuchInstance())

    def test_get_next(self):
        self.datastore.should_receive('get_next').with_args((1, 1)).and_return((1, 2), Integer(5))

        self.service.message_received(self.transport_dispatcher,
                                      sentinel.transport_domain,
                                      sentinel.transport_address,
                                      MSG_SNMP_WALK)

        varbindlist = TraversableMessage(self.capture_matcher.obj)[PDUs][ResponsePDU][VarBindList]
        self.assertEqual(varbindlist[VarBind][ObjectName].value, (1, 2))
        self.assertEqual(
            varbindlist[VarBind][_BindValue][ObjectSyntax][SimpleSyntax][Integer].value,
            Integer(5))

    def test_get_next_when_inexistent_next_oid_requested(self):
        self.datastore.should_receive('get_next').with_args((1, 1)).and_raise(NoNextOID((1, 1)))

        self.service.message_received(self.transport_dispatcher,
                                      sentinel.transport_domain,
                                      sentinel.transport_address,
                                      MSG_SNMP_WALK)

        response_pdu = TraversableMessage(self.capture_matcher.obj)[PDUs][ResponsePDU]
        self.assertEqual(response_pdu.get_by_index(1).value, SNMP_ERR_noSuchName)

    def test_unsupported_command_returns_genError(self):
        self.service.message_received(self.transport_dispatcher,
                                      sentinel.transport_domain,
                                      sentinel.transport_address,
                                      MSG_SNMP_BULK_GET)

        self.assertEqual(TraversableMessage(self.capture_matcher.obj)[PDUs][ResponsePDU]
                         .get_by_index(1).value, Integer(SNMP_ERR_genErr))

    def test_wrong_community_gets_rejected(self):
        self.service.message_received(self.transport_dispatcher,
                                      sentinel.transport_domain,
                                      sentinel.transport_address,
                                      MSG_SNMP_WRONG_COMM)

        self.transport_dispatcher.should_receive("sendMessage").never()

