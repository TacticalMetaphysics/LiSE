import igraph
from item import (
    read_things_in_dimensions,
    read_places_in_dimensions,
    read_portals_in_dimensions,
    read_schedules_in_dimensions,
    read_journeys_in_dimensions)
from util import DictValues2DIterator


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
        db.dimensiondict[name] = self
        self.db = db

    def __getattr__(self, attrn):
        if attrn == 'portals':
            return DictValues2DIterator(self.portalorigdestdict)
        elif attrn == 'itemdict':
            return self.db.itemdict[self.name]
        elif attrn == 'thingdict':
            return self.db.thingdict[self.name]
        elif attrn == 'placedict':
            return self.db.placedict[self.name]
        elif attrn == 'scheduledict':
            return self.db.scheduledict[self.name]
        elif attrn == 'journeydict':
            return self.db.journeydict[self.name]
        elif attrn == 'portalorigdestdict':
            return self.db.portalorigdestdict[self.name]
        elif attrn == 'portaldestorigdict':
            return self.db.portaldestorigdict[self.name]
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
        for place in self.placedict.itervalues():
            place.unravel()
        for dests in self.portalorigdestdict.itervalues():
            for portal in dests.itervalues():
                portal.unravel()
        for journey in self.journeydict.itervalues():
            journey.unravel()
        for schedule in self.scheduledict.itervalues():
            schedule.unravel()
        for thing in self.thingdict.itervalues():
            thing.unravel()

    def get_edges(self):
        """Return pairs of names, where each name represents a portal
herein."""
        r = []
        for (orign, origdict) in self.portalorigdestdict.iteritems():
            for destn in origdict.iterkeys():
                r.append((orign, destn))
        return r

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
