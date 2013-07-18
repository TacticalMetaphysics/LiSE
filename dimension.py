import igraph
from item import (
    read_things_in_dimensions,
    read_places_in_dimensions,
    read_portals_in_dimensions,
    read_schedules_in_dimensions,
    read_journeys_in_dimensions)
from util import DictValues2DIterator
from collections import OrderedDict
from logging import getLogger

logger = getLogger(__name__)


"""Class and loaders for dimensions--the top of the world hierarchy."""


class Dimension:
    """Container for a given view on the game world, sharing no things,
places, or portals with any other dimension, but possibly sharing
characters."""
    class EdgeIterator:
        def __init__(self, portiter):
            self.portiter = portiter
        def __iter__(self):
            return self
        def next(self):
            p = self.portiter.next()
            return (p._orig, p._dest)

    def __init__(self, db, name):
        """Return a dimension with the given name.

Probably useless unless, once you're sure you've put all your places,
portals, and things in the db, you call the Dimension object's unravel(db)
method. Thereafter, it will have dictionaries of all those items,
keyed with their names.

        """
        self.name = name
        db.dimensiondict[name] = self
        self.db = db
        self.hiplace = 0
        self.hiport = 0
        self.paths = {}

    def __getattr__(self, attrn):
        if attrn == 'graph':
            return self.db.get_igraph_graph(self.name)
        elif attrn == 'portals':
            return DictValues2DIterator(self.portalorigdestdict)
        elif attrn == 'itemdict':
            return self.db.itemdict[self.name]
        elif attrn == 'items':
            return self.itemdict.itervalues()
        elif attrn == 'thingdict':
            return self.db.thingdict[self.name]
        elif attrn == 'things':
            return self.thingdict.itervalues()
        elif attrn == 'placedict':
            return self.db.placedict[self.name]
        elif attrn == 'places':
            return self.placedict.itervalues()
        elif attrn == 'scheduledict':
            return self.db.scheduledict[self.name]
        elif attrn == 'schedules':
            return self.scheduledict.itervalues()
        elif attrn == 'journeydict':
            return self.db.journeydict[self.name]
        elif attrn == 'journeys':
            return self.journeydict.itervalues()
        elif attrn == 'portalorigdestdict':
            return self.db.portalorigdestdict[self.name]
        elif attrn == 'portaldestorigdict':
            return self.db.portaldestorigdict[self.name]
        elif attrn == 'edges':
            return EdgeIterator(self.portals)
        else:
            raise AttributeError(
                "Dimension instance has no attribute {0}.".format(attrn))

    def __hash__(self):
        """Return the hash of this dimension's name, since the database
constrains it to be unique."""
        return hash(self.name)

    def __str__(self):
        return self.name

    def unravel(self):
        """Get the dictionaries of the items in this dimension from the given
database. Then iterate over the values therein and unravel
everything."""
        db = self.db
        if self.name not in db.itemdict:
            db.itemdict[self.name] = {}
        if self.name not in db.thingdict:
            db.thingdict[self.name] = {}
        if self.name not in db.placedict:
            db.placedict[self.name] = {}
        if self.name not in db.scheduledict:
            db.scheduledict[self.name] = {}
        if self.name not in db.journeydict:
            db.journeydict[self.name] = {}
        if self.name not in db.portalorigdestdict:
            db.portalorigdestdict[self.name] = {}
        if self.name not in db.portaldestorigdict:
            db.portaldestorigdict[self.name] = {}
        # this order is deliberate
        for place in self.places:
            place.unravel()
        for portal in self.portals:
            portal.unravel()
        for journey in self.journeys:
            journey.unravel()
        for schedule in self.schedules:
            schedule.unravel()
        for thing in self.things:
            thing.unravel()

    def index_places(self, places):
        for place in places:
            if not hasattr(place, 'dimidx'):
                place.dimidx = {}
        n = len(places)
        # igraph graphs start with a single vertex in.
        self.graph.add_vertices(n - 1)
        old_hi = self.hiplace
        self.hiplace += n
        i = 0
        while old_hi + i < self.hiplace:
            self.graph.vs[old_hi + i]["name"] = str(places[i])
            places[i].dimidx[self.name] = old_hi + i
            i += 1

    def index_place(self, place):
        self.index_places([place])

    def index_portals(self, portals):
        self.paths = {}
        unindexed_places = set()
        for port in portals:
            if not hasattr(port, 'dimidx'):
                port.dimidx = {}
            for place in (port.orig, port.dest):
                if (
                        not hasattr(place, 'dimidx') or
                        self.name not in place.dimidx):
                    unindexed_places.add(place)
        if len(unindexed_places) > 0:
            self.index_places(tuple(unindexed_places))
        edges = []
        for port in portals:
            edges.append(
                (port.orig.dimidx[self.name],
                 port.dest.dimidx[self.name]))
        self.graph.add_edges(edges)
        n = len(portals)
        old_hi = self.hiport
        self.hiport += n
        i = 0
        while old_hi + i < self.hiport:
            self.graph.es[old_hi + i]["name"] = str(portals[i])
            portals[i].dimidx[self.name] = old_hi + 1
            i += 1

    def index_portal(self, portal):
        self.index_portals([portal])

    def shortest_path(self, orig, dest):
        # TODO hinting
        origi = orig.dimidx[self.name]
        desti = dest.dimidx[self.name]
        paths = self.graph.get_shortest_paths(desti)
        for path in paths:
            if path[-1] == origi:
                r = []
                for e in reversed(path):
                    r.append(self.graph.vs[e]["name"])
                return r
        return None

    def get_igraph_layout(self, layout_type):
        """Return a Graph layout, of the kind that igraph uses, representing
this dimension, and laid out nicely."""
        return self.graph.layout(layout=layout_type)


def read_dimensions(db, names):
    """Read in from disk the dimensions of the given names and everything
in them.

Objects will be instantiated to represent the lot, and a dictionary
thereof will be returned, but the objects won't be unraveled yet.

    """
    read_things_in_dimensions(db, names)
    read_places_in_dimensions(db, names)
    read_portals_in_dimensions(db, names)
    read_schedules_in_dimensions(db, names)
    read_journeys_in_dimensions(db, names)
    r = {}
    for name in names:
        r[name] = Dimension(db, name)
    return r


def load_dimensions(db, names):
    r = read_dimensions(db, names)
    for dim in r.itervalues():
        dim.unravel()
    return r
