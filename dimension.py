import igraph
from item import (
    read_things_in_dimensions,
    read_places_in_dimensions,
    read_portals_in_dimensions,
    read_schedules_in_dimensions,
    read_journeys_in_dimensions)
from util import SaveableMetaclass


__metaclass__ = SaveableMetaclass


class Dimension:
    tablenames = ["dimension"]
    coldecls = {"dimension":
                {"name": "text"}}
    primarykeys = {"dimension": ("name",)}

    def __init__(self, name, placedict, portaldict, thingdict, db=None):
        self.name = name
        self.placedict = placedict
        self.portaldict = portaldict
        self.thingdict = thingdict
        if db is not None:
            db.dimensiondict[name] = self

    def __hash__(self):
        return hash(self.name)

    def unravel(self, db):
        for mydict in [self.placedict, self.portaldict, self.thingdict]:
            for val in mydict.itervalues():
                val.unravel(db)

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
    read_schedules_in_dimensions(db, names)
    read_journeys_in_dimensions(db, names)
    things = read_things_in_dimensions(db, names)
    places = read_places_in_dimensions(db, names)
    portals = read_portals_in_dimensions(db, names)
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
