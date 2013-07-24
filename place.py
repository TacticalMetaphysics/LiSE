from item import Item
from util import dictify_row, SaveableMetaclass
import re


__metaclass__ = SaveableMetaclass


class PlaceContentsIter:
    def __init__(self, place, branch=None, tick=None):
        self.db = place.db
        self.place_s = str(place)
        self.dimension_s = place._dimension
        self.branch = branch
        self.tick = tick
        self.locdictiter = self.db.get_world_state(
            self.branch, self.tick).dimensiondict[
                self.dimension_s]["thing_loc"].iteritems()

    def __iter__(self):
        return self

    def next(self):
        (thing_s, loc_s) = (None, None)
        while loc_s != self.place_s:
            (thing_s, loc_s) = self.locdictiter.next()
        return self.place.db.thingdict[self.place._dimension][thing_s]


class PortalOrigIter:
    portfmt = "Portal({0}->{1})"
    def __init__(self, place, branch=None, tick=None):
        self.db = place.db
        self.place_s = str(place)
        self.dimension_s = place._dimension
        self.branch = branch
        self.tick = tick
        self.portorigiter = self.db.get_world_state(
            self.branch, self.tick).dimensiondict[
                self.dimension_s]["portal_by_orig_dest"][
                    self.place_s].iterkeys()

    def __iter__(self):
        return self

    def next(self):
        dest_s = self.portorigiter.next()
        port_s = self.portfmt.format(self.place_s, dest_s)
        return self.db.portaldict[self.dimension_s][port_s]


class Place(Item):
    """The 'top level' of the world model. Places contain Things and are
connected to other Places, forming a graph."""
    tables = [
        ("place",
         {"dimension": "text not null DEFAULT 'Physical'",
          "name": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "i": "integer not null default 0"},
         ("dimension", "name", "branch", "tick_from"),
         {},
         [])]

    def __init__(self, db, dimension, name)
        """Return a Place of the given name, in the given dimension. Register
it with the placedict and itemdict in the db."""
        Item.__init__(self, db, dimension, name)
        if self._dimension not in self.db.placedict:
            self.db.placedict[self._dimension] = {}
        self.db.placedict[self._dimension][str(self)] = self

    def __str__(self):
        return self.name

    def __int__(self):
        w = self.db.get_world_state()
        d = w.dimensiondict[self._dimension]["place_by_name"]
        return d[str(self)]

    def __getattr__(self, attrn):
        if attrn == 'spot':
            return self.db.spotdict[self._dimension][self.name]
        elif attrn == 'contents':
            return PlaceContentsIter(self)
        elif attrn == 'portals':
            return PortalOrigIter(self)
        else:
            try:
                return Item.__getattr__(self, attrn)
            except AttributeError:
                raise AttributeError("Place instance has no attribute " + attrn)

    def unravel(self):
        pass

    def can_contain(self, other):
        """Does it make sense for that to be here?"""
        return True

    def get_tabdict(self):
        return {
            "place": {
                "dimension": self._dimension,
                "name": self.name,
                "i": self.i}}


place_dimension_qryfmt = (
    "SELECT {0} FROM place WHERE dimension IN "
    "({1})".format(
        ", ".join(Place.colns), "{0}"))


generic_place_re = re.compile("Place_([0-9])+")


def read_places_in_dimensions(db, dimnames):
    """Read and instantiate, but do not unravel, all places in the given
dimensions.

Return them in a 2D dict keyed by dimension name, then place name.

    """
    qryfmt = place_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Place.colnames["place"])
        rowdict["db"] = db
        m = re.match(generic_place_re, rowdict["name"])
        if m is not None:
            num = int(m.groups()[0])
            if num > db.hi_place:
                db.hi_place = num
        r[rowdict["dimension"]][rowdict["name"]] = Place(**rowdict)
    for dimname in dimnames:
        dimension = db.get_dimension(dimname)
        dimension.index_places(r[dimname].itervalues())
    return r


def unravel_places(pls):
    """Unravel places in a dict keyed by their names.

Return the same dict."""
    for pl in pls.itervalues():
        pl.unravel()
    return pls


def unravel_places_in_dimensions(pls):
    """Unravel places previously read in by read_places or
read_places_in_dimensions."""
    for pl in pls.itervalues():
        unravel_places(pl)
    return pls


def load_places_in_dimensions(db, dimnames):
    """Load all places in the given dimensions.

Return them in a 2D dict keyed by the dimension name, then the place
name.

    """
    return unravel_places_in_dimensions(
        load_places_in_dimensions(db, dimnames))
