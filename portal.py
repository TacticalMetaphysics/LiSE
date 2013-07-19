from util import (
    dictify_row,
    DictValues2DIterator,
    SaveableMetaclass)
from item import Item
from logging import getLogger


logger = getLogger(__name__)


class Portal(Item):
    __metaclass__ = SaveableMetaclass
    tables = [
        ("portal",
         {"dimension": "text not null DEFAULT 'Physical'",
          "from_place": "text not null",
          "to_place": "text not null",
          "i": "integer not null default 0"},
         ("dimension", "from_place", "to_place"),
         # This schema relies on a trigger to create an appropriate
         # item record.
         {"dimension, from_place": ("place", "dimension, name"),
          "dimension, to_place": ("place", "dimension, name")},
         [])]

    def __init__(self, db, dimension, from_place, to_place, i):
        self._orig = from_place
        self._dest = to_place
        self.i = i
        name = "Portal({0}->{1})".format(
            str(from_place), str(to_place))
        Item.__init__(self, db, dimension, name)
        podd = db.portalorigdestdict
        pdod = db.portaldestorigdict
        for d in (db.itemdict, podd, pdod):
            if self._dimension not in d:
                d[self._dimension] = {}
        if self._orig not in podd[self._dimension]:
            podd[self._dimension][self._orig] = {}
        if self._dest not in pdod[self._dimension]:
            pdod[self._dimension][self._dest] = {}
        podd[self._dimension][self._orig][self._dest] = self
        pdod[self._dimension][self._dest][self._orig] = self
        self.dimension.index_portal(self)

    def __str__(self):
        return 'Portal({0}->{1})'.format(str(self.orig), str(self.dest))

    def __getattr__(self, attrn):
        if attrn == "spot":
            return self.dest.spot
        elif attrn == "orig":
            return self.db.placedict[self._dimension][self._orig]
        elif attrn == "dest":
            return self.db.placedict[self._dimension][self._dest]
        elif attrn == "edge":
            return self.db.edgedict[self._dimension][str(self)]
        elif attrn == "dimension":
            return self.db.get_dimension(self._dimension)
        elif attrn == "reciprocal":
            return self.db.portaldestorigdict[
                self._dimension][self._orig][self._dest]
        else:
            raise AttributeError("Portal has no such attribute")

    def unravel(self):
        pass

    def get_tabdict(self):
        return {
            "portal": {
                "dimension": self._dimension,
                "from_place": self._orig,
                "to_place": self._dest,
                "i": self.i}}

    def delete(self):
        del self.db.portalorigdestdict[self._dimension][self._orig][self._dest]
        del self.db.portaldestorigdict[self._dimension][self._dest][self._orig]
        Item.delete(self)

    def admits(self, traveler):
        """Return True if I want to let the given thing enter me, False
otherwise."""
        return True

    def touches(self, place):
        return self.orig is place or self.dest is place

    def find_neighboring_portals(self):
        return self.orig.portals + self.dest.portals

    def notify_moving(self, thing, amount):
        """Handler for when a thing moves through me by some amount of my
length. Does nothing by default."""
        pass


portal_colstr = ", ".join(Portal.colnames["portal"])
portal_dimension_qryfmt = (
    "SELECT {0} FROM portal WHERE dimension IN "
    "({1})".format(portal_colstr, "{0}"))


def read_portals_in_dimensions(db, dimnames):
    """Read and instantiate, but do not unravel, all portals in the given
dimensions.

Return them in a 2D dict keyed by dimension name, then portal name.

    """
    qryfmt = portal_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for dimname in dimnames:
        r[dimname] = {}
    for row in db.c:
        rowdict = dictify_row(row, Portal.colnames["portal"])
        rowdict["db"] = db
        orig = rowdict["from_place"]
        dest = rowdict["to_place"]
        dim = rowdict["dimension"]
        if orig not in r[dim]:
            r[dim][orig] = {}
        r[dim][orig][dest] = Portal(**rowdict)
    for dimname in dimnames:
        dimension = db.get_dimension(dimname)
        ports = [port for port in DictValues2DIterator(r[dimname])]
        dimension.index_portals(ports)
    return r


def load_portals_in_dimensions(db, dimnames):
    r = read_portals_in_dimensions(db, dimnames)
    for origin in r.itervalues():
        for destination in origin.itervalues():
            for portal in destination.itervalues():
                portal.unravel()
    return r
