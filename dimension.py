from thing import Thing
from place import Place
from portal import Portal
from util import DictValues2DIterator, SaveableMetaclass, dictify_row
from logging import getLogger
from igraph import Graph

logger = getLogger(__name__)


"""Class and loaders for dimensions--the top of the world hierarchy."""

class Dimension:
    """Container for a given view on the game world, sharing no things,
places, or portals with any other dimension, but possibly sharing
characters."""
    __metaclass__ = SaveableMetaclass
    thing_loc_qry_start = "SELECT thing, branch, tick_from, tick_to, location FROM thing_location WHERE dimension=?"
    thing_speed_qry_start = "SELECT thing, branch, tick_from, tick_to, ticks_per_span FROM thing_speed WHERE dimension=?"
    port_qry_start = "SELECT origin, destination, branch, tick_from, tick_to FROM portal_existence WHERE dimension=?"
    tables = [(
        "dimension_paths",
        {"dimension": "text not null",
         "origin": "text not null",
         "destination": "text not null",
         "i": "integer not null",
         "branch": "integer not null default 0",
         "tick_from": "integer not null default 0",
         "tick_to": "integer default null",
         "to_place": "text not null"},
        ("dimension", "origin", "destination", "i", "branch", "tick_from"),
        {"dimension, origin": ("place", "dimension, name"),
         "dimension, destination": ("place", "dimension, name"),
         "dimension, to_place": ("place", "dimension, name")},
        ["origin<>destination", "i>=0"])]

    def __init__(self, db, name):
        """Return a dimension with the given name.

Probably useless unless, once you're sure you've put all your places,
portals, and things in the db, you call the Dimension object's unravel(db)
method. Thereafter, it will have dictionaries of all those items,
keyed with their names.

        """
        self.name = name
        self.db = db
        self.db.dimensiondict[str(self)] = self
        self.places = []
        self.places_by_name = {}
        self.portals = []
        self.portals_by_origi_desti = {}
        self.portals_by_orign_destn = {}
        self.things = []
        self.things_by_name = {}
        self.paths = {}
        self.graph = Graph(directed=True)

    def __hash__(self):
        """Return the hash of this dimension's name, since the database
constrains it to be unique."""
        return hash(self.name)

    def __str__(self):
        return self.name
 
    def get_igraph_layout(self, layout_type):
        """Return a Graph layout, of the kind that igraph uses, representing
this dimension, and laid out nicely."""
        return self.graph.layout(layout=layout_type)

    def save(self):
        for place in self.places:
            place.save()
        for port in self.portals:
            port.save()
        for thing in self.things:
            thing.save()
        self.coresave()

    def get_shortest_path(self, orig, dest, branch=None, tick=None):
        origi = int(orig)
        desti = int(dest)
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch in self.paths:
            for (tick_from, (pathdict, tick_to)) in self.paths[branch].iteritems():
                if tick_from <= tick and (tick_to is None or tick < tick_to):
                    if origi in pathdict and desti in pathdict[origi]:
                        return pathdict[origi][desti]
        else:
            self.paths[branch] = {}
        if tick not in self.paths[branch]:
            self.paths[branch][tick] = ({}, None)
        for path in self.graph.get_shortest_paths(desti):
            ifrom = path[-1]
            if ifrom not in self.paths[branch][tick][0]:
                self.paths[branch][tick][0][ifrom] = {}
            self.paths[branch][tick][0][ifrom][desti] = path
        return self.paths[branch][tick][0][origi][desti]

    def expire_shortest_path(self, orig, dest, branch, tick_from, tick_to=None):
        origi = int(orig)
        desti = int(dest)
        if tick_to is None:
            tick_to = self.db.tick
        self.paths[branch][tick_from][1] = tick_to

    def load(self, branches=None, tick_from=None, tick_to=None):
        branchexpr = ""
        tickfromexpr = ""
        ticktoexpr = ""
        if branches is not None:
            branchexpr = " AND branch IN ({0})".format(", ".join(["?"] * len(branches)))
        if tick_from is not None:
            tickfromexpr = " AND tick_from>=?"
        if tick_to is not None:
            ticktoexpr = " AND tick_to<=?"
        extrastr = "".join((branchexpr, tickfromexpr, ticktoexpr))
        qrystr = self.thing_loc_qry_start + extrastr
        valtup = tuple([str(self)] + [b for b in (branches, tickfrom, tick_to) if b is not None])
        self.db.c.execute(qrystr, valtup)
        for row in self.db.c:
            (thingn, branch, tick_from, tick_to, locn) = row
            if thingn not in self.things_by_name:
                self.things_by_name[thingn] = Thing(self, thingn)
            if locn not in self.place_by_name:
                pl = Place(self, locn)
                self.place_by_name[locn] = pl
                self.places.append(pl)
            self.things_by_name[thingn].set_location(
                self.place_by_name[locn], branch, tick_from, tick_to)
        qrystr = self.thing_speed_qry_start + extrastr
        self.db.c.execute(qrystr, valtup)
        for row in self.db.c:
            (thingn, branch, tick_from, tick_to, spd) = row
            if thingn not in self.things_by_name:
                # well, it isn't HERE, so it can't well go anywhere at any speed, can it
                continue
            self.things_by_name[thingn].set_speed(spd, branch, tick_from, tick_to)
        qrystr = self.port_qry_start + extrastr
        self.db.c.execute(qrystr, valtup)
        for row in self.db.c:
            (orign, destn, branch, tick_from, tick_to) = row
            if orign not in self.place_by_name:
                opl = Place(self, orign)
                self.place_by_name[orign] = opl
                self.places.append(opl)
            if destn not in self.place_by_name:
                dpl = Place(self, destn)
                self.place_by_name[destn] = dpl
                self.places.append(dpl)
            if orign not in self.portal_by_orign_destn:
                self.portal_by_orign_destn[orign] = {}
            po = Portal(self, opl, dpl)
            self.portal_by_orign_destn[orign][destn] = po
            self.portals.append(po)
        i = 0
        for place in self.places:
            place.i = i
            i += 1
        # Contrary to the tutorial, the graph starts out with vertex 0
        # already in it.
        self.graph.add_vertices(i)
        self.graph.vs["place"] = self.places
        i = 0
        edges = []
        for portal in self.portals:
            portal.i = i
            edges.append((portal.orig.i, portal.dest.i))
            i += 1
        self.graph.add_edges(edges)
        self.graph.es["portal"] = self.portals
