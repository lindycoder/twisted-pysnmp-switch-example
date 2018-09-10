class UnknownOID(Exception):
    def __init__(self, oid, msg="OID {} was not found"):
        super(UnknownOID, self).__init__(msg.format(oid))


class NoNextOID(Exception):
    def __init__(self, oid, msg="No OID was found after {}"):
        super(NoNextOID, self).__init__(msg.format(oid))


class OIDStore(object):
    def __init__(self, oids=None):
        self.oids = oids or {}

    def get(self, oid):
        try:
            value = self._handle_callable_value(oid, self.oids[oid])
            return oid, value
        except KeyError:
            raise UnknownOID(oid)

    def get_next(self, oid):
        set_oid = set(self.oids.keys())
        set_oid.add(oid)
        sorted_oids = sorted(set_oid)
        index = sorted_oids.index(oid)
        try:
            next_oid = sorted_oids[index+1]
        except IndexError:
            raise NoNextOID(oid)
        return self.get(next_oid)

    def set(self, oid, value):
        if oid not in self.oids:
            raise UnknownOID(oid)

        self.oids[oid] = value

    def _handle_callable_value(self, oid, value):
        if callable(value):
            return value(oid, self)
        return value


def is_a_descendant_or_same(oid, ancestor):
    return oid[:len(ancestor)] == ancestor


def is_a_descendant(oid, ancestor):
    return oid != ancestor and is_a_descendant_or_same(oid, ancestor)
