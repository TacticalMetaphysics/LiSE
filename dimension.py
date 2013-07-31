from thing import Thing
from place import Place
from portal import Portal
from spot import Spot
from board import Board
from pawn import Pawn
from img import Img
from arrow import Arrow
from logging import getLogger
from igraph import Graph
from collections import OrderedDict
from util import DictValues2DIterator

logger = getLogger(__name__)


"""Class and loaders for dimensions--the top of the world hierarchy."""


class Dimension:
    """Container for a given view on the game world, sharing no things,
places, or portals with any other dimension, but possibly sharing
characters."""
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
        self.places_by_name = OrderedDict()
        self.portals_by_orign_destn = OrderedDict()
        self.things_by_name = {}
        self.boards = []
        self.graph = Graph(directed=True)

    def __hash__(self):
        """Return the hash of this dimension's name, since the database
constrains it to be unique."""
        return hash(self.name)

    def __str__(self):
        return self.name

    def __getattr__(self, attrn):
        if attrn == 'things':
            return self.things_by_name.itervalues()
        elif attrn == 'places':
            return self.places_by_name.itervalues()
        elif attrn == 'portals':
            return DictValues2DIterator(self.portals_by_orign_destn)
        else:
            raise AttributeError("dimension has no attribute named " + attrn)

    def get_igraph_layout(self, layout_type):
        """Return a Graph layout, of the kind that igraph uses, representing
this dimension, and laid out nicely."""
        return self.graph.layout(layout=layout_type)

    def save(self):
        for port in self.portals:
            port.save()
        for thing in self.things:
            thing.save()

    def get_shortest_path(self, orig, dest, branch=None, tick=None):
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        for path in self.graph.get_shortest_paths(int(dest)):
            if self.graph.vs[path[-1]]["place"] == orig:
                return [self.graph.vs[i]["place"] for i in path]

    def add_place(self, pl):
        print "Adding place {0} to dimension {1}.".format(str(pl), str(self))
        self.places_by_name[str(pl)] = pl

    def add_portal(self, po):
        print "Adding portal from {0} to {1} to dimension {2}.".format(str(po.orig), str(po.dest), str(self))
        if str(po.orig) not in self.portals_by_orign_destn:
            self.portals_by_orign_destn[str(po.orig)] = OrderedDict()
        self.portals_by_orign_destn[str(po.orig)][str(po.dest)] = po

    def add_thing(self, th):
        print "Adding thing {0} to dimension {1}.".format(str(th), str(self))
        self.things_by_name[str(th)] = th
