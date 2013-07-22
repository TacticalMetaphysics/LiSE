from thing import (
    read_things_in_dimensions,
    read_schedules_in_dimensions,
    read_journeys_in_dimensions)
from place import read_places_in_dimensions
from portal import read_portals_in_dimensions
from util import DictValues2DIterator, SaveableMetaclass, dictify_row
from logging import getLogger

logger = getLogger(__name__)


"""Class and loaders for dimensions--the top of the world hierarchy."""


DIMENSION_QRYFMT = "INSERT INTO paths VALUES {0}"
PATH_ROW = "(?, ?, ?, ?, ?)"


class EdgeIterator:
    def __init__(self, portiter):
        self.portiter = portiter

    def __iter__(self):
        return self

    def next(self):
        p = self.portiter.next()
        return (p._orig, p._dest)


class Dimension:
    """Container for a given view on the game world, sharing no things,
places, or portals with any other dimension, but possibly sharing
characters."""
    __metaclass__ = SaveableMetaclass
    tables = [(
        "paths",
        {"dimension": "text not null",
         "origin": "integer not null",
         "destination": "integer not null",
         "i": "integer not null",
         "branch": "integer not null default 0",
         "tick_from": "integer not null default 0",
         "tick_to": "integer default null",
         "to_place": "integer not null"},
        ("dimension", "origin", "destination", "i", "branch", "tick_from"),
        {"dimension, origin": ("place", "dimension, i"),
         "dimension, destination": ("place", "dimension, i"),
         "dimension, to_place": ("place", "dimension, i")},
        ["origin<>destination", "i>=0"])]

    def __init__(self, db, name):
        """Return a dimension with the given name.

Probably useless unless, once you're sure you've put all your places,
portals, and things in the db, you call the Dimension object's unravel(db)
method. Thereafter, it will have dictionaries of all those items,
keyed with their names.

        """
        self.name = name
        db.dimensiondict[name] = self
        if name not in db.pathdestorigdict:
            db.pathdestorigdict[name] = {}
        if name not in db.placeidxdict:
            db.placeidxdict[name] = {}
        if name not in db.portalidxdict:
            db.portalidxdict[name] = {}
        self.db = db
        self.hiplace = 0
        self.hiport = 0

    def __getattr__(self, attrn):
        if attrn == 'graph':
            return self.db.get_igraph_graph(self.name)
        elif attrn == 'vs':
            return self.graph.vs
        elif attrn == 'es':
            return self.graph.es
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
        elif attrn == 'pathdestorigdict':
            return self.db.pathdestorigdict[self.name]
        elif attrn == 'paths':
            return DictValues2DIterator(self.pathdestorigdict)
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

    def get_tabdict(self):
        path_steps = []
        pathed_steps = set()
        for p in self.paths:
            path = list(p)
            try:
                desti = path[0]
                origi = path.pop()
                before = origi
                after = path.pop()
            except IndexError:
                continue
            i = 0
            while path != []:
                pt = (self.name, origi, desti, i, after)
                if pt in pathed_steps:
                    after = path.pop()
                    continue
                pathed_steps.add(pt)
                path_steps.append(
                    {
                        "dimension": self.name,
                        "origin": origi,
                        "destination": desti,
                        "i": i,
                        "to_place": after})
                before = after
                after = path.pop()
                i += 1
        return {"paths": path_steps}

    def index_places(self, places):
        for place in places:
            self.index_place(place)

    def index_place(self, place):
        if (
                place.i+1 > len(self.vs) or "name" not in
                self.vs[place.i].attributes() or
                self.vs[place.i]["name"] != str(place)):
            self.graph.add_vertices(1)
            place.i = len(self.vs) - 1
            self.graph.vs[place.i]["name"] = str(place)
            self.db.placeidxdict[self.name][place.i] = place

    def index_portals(self, portals):
        for portal in portals:
            self.index_portal(portal)

    def index_portal(self, portal):
        self.index_places([portal.orig, portal.dest])
        if (
                len(self.es) == 0 or
                portal.i+1 > len(self.es) or
                "name" not in self.es[portal.i].attributes() or
                self.es[portal.i]["name"] != str(portal)):
            self.graph.add_edges([(portal.orig.i, portal.dest.i)])
            portal.i = len(self.es) - 1
            self.graph.es[portal.i]["name"] = str(portal)
            self.db.portalidxdict[self.name][portal.i] = portal

    def shortest_path(self, orig, dest):
        # TODO hinting
        origi = orig.i
        desti = dest.i
        if desti not in self.pathdestorigdict:
            self.pathdestorigdict[desti] = {}
        if origi not in self.pathdestorigdict[desti]:
            paths = self.graph.get_shortest_paths(desti)
            for path in paths:
                if path == []:
                    continue
                path_origi = path[-1]
                logger.debug("hinting path from %d to %d",
                             path_origi, desti)
                self.pathdestorigdict[desti][path_origi] = path
        if origi in self.pathdestorigdict[desti]:
            return self.pathdestorigdict[desti][origi]
        else:
            return None

    def get_igraph_layout(self, layout_type):
        """Return a Graph layout, of the kind that igraph uses, representing
this dimension, and laid out nicely."""
        return self.graph.layout(layout=layout_type)

    def save(self):
        for place in self.places:
            place.save()
        for portal in self.portals:
            portal.save()
        for thing in self.things:
            thing.save()
        self.coresave()


PATH_DIMENSION_QRYFMT = (
    "SELECT {0} FROM paths WHERE dimension IN ({1})".format(
        ", ".join(Dimension.colns), "{0}"))


def read_paths_in_dimensions(db, names):
    qryfmt = PATH_DIMENSION_QRYFMT
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    qrytup = tuple(names)
    for name in names:
        if name not in db.pathdestorigdict:
            db.pathdestorigdict[name] = {}
    db.c.execute(qrystr, qrytup)
    for row in db.c:
        rowdict = dictify_row(row, Dimension.colns)
        pdod = db.pathdestorigdict[rowdict["dimension"]]
        orig = rowdict["origin"]
        dest = rowdict["destination"]
        topl = rowdict["to_place"]
        i = rowdict["i"]
        if dest not in pdod:
            pdod[dest] = {}
        if orig not in pdod[dest]:
            pdod[dest][orig] = []
        while len(pdod[dest][orig]) <= i:
            pdod[dest][orig].append(None)
        pdod[dest][orig][i] = topl


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
    read_paths_in_dimensions(db, names)
    r = {}
    for name in names:
        r[name] = Dimension(db, name)
    return r


def load_dimensions(db, names):
    r = read_dimensions(db, names)
    for dim in r.itervalues():
        dim.unravel()
    return r
