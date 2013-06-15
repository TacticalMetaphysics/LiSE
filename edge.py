from util import stringlike

class Edge:
    def __init__(self, db, dimension, portal):
        self.db = db
        self.dimension = dimension
        self.portal = portal
        self.vertlist = None
        self.oldstate = None
        dimname = str(self.dimension)
        portname = str(self.portal)
        self.db.edgedict[dimname][portname] = self

    def __str__(self):
        return str(self.portal)

    def __getattr__(self, attrn):
        if attrn == 'orig':
            return self.portal.orig.spot
        elif attrn == 'dest':
            return self.portal.dest.spot
        elif attrn == 'visible':
            return self.orig.visible or self.dest.visible
        else:
            raise AttributeError(
                "Edge instance has no attribute {0}".format(attrn))

    def unravel(self):
        if stringlike(self.dimension):
            self.dimension = self.db.dimensiondict[self.dimension]
        if stringlike(self.portal):
            self.portal = self.db[str(self.dimension)][self.portal]

    def get_state_tup(self):
        return (
            self.orig.window_x,
            self.orig.window_y,
            self.dest.window_x,
            self.dest.window_y)
