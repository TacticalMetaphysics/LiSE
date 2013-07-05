from util import stringlike

order = 0

class Edge:
    def __init__(self, db, dimension, portal):
        global order
        self.db = db
        self._dimension = str(dimension)
        self._portal = str(portal)
        self.vertlist = None
        self.wedge_a = None
        self.wedge_b = None
        self.oldstate = None
        self.order = order
        order += 2
    def __str__(self):
        return str(self.portal)

    def __getattr__(self, attrn):
        if attrn == "dimension":
            return self.db.dimensiondict[self._dimension]
        elif attrn == "portal":
            return self.db.itemdict[self._dimension][self._portal]
        elif attrn == 'orig':
            return self.portal.orig.spot
        elif attrn == 'dest':
            return self.portal.dest.spot
        else:
            raise AttributeError(
                "Edge instance has no attribute {0}".format(attrn))

    def unravel(self):
        dimname = str(self.dimension)
        portname = str(self.portal)
        self.db.edgedict[dimname][portname] = self


    def get_state_tup(self):
        return self.orig.get_state_tup() + self.dest.get_state_tup()
