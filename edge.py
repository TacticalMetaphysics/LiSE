from util import stringlike

order = 0

class Edge:
    def __init__(self, db, dimension, portal):
        global order
        self.db = db
        self.dimension = dimension
        self.portal = portal
        self.vertlist = None
        self.wedge_a = None
        self.wedge_b = None
        self.oldstate = None
        self.order = order
        order += 2
    def __str__(self):
        return str(self.portal)

    def __getattr__(self, attrn):
        if attrn == 'orig':
            return self.portal.orig.spot
        elif attrn == 'dest':
            return self.portal.dest.spot
        else:
            raise AttributeError(
                "Edge instance has no attribute {0}".format(attrn))

    def unravel(self):
        if stringlike(self.dimension):
            self.dimension = self.db.dimensiondict[self.dimension]
        if stringlike(self.portal):
            self.portal = self.db[str(self.dimension)][self.portal]
        dimname = str(self.dimension)
        portname = str(self.portal)
        self.db.edgedict[dimname][portname] = self


    def get_state_tup(self):
        return self.orig.get_state_tup() + self.dest.get_state_tup()
