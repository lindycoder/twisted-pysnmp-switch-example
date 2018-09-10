class CapturingMatcher(object):
    def __init__(self):
        self.obj = None

    def __eq__(self, other):
        self.obj = other
        return True


def makeTraversable(component):
    if 'values' in dir(component):
        ret = TraversableMessage(component)
    else:
        ret = TraversableMessageStraight(component)
    return ret


class TraversableMessage(object):
    def __init__(self, other):
        self.value = other.values()

    def __getitem__(self, class_name):
        ret = None

        for component in self.value:
            if isinstance(component, class_name):
                if ret:
                    raise KeyError()
                ret = makeTraversable(component)
        return ret

    def get_by_index(self, index):
        return makeTraversable(list(self.value)[index])


class TraversableMessageStraight(TraversableMessage):
    def __init__(self, other):
        self.value = other
