import igraph
from item import (
    load_things_in_dimensions,
    load_places_in_dimensions,
    load_portals_in_dimensions)
from util import SaveableMetaclass


__metaclass__ = SaveableMetaclass


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

    def unravel(self, db):
        for place in self.places:
            place.unravel(db)
        for portal in self.portals:
            portal.unravel(db)
        for thing in self.things:
            thing.unravel(db)

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


def read_dimensions(db, names):
    things = load_things_in_dimensions(db, names)
    places = load_places_in_dimensions(db, names)
    portals = load_portals_in_dimensions(db, names)
    r = {}
    for name in names:
        r[name] = Dimension(
            name,
            places[name],
            portals[name],
            things[name],
            db)
    return r


def unravel_dimensions(db, dd):
    for dim in dd.itervalues():
        dim.unravel(db)
    return dd


def load_dimensions(db, names):
    return unravel_dimensions(db, read_dimensions(db, names))
