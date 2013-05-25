import igraph
from item import (
    read_things_in_dimensions,
    read_places_in_dimensions,
    read_portals_in_dimensions,
    read_schedules_in_dimensions,
    read_journeys_in_dimensions)
from util import SaveableMetaclass


"""Class and loaders for dimensions--the top of the world hierarchy."""


class Dimension:
    """Container for a given view on the game world, sharing no things,
places, or portals with any other dimension, but possibly sharing
characters."""

    def __init__(self, name, db=None):
        """Return a dimension with the given name.

Probably useless unless, once you're sure you've put all your places,
portals, and things in the db, you call the Dimension object's unravel(db)
method. Thereafter, it will have dictionaries of all those items,
keyed with their names.

        """
        self.name = name
        if db is not None:
            db.dimensiondict[name] = self

    def __hash__(self):
        return hash(self.name)

    def unravel(self, db):
        if not hasattr(self, 'itemdict'):
            self.itemdict = db.itemdict[self.name]
        if not hasattr(self, 'thingdict'):
            self.thingdict = db.thingdict[self.name]
        if not hasattr(self, 'placedict'):
            self.placedict = db.placedict[self.name]
        if not hasattr(self, 'portalorigdestdict'):
            self.portalorigdestdict = db.portalorigdestdict[self.name]
        if not hasattr(self, 'portaldestorigdict'):
            self.portaldestorigdict = db.portaldestorigdict[self.name]
        # this order is deliberate
        for place in self.placedict.itervalues():
            place.unravel(db)
        for dests in self.portalorigdestdict.itervalues():
            for portal in dests.itervalues():
                portal.unravel(db)
        for thing in self.thingdict.itervalues():
            thing.unravel(db)
            
    def get_edges(self):
        """Return pairs of hashes, where each hash represents a portal
herein."""
        return [(hash(item[0]), hash(item[1])) for item in
                self.portalorigdestdict.iteritems()]

    def get_edge_atts(self):
        """This will be useful when I want to add weights to the edges."""
        return {}

    def get_vertex_atts(self):
        """igraph uses this. I think it's also to do with weight."""
        return {}

    def get_igraph_graph(self):
        """Return a Graph object, of the kind that igraph uses, representing
this dimension."""
        return igraph.Graph(edges=self.get_edges(), directed=True,
                            vertex_attrs=self.get_vertex_atts(),
                            edge_attrs=self.get_edge_atts())

    def get_igraph_layout(self, layout_type):
        """Return a Graph layout, of the kind that igraph uses, representing
this dimension, and laid out nicely."""
        return self.get_igraph_graph().layout(layout=layout_type)
                


def read_dimensions(db, names):
    """Read in from disk the dimensions of the given names and everything
in them.

Objects will be instantiated to represent the lot, and a dictionary
thereof will be returned, but the objects won't be unraveled yet.

    """
    read_schedules_in_dimensions(db, names)
    read_journeys_in_dimensions(db, names)
    read_things_in_dimensions(db, names)
    read_places_in_dimensions(db, names)
    read_portals_in_dimensions(db, names)
    r = {}
    for name in names:
        r[name] = Dimension(name, db)
    return r


def unravel_dimensions(db, dd):
    for dim in dd.itervalues():
        dim.unravel(db)
    return dd


def load_dimensions(db, names):
    return unravel_dimensions(db, read_dimensions(db, names))
