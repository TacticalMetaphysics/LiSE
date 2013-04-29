from util import (
    SaveableMetaclass, dictify_row,
    LocationException, ContainmentException)


__metaclass__ = SaveableMetaclass


class Item:
    tablenames = ["item"]
    coldecls = {
        "item":
        {"dimension": "text",
         "name": "text"}}
    primarykeys = {
        "item": ("dimension", "name")}


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
        self.dimension = db.dimensiondict[self.dimension]

    def parse(self, rows):
        r = {}
        for row in rows:
            if row["dimension"] not in r:
                r[row["dimension"]] = {}
            r[row["dimension"]][row["name"]] = row
        return r

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
         "location": "text",
         "container": "text"},
        "thing_kind":
        {"name": "text"},
        "thing_kind_link":
        {"dimension": "text",
         "thing": "text",
         "kind": "text"}}
    primarykeys = {
        "thing": ("dimension", "name"),
        "location": ("dimension", "thing"),
        "thing_kind": ("name",),
        "thing_kind_link": ("thing", "kind")}
    foreignkeys = {
        "thing":
        {"dimension": ("dimension", "name"),
         "dimension, container": ("thing", "dimension, name")},
        "thing_kind_link":
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
        self.dimension = db.dimensiondict[self.dimension]
        self.location = db.itemdict[self.dimension.name][self.location]
        self.container = db.itemdict[self.dimension.name][self.container]
        self.unravelled = True
        if hasattr(self.container, 'unravelled'):
            self.container.add(self)

    def parse(self, rows):
        tabdict = {}
        for row in rows:
            if row["dimension"] not in tabdict:
                tabdict[row["dimension"]] = {}
            if row["name"] not in tabdict[row["dimension"]]:
                tabdict[row["dimension"]][row["name"]] = {
                    "dimension": row["dimension"],
                    "name": row["name"],
                    "kinds": []}
            ptr = tabdict[row["dimension"]][row["name"]]
            ptr["kinds"].append(row["kinds"])
        return tabdict

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
                podd[from_place] = {}
            if to_place not in pdod:
                pdod[to_place] = {}
            pd[dimension][name] = self
            podd[dimension][from_place][to_place] = self
            pdod[dimension][to_place][from_place] = self

    def unravel(self, db):
        self.dimension = db.dimensiondict[self.dimension]
        self.orig = db.itemdict[self.dimension.name][self.orig]
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


def pull_things_in_dimension(db, dimname):
    qryfmt = (
        "SELECT {0} FROM thing WHERE "
        "dimension=?")
    colstr = ", ".join(Thing.colnames["thing"])
    qrystr = qryfmt.format(colstr)
    db.c.execute(qrystr, (dimname,))
    r = {}
    rows = [
        dictify_row(row, Thing.colnames["thing"])
        for row in db.c]
    for row in rows:
        r[row["name"]] = row
    return r


def pull_places_in_dimension(db, dimname):
    qryfmt = "SELECT {0} FROM place WHERE dimension=?"
    qrystr = qryfmt.format(Place.colnamestr["place"])
    db.c.execute(qrystr, (dimname,))
    rows = [
        dictify_row(row, Place.colnames["place"])
        for row in db.c]
    r = {}
    for row in rows:
        r[row["name"]] = row
    return r


def pull_portals_in_dimension(db, dimname):
    qryfmt = "SELECT {0} FROM portal WHERE dimension=?"
    qrystr = qryfmt.format(Portal.colnamestr["portal"])
    db.c.execute(qrystr, (dimname,))
    r = {}
    for row in db.c:
        rowdict = dictify_row(row, Portal.colnames["portal"])
        r[rowdict["name"]] = rowdict
    return r


def combine_things(things, journeys, schedules):
    for item in journeys.iteritems():
        (dimension, journey2) = item
        if dimension in things:
            for item2 in journey2.iteritems():
                (thing, journey3) = item2
                if thing in things[dimension]:
                    things[dimension][thing]["journey"] = journey3
    for item in schedules.iteritems():
        (dimension, schedule2) = item
        if dimension in things:
            for item2 in schedule2.iteritems():
                (thing, schedule3) = item2
                if thing in things[dimension]:
                    things[dimension][thing]["schedule"] = schedule3
    return things
