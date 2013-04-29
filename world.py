import igraph
from util import (SaveableMetaclass, LocationException,
                  ContainmentException, dictify_row)




class Portal(Item):
    # Portals would be called 'exits' if that didn't make it
    # perilously easy to exit the program by mistake. They link
    # one place to another. They are one-way; if you want two-way
    # travel, make another one in the other direction. Each portal
    # has a 'weight' that probably represents how far you have to
    # go to get to the other side; this can be zero. Portals are
    # likely to impose restrictions on what can go through them
    # and when. They might require some ritual to be performed
    # prior to becoming passable, e.g. opening a door before
    # walking through it. They might be diegetic, in which case
    # they point to a Thing that the player can interact with, but
    # the portal itself is not a Thing and does not require one.
    #
    # These are implemented as methods, although they
    # will quite often be constant values, because it's not much
    # more work and I expect that it'd cause headaches to be
    # unable to tell whether I'm dealing with a number or not.
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

    def pull_in_dimension(self, db, dimname):
        qryfmt = "SELECT {0} FROM portal WHERE dimension=?"
        qrystr = qryfmt.format(self.colnamestr["portal"])
        db.c.execute(qrystr, (dimname,))
        r = {dimname: {}}
        for row in db.c:
            rowdict = dictify_row(self.colnames["portal"], row)
            r[dimname][rowdict["name"]] = rowdict
        return r

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


class Dimension:
    tablenames = ["dimension"]
    coldecls = {"dimension":
                {"name": "text"}}
    primarykeys = {"dimension": ("name",)}

    def __init__(self, name, places, portals, things, db=None):
        self.name = name
        self.places = places
        self.portals = portals
        self.things = things
        if db is not None:
            db.dimensiondict[name] = self

    def get_edge(self, portal):
        origi = self.places.index(portal.orig)
        desti = self.places.index(portal.dest)
        return (origi, desti)

    def get_edges(self):
        return [self.get_edge(port) for port in self.portals]

    def get_edge_atts(self):
        return {}

    def get_vertex_atts(self):
        return {}

    def get_igraph_graph(self):
        return igraph.Graph(edges=self.get_edges(), directed=True,
                            vertex_attrs=self.get_vertex_atts(),
                            edge_attrs=self.get_edge_atts())

    def get_igraph_layout(self, layout_type):
        return self.get_igraph_graph().layout(layout=layout_type)


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

    def pull_in_dimension(self, db, dimname):
        qryfmt = "SELECT {0} FROM place WHERE dimension=?"
        qrystr = qryfmt.format(self.colnamestr["place"])
        db.c.execute(qrystr, (dimname,))
        return self.parse([
            dictify_row(self.cols, row) for row in db.c])

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
        self.unravelled = (
            isinstance(self.dimension, Dimension) and
            isinstance(self.location, Place) and
            isinstance(self.container, Thing))
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
        if self.container.unravelled:
            self.container.add(self)

    def pull_in_dimension(self, db, dimname):
        qryfmt = (
            "SELECT {0} FROM thing, thing_kind_link WHERE "
            "thing.dimension=thing_kind_link.dimension AND "
            "thing.name=thing_kind_link.thing AND "
            "dimension=?")
        thingcols = ["thing." + col for col in self.cols]
        allcols = self.cols + ["kind"]
        colstr = ", ".join(thingcols) + ", thing_kind_link.kind"
        qrystr = qryfmt.format(colstr)
        db.c.execute(qrystr, (dimname,))
        return self.parse([
            dictify_row(allcols, row) for row in db.c])

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


def pull_dimension(db, name):
    things = Thing.pull_in_dimension(db, name)
    places = Place.pull_in_dimension(db, name)
    portals = Portal.pull_in_dimension(db, name)
    journeys = Journey.pull_in_dimension(db, name)
    schedules = pull_schedules_in_dimension(db, name)
    things = Thing.combine(things, journeys, schedules)
    dimension = Dimension(name, places, portals, things, db)
    return dimension
