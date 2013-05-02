from util import (
    SaveableMetaclass, dictify_row,
    LocationException, ContainmentException)
from pawn import Pawn
from schedule import Schedule


__metaclass__ = SaveableMetaclass


class Item:
    tablenames = ["item"]
    coldecls = {
        "item":
        {"dimension": "text",
         "name": "text"},
        "scheduled_event":
        {"dimension": "text",
         "item": "text",
         "start": "integer",
         "event": "text not null",
         "length": "integer"}}
    primarykeys = {
        "item": ("dimension", "name"),
        "scheduled_event": ("dimension", "item", "start")}
    foreignkeys = {
        "scheduled_event": {
            "dimension, item": ("item", "dimension, name"),
            "event": ("event", "name")}}


class Place(Item):
    tablenames = ["place"]
    coldecls = {"place":
                {"dimension": "text",
                 "name": "text"}}
    primarykeys = {"place": ("dimension", "name")}

    def __init__(self, dimension, name, db=None):
        self.dimension = dimension
        self.name = name
        if db is not None:
            if dimension not in db.itemdict:
                db.itemdict[dimension] = {}
            db.itemdict[dimension][name] = self

    def unravel(self, db):
        if isinstance(self.dimension, str):
            self.dimension = db.dimensiondict[self.dimension]

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name


class Thing(Item):
    tablenames = ["thing", "thing_kind", "thing_kind_link"]
    coldecls = {
        "thing":
        {"dimension": "text",
         "name": "text",
         "location": "text not null",
         "container": "text default null",
         "portal": "text default null",
         "progress": "float default 0.0",
         "age": "integer default 0"},
        "thing_kind":
        {"dimension": "text",
         "thing": "text",
         "kind": "text"},
        "journey_step":
        {"dimension": "text",
         "thing": "text",
         "idx": "integer",
         "portal": "text"}}
    primarykeys = {
        "thing": ("dimension", "name"),
        "journey_step": ("dimension", "thing", "idx"),
        "thing_kind": ("dimension", "thing", "kind")}
    foreignkeys = {
        "thing":
        {"dimension": ("dimension", "name"),
         "dimension, container": ("thing", "dimension, name")},
        "thing_kind":
        {"dimension": ("dimension", "name"),
         "thing": ("thing", "name"),
         "kind": ("thing_kind", "name")}}

    def __init__(self, dimension, name, location, container, kinds, db=None):
        self.dimension = dimension
        self.name = name
        self.location = location
        self.container = container
        self.kinds = kinds
        self.contents = set()
        if db is not None:
            dimname = None
            if isinstance(dimension, str):
                dimname = dimension
            else:
                dimname = dimension.name
            db.itemdict[dimname][self.name] = self

    def unravel(self, db):
        if isinstance(self.dimension, str):
            self.dimension = db.dimensiondict[self.dimension]
        if isinstance(self.location, str):
            self.location = db.itemdict[self.dimension.name][self.location]
            assert(isinstance(self.location, Place))
        if isinstance(self.container, str):
            self.container = db.itemdict[self.dimension.name][self.container]
            assert(isinstance(self.container, Thing))
        self.unravelled = True
        self.container.add(self)

    def __str__(self):
        return "(%s, %s)" % (self.dimension, self.name)

    def __iter__(self):
        return (self.dimension, self.name)

    def __repr__(self):
        if self.location is None:
            loc = "nowhere"
        else:
            loc = str(self.location)
        return self.name + "@" + loc

    def add(self, it):
        """Add an item to my contents without caring if it makes any sense to
do so.

This will not, for instance, remove the item from wherever it currently is.

"""
        self.contents.add(it)

    def remove(self, it):
        """Remove an item from my contents without putting it anywhere else.

The item might end up not being contained in anything, leaving it
inaccessible. Beware.

"""
        self.contents.remove(it)

    def can_enter(self, it):
        return True

    def can_contain(self, it):
        return True

    def enter(self, it):
        if isinstance(it, Place):
            self.enter_place(it)
        elif isinstance(it, Portal):
            self.enter_portal(it)
        elif isinstance(it, Thing):
            self.enter_thing(it)
        else:
            raise Exception("%s tried to enter %s, which is not enterable" %
                            (self.name, repr(it)))

    def enter_place(self, it):
        if self.can_enter(it) and it.can_contain(self):
            if self.container is None or self.container.location == it:
                self.location = it
                self.db.placecontentsdict[self.name] = it
            else:
                raise LocationException("%s tried to enter Place %s before "
                                        "its container %s did" %
                                        (self.name, it.name,
                                         self.container.name))
        else:
            raise LocationException("%s cannot enter Place %s" %
                                    (self.name, it.name))

    def enter_portal(self, it):
        if self.can_enter(it) and it.can_contain(self):
            self.container.remove(self)
            it.add(self)
        else:
            raise ContainmentException("%s cannot enter Portal %s" %
                                       (self.name, it.name))

    def enter_thing(self, it):
        if self.can_enter(it) and it.can_contain(self):
            self.container.remove(self)
            it.add(self)
        else:
            raise ContainmentException("%s cannot enter Thing %s" %
                                       (self.name, it.name))

    def speed_thru(self, port):
        """Given a portal, return a float representing how fast I can pass
through it.

Speed is equal to the reciprocal of the number of ticks of the
game-clock it takes to pass through the portal.

        """
        return 1/60.


