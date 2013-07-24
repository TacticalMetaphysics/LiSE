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
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "i": "integer not null default 0"},
         ("dimension", "from_place", "to_place", "branch", "tick_from"),
         # This schema relies on a trigger to create an appropriate
         # item record.
         {"dimension, from_place": ("place", "dimension, name"),
          "dimension, to_place": ("place", "dimension, name")},
         [])]

    def __init__(self, db, dimension, from_place, to_place):
        self._orig = str(from_place)
        self._dest = str(to_place)
        Item.__init__(self, db, dimension, str(self))
        w = self.db.get_world_state(branch, tick)
        d = w.dimensiondict[self._dimension]
        if str(self) in d["portal_by_i"]:
            i = d["portal_by_i"].index(str(self))
        else:
            i = len(d["portal_by_i"])
            d["portal_by_i"].append(str(self))
        if self._orig not in d["portal_by_orig_dest"]:
            d["portal_by_orig_dest"][self._orig] = {}
        d["portal_by_orig_dest"][self._dest] = i
        if self._dest not in d["portal_by_dest_orig"]:
            d["portal_by_dest_orig"][self._dest] = {}
        d["portal_by_dest_orig"][self._dest][self._orig] = i
        if self._dimension not in self.db.portaldict:
            self.db.portaldict[self._dimension] = {}
        self.db.portaldict[self._dimension][str(self)] = self
        

    def __str__(self):
        return 'Portal({0}->{1})'.format(self._orig, self._dest)

    def __int__(self):
        w = self.db.get_world_state()
        d = w.dimensiondict["portal_by_orig_dest"]
        return d[self._dimension][self._orig][self._dest]

    def __getattr__(self, attrn):
        if attrn == 'exists':
            w = self.db.get_world_state()
            d = w.dimensiondict[self._dimension]
            return (
                self._orig in d["portal_by_orig_dest"] and
                self._dest in d["portal_by_orig_dest"][self._orig])
        elif attrn == 'orig':
            return self.db.placedict[self._dimension][self._orig]
        elif attrn == 'dest':
            return self.db.placedict[self._dimension][self._dest]
        else:
            raise AttributeError("Portal has no such attribute")

    def unravel(self):
        pass

    def admits(self, traveler):
        """Return True if I want to let the given thing enter me, False
otherwise."""
        return True

    def touches(self, place):
        return self.orig == place or self.dest == place

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
