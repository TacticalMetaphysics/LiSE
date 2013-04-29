import igraph
import item
import journey
import schedule
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


def pull_dimension(db, name):
    things = item.pull_things_in_dimension(db, name)
    places = item.pull_places_in_dimension(db, name)
    portals = item.pull_portals_in_dimension(db, name)
    journeys = journey.pull_in_dimension(db, name)
    schedules = schedule.pull_in_dimension(db, name)
    things = item.combine_things(things, journeys, schedules)
    dimension = Dimension(name, places, portals, things, db)
    return dimension