class Portal(Item):
    tablenames = ["portal"]
    coldecls = {"portal":
                {"dimension": "text",
                 "name": "text",
                 "from_place": "text",
                 "to_place": "text"}}
    primarykeys = {"portal": ("dimension", "name")}
    foreignkeys = {"portal":
                   {"dimension, name": ("item", "dimension, name"),
                    "dimension, from_place": ("place", "dimension, name"),
                    "dimension, to_place": ("place", "dimension, name")}}

    def __init__(self, dimension, name, from_place, to_place, db=None):
        self.dimension = dimension
        self.name = name
        self.orig = from_place
        self.dest = to_place
        if db is not None:
            pd = db.itemdict
            podd = db.portalorigdestdict
            pdod = db.portaldestorigdict
            for d in [pd, podd, pdod]:
                if dimension not in d:
                    d[dimension] = {}
            if from_place not in podd:
                podd[dimension][from_place] = {}
            if to_place not in pdod:
                pdod[dimension][to_place] = {}
            pd[dimension][name] = self
            podd[dimension][from_place][to_place] = self
            pdod[dimension][to_place][from_place] = self

    def unravel(self, db):
        if isinstance(self.dimension, str):
            self.dimension = db.dimensiondict[self.dimension]
        if isinstance(self.orig, str):
            self.orig = db.itemdict[self.dimension.name][self.orig]
        if isinstance(self.dest, str):
            self.dest = db.itemdict[self.dimension.name][self.dest]

    def __hash__(self):
        return self.hsh

    def get_weight(self):
        return self.weight

    def get_avatar(self):
        return self.avatar

    def is_passable_now(self):
        return True

    def admits(self, traveler):
        return True

    def is_now_passable_by(self, traveler):
        return self.isPassableNow() and self.admits(traveler)

    def get_dest(self):
        return self.dest

    def get_orig(self):
        return self.orig

    def get_ends(self):
        return [self.orig, self.dest]

    def touches(self, place):
        return self.orig is place or self.dest is place

    def find_neighboring_portals(self):
        return self.orig.portals + self.dest.portals


thing_dimension_qryfmt = (
    "SELECT {0} FROM thing WHERE dimension IN "
    "({1})".format(
        ", ".join(Thing.colns), "{0}"))


schedule_item_qryfmt = (
    "SELECT {0} FROM scheduled_event WHERE "
    "(dimension, item) IN ({1})".format(
        ", ".join(Item.colnames["scheduled_event"]),
        "{0}"))


def read_schedules_in_item(db, dimitems):
    qmstr = ", ".join(["(?, ?)"] * len(dimitems))
    qryfmt = schedule_item_qryfmt
    qrystr = qryfmt.format(qmstr)
    flat = []
    for pair in dimitems:
        flat.extend(iter(pair))
    db.c.execute(qrystr, flat)
    r = {}
    for pair in dimitems:
        (dim, it) = pair
        r[dim] = {}
    for row in db.c:
        rowdict = dictify_row(row, Item.colnames["scheduled_event"])
        d = rowdict["dimension"]
        i = rowdict["item"]
        s = rowdict["start"]
        if i not in r[d]:
            r[d][i] = {}
        r[d][i][s] = rowdict
    return r


def read_things_in_dimensions(db, dimnames):
    qryfmt = thing_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    dim_thing_pairs = []
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Thing.colns)
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["name"]] = rowdict
        dim_thing_pairs.append((rowdict["dimension"], rowdict["name"]))
    s = read_schedules_in_things(db, dim_thing_pairs)
    for dimn in dimnames:
        rptr = r[dimn]
        sptr = s[dimn]
        for item in sptr.iteritems():
            (itemn, 
    j = read_journeys_in_things(db, dim_thing_pairs)

    for things in r.itervalues():
        for thing in things.itervalues():
            thing = Thing(**thing)
    return r


def unravel_things(db, tdb):
    for thing in tdb.itervalues():
        thing.unravel(db)
    return tdb


def unravel_things_in_dimensions(db, tddb):
    for things in tddb.itervalues():
        unravel_things(db, things)
    return tddb


def load_things_in_dimensions(db, dimnames):
    return unravel_things_in_dimensions(
        db, read_things_in_dimensions(db, dimnames))


place_dimension_qryfmt = (
    "SELECT {0} FROM place WHERE dimension IN "
    "({1})".format(
        ", ".join(Place.colns), "{0}"))


def read_places_in_dimensions(db, dimnames):
    qryfmt = place_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Place.colnames["place"])
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["name"]] = Place(**rowdict)
    return r


def unravel_places(db, pls):
    for pl in pls.itervalues():
        pl.unravel(db)
    return pls


def unravel_places_in_dimensions(db, pls):
    for pl in pls.itervalues():
        unravel_places(db, pl)
    return pls


def load_places_in_dimensions(db, dimnames):
    return unravel_places_in_dimensions(
        db, load_places_in_dimensions(db, dimnames))


portal_dimension_qryfmt = (
    "SELECT {0} FROM portal WHERE dimension IN "
    "({1})".format(
        ", ".join(Portal.colnames["portal"]), "{0}"))


def read_portals_in_dimensions(db, dimnames):
    qryfmt = portal_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for dimname in dimnames:
        r[dimname] = {}
    for row in db.c:
        rowdict = dictify_row(row, Portal.colnames["portal"])
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["name"]] = Portal(**rowdict)
    return r


def unravel_portals(db, portd):
    for port in portd.itervalues():
        port.unravel(db)
    return portd


def unravel_portals_in_dimensions(db, portdd):
    for ports in portdd.itervalues():
        unravel_portals(db, ports)
    return portdd


def load_portals_in_dimensions(db, dimnames):
    return unravel_portals_in_dimensions(
        db, read_portals_in_dimensions(db, dimnames))
