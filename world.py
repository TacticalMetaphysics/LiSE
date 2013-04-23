import igraph
from util import (SaveableMetaclass, LocationException,
                  ContainmentException, Item, dictify_row)


__metaclass__ = SaveableMetaclass


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

    def setup(self):
        rowdict = self.tabdict["portal"][0]
        from_place = rowdict["from_place"]
        to_place = rowdict["to_place"]
        pd = self.db.placedict
        self.orig = pd[self.dimension.name][from_place]
        self.dest = pd[self.dimension.name][to_place]
        self.db.portaldict[self.dimension.name][self.name] = self
        podd = self.db.portalorigdestdict[self.dimension.name]
        pdod = self.db.portaldestorigdict[self.dimension.name]
        podd[self.orig.name] = self.dest
        pdod[self.dest.name] = self.orig

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


class Item:
    coldecls = {
        "item":
        {"dimension": "text",
         "name": "text"}}
    primarykeys = {
        "item": ("dimension", "name")}


class Dimension:
    coldecls = {"dimension":
                {"name": "text"}}
    primarykeys = {"dimension": ("name",)}

    def pull(self, db, tabdict):
        qryfmt = "SELECT %s FROM %s WHERE dimension IN (%s)"
        dimnames = [rowdict["name"] for rowdict in tabdict["dimension"]]
        qrystr = qryfmt % (Place.colnames["place"], "place", dimnames)
        qrytup = tuple(dimnames)
        db.c.execute(qrystr, qrytup)
        tabdict["place"] = [
            dictify_row(Place.colnames["place"], row)
            for row in db.c]
        qrystr = qryfmt % (Portal.colnames["portal"], "portal", dimnames)
        db.c.execute(qrystr, qrytup)
        tabdict["portal"] = [
            dictify_row(Portal.colnames["portal"], row)
            for row in db.c]
        qrystr = qryfmt % (Thing.colnames["thing"], "thing", dimnames)
        db.c.execute(qrystr, qrytup)
        tabdict["thing"] = [
            dictify_row(Thing.colnames["thing"], row)
            for row in db.c]
        qrystr = qryfmt % (Journey.colnames["journey"], "journey", dimnames)
        db.c.execute(qrystr, qrytup)
        tabdict["journey"] = [
            dictify_row(Journey.colnames["journey"], row)
            for row in db.c]
        for clas in [Place, Portal, Thing, Journey]:
            tabdict.update(clas.pull(db, tabdict))
        return tabdict

    def setup(self):
        rowdict = self.tabdict["dimension"][0]
        db = self.db
        self.name = rowdict["name"]
        self.placedict = self.db.placedict[self.name]
        self.portaldict = self.db.portaldict[self.name]
        self.thingdict = self.db.thingdict[self.name]
        self.journeydict = self.db.journeydict[self.name]
        db.dimensiondict[self.name] = self

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
    coldecls = {"place":
                {"dimension": "text",
                 "name": "text"}}
    primarykeys = {"place": ("dimension", "name")}

    def setup(self):
        rowdict = self.tabdict["place"][0]
        db = self.db
        dimname = rowdict["dimension"]
        self.name = rowdict["name"]
        self.dimension = db.dimensiondict[dimname]
        pcd = self.db.placecontentsdict
        podd = self.db.portalorigdestdict
        self.contents = pcd[dimname][self.name]
        self.portals = podd[dimname][self.name]
        self.db.placedict[dimname][self.name] = self

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name


class Thing(Item):
    coldecls = {"thing":
                {"dimension": "text",
                 "name": "text",
                 "location": "text"},
                "containment":
                {"dimension": "text",
                 "contained": "text",
                 "container": "text"},
                "thing_kind":
                {"name": "text"},
                "thing_kind_link":
                {"dimension": "text",
                 "thing": "text",
                 "kind": "text"}}
    primarykeys = {"thing": ("dimension", "name"),
                   "location": ("dimension", "thing"),
                   "containment": ("dimension", "contained"),
                   "thing_kind": ("name",),
                   "thing_kind_link": ("thing", "kind")}
    foreignkeys = {"thing":
                   {"dimension": ("dimension", "name")},
                   "containment":
                   {"dimension": ("dimension", "name"),
                    "dimension, contained": ("thing", "dimension, name"),
                    "dimension, container": ("thing", "dimension, name")},
                   "thing_kind_link":
                   {"dimension": ("dimension", "name"),
                    "thing": ("thing", "name"),
                    "kind": ("thing_kind", "name")}}
    checks = {"containment": ["contained<>container"]}

    def setup(self):
        Item.setup(self)
        rowdict = self.tabdict["thing"][0]
        locname = rowdict["location"]
        dimname = self.dimension.name
        db = self.db
        self.location = db.placedict[dimname][locname]
        db.thingdict[dimname][self.name] = self
        if self.name in db.contentsdict[dimname]:
            self.contents = db.contentsdict[dimname][self.name]
            for contained in self.contents:
                db.containerdict[dimname][contained.name] = self
        else:
            self.contents = []
            db.contentsdict[dimname][self.name] = self.contents
        if self.name in db.containerdict[dimname]:
            self.container = db.containerdict[dimname]
        else:
            self.container = None

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
