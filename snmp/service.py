import logging

from pyasn1.codec.ber import encoder, decoder
from pysnmp.carrier.twisted.dgram import udp
from pysnmp.carrier.twisted.dispatch import TwistedDispatcher
from pysnmp.proto import api

from snmp.oid_store import UnknownOID, NoNextOID

LOG = logging.getLogger(__name__)
SNMP_ERR_noSuchName = 2
SNMP_ERR_genErr = 5

NO_SUCH_NAME_MESSAGE = "Returning noSuchName, ignoring exception"


class SnmpService(object):
    def __init__(self, ip, datastore, community, port=161, name="Untitled Switch", **_):
        self.ip = ip
        self.datastore = datastore
        self.community = community
        self.port = port
        self.name = name

    def message_received(self, transport_dispatcher, transport_domain, transport_address,
                         whole_message):
        while whole_message:
            message_version = api.decodeMessageVersion(whole_message)
            protocol = api.protoModules[message_version]

            request_message, whole_message = decoder.decode(whole_message,
                                                            asn1Spec=protocol.Message())
            request_pdu = protocol.apiMessage.getPDU(request_message)
            response_msg = protocol.apiMessage.getResponse(request_message)
            response_pdu = protocol.apiMessage.getPDU(response_msg)
            community = protocol.apiMessage.getCommunity(request_message)

            if not self._is_valid_community(community):
                break

            if request_pdu.isSameTypeWith(protocol.GetRequestPDU()):
                self._get_request(protocol, request_pdu, response_pdu)
            elif request_pdu.isSameTypeWith(protocol.GetNextRequestPDU()):
                self._get_next_request(protocol, request_pdu, response_pdu)
            elif request_pdu.isSameTypeWith(protocol.SetRequestPDU()):
                self._set_request(protocol, request_pdu, response_pdu)
            else:
                self._error(protocol, response_pdu)

            transport_dispatcher.sendMessage(
                    encoder.encode(response_msg), transport_domain, transport_address
            )
        return whole_message

    def _is_valid_community(self, community):
        return str(community) == self.community

    def _set_request(self, protocol, request_pdu, response_pdu):
        var_binds = []
        no_such_instance_index = []
        for oid, val in protocol.apiPDU.getVarBinds(request_pdu):
            try:
                self.datastore.set(oid, val)
            except UnknownOID:
                logging.exception(NO_SUCH_NAME_MESSAGE)
                no_such_instance_index.append(len(var_binds) + 1)
            var_binds.append((oid, val))

        protocol.apiPDU.setVarBinds(response_pdu, var_binds)
        for i in no_such_instance_index:
            protocol.apiPDU.setNoSuchInstanceError(response_pdu, i)

    def _get_next_request(self, protocol, request_pdu, response_pdu):
        var_binds = []
        for oid, val in protocol.apiPDU.getVarBinds(request_pdu):
            try:
                next_oid, value = self.datastore.get_next(oid)
                var_binds.append((next_oid, value))
            except NoNextOID:
                logging.exception(NO_SUCH_NAME_MESSAGE)
                protocol.apiPDU.setErrorStatus(response_pdu, SNMP_ERR_noSuchName)
        protocol.apiPDU.setVarBinds(response_pdu, var_binds)

    def _get_request(self, protocol, request_pdu, response_pdu):
        var_binds = []
        no_such_instance_index = []
        for oid, val in protocol.apiPDU.getVarBinds(request_pdu):
            value = None
            try:
                oid, value = self.datastore.get(oid)
            except UnknownOID:
                logging.exception(NO_SUCH_NAME_MESSAGE)
                no_such_instance_index.append(len(var_binds) + 1)
            var_binds.append((oid, value))

        protocol.apiPDU.setVarBinds(response_pdu, var_binds)
        for i in no_such_instance_index:
            protocol.apiPDU.setNoSuchInstanceError(response_pdu, i)

    def _error(self, protocol, response_pdu):
        protocol.apiPDU.setErrorStatus(response_pdu, SNMP_ERR_genErr)

    def hook_to_reactor(self):
        transport_dispatcher = TwistedDispatcher()

        transport_dispatcher.registerRecvCbFun(self.message_received)

        transport_dispatcher.registerTransport(
                udp.domainName, udp.UdpTwistedTransport().openServerMode((self.ip, self.port))
        )
        LOG.info("%s (SNMP): Registered on %s udp/%s with community %s",
                 self.name, self.ip, self.port, self.community)
