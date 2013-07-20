from item import Item
from util import dictify_row, SaveableMetaclass
import re


__metaclass__ = SaveableMetaclass


class Place(Item):
    """The 'top level' of the world model. Places contain Things and are
connected to other Places, forming a graph."""
    tables = [
        ("place",
         {"dimension": "text not null DEFAULT 'Physical'",
          "name": "text not null",
          "i": "integer not null default 0"},
         ("dimension", "name"),
         {},
         [])]

    def __init__(self, db, dimension, name, i):
        """Return a Place of the given name, in the given dimension. Register
it with the placedict and itemdict in the db."""
        Item.__init__(self, db, dimension, name)
        self.i = i
        if self._dimension not in db.placedict:
            db.placedict[self._dimension] = {}
        if self._dimension not in db.contentsdict:
            db.contentsdict[self._dimension] = {}
        if self.name not in db.contentsdict[self._dimension]:
            db.contentsdict[self._dimension][self.name] = set()
        db.placedict[self._dimension][self.name] = self
        self.dimension.index_place(self)

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __getattr__(self, attrn):
        if attrn == 'spot':
            return self.db.spotdict[self._dimension][self.name]
        elif attrn == 'contents':
            return self.db.contentsdict[self._dimension][self.name]
        else:
            return Item.__getattr__(self, attrn)

    def __setattr__(self, attrn, val):
        if (
                attrn == "i" and hasattr(self, 'i') and
                self._dimension in self.db.placeidxdict and
                val in self.db.placeidxdict[self._dimension]):
            del self.db.placeidxdict[self._dimension][self.i]
            self.db.placeidxdict[self._dimension][val] = self
        super(Place, self).__setattr__(attrn, val)

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

    def delete(self):
        del self.db.placedict[self._dimension][self.name]
        Item.delete(self)


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
