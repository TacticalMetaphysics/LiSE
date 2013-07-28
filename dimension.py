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

logger = getLogger(__name__)


"""Class and loaders for dimensions--the top of the world hierarchy."""


class Dimension:
    """Container for a given view on the game world, sharing no things,
places, or portals with any other dimension, but possibly sharing
characters."""
    thing_loc_qry_start = (
        "SELECT thing, branch, tick_from, tick_to, "
        "location FROM thing_location WHERE dimension=?")
    thing_speed_qry_start = (
        "SELECT thing, branch, tick_from, tick_to, "
        "ticks_per_span FROM thing_speed WHERE dimension=?")
    port_qry_start = (
        "SELECT origin, destination, branch, tick_from, "
        "tick_to FROM portal_existence WHERE dimension=?")
    board_qry_start = (
        "SELECT wallpaper, width, height "
        "FROM board WHERE dimension=? AND i=?")
    spot_board_qry_start = (
        "SELECT place, branch, tick_from, tick_to, "
        "x, y FROM spot_coords WHERE dimension=? AND board=?")
    spot_img_qry_start = (
        "SELECT place, branch, tick_from, tick_to, "
        "img FROM spot_img WHERE dimension=? AND board=?")
    spot_inter_qry_start = (
        "SELECT place, branch, tick_from, tick_to "
        "FROM spot_interactive WHERE dimension=? AND board=?")
    pawn_img_qry_start = (
        "SELECT thing, branch, tick_from, tick_to, "
        "img FROM pawn_img WHERE dimension=? AND board=?")
    pawn_inter_qry_start = (
        "SELECT thing, branch, tick_from, tick_to "
        "FROM pawn_interactive WHERE dimension=? AND board=?")
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
        self.boards = []
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

    def get_shortest_path(self, orig, dest, branch=None, tick=None):
        origi = int(orig)
        desti = int(dest)
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        for path in self.graph.get_shortest_paths(desti):
            if path[-1] == origi:
                return path

    def load(self, branches=None, tick_from=None, tick_to=None):
        branchexpr = ""
        tickfromexpr = ""
        ticktoexpr = ""
        if branches is not None:
            branchexpr = " AND branch IN ({0})".format(
                ", ".join(["?"] * len(branches)))
        if tick_from is not None:
            tickfromexpr = " AND tick_from>=?"
        if tick_to is not None:
            ticktoexpr = " AND tick_to<=?"
        extrastr = "".join((branchexpr, tickfromexpr, ticktoexpr))
        qrystr = self.thing_loc_qry_start + extrastr
        valtup = tuple([str(self)] + [
            b for b in (branches, tick_from, tick_to)
            if b is not None])
        self.db.c.execute(qrystr, valtup)
        for row in self.db.c:
            (thingn, branch, tick_from, tick_to, locn) = row
            if thingn not in self.things_by_name:
                self.things_by_name[thingn] = Thing(self, thingn)
            if locn not in self.places_by_name:
                pl = Place(self, locn)
                self.places_by_name[locn] = pl
                self.places.append(pl)
            self.things_by_name[thingn].set_location(
                self.places_by_name[locn], branch, tick_from, tick_to)
        qrystr = self.port_qry_start + extrastr
        self.db.c.execute(qrystr, valtup)
        for row in self.db.c:
            (orign, destn, branch, tick_from, tick_to) = row
            if orign not in self.places_by_name:
                opl = Place(self, orign)
                self.places_by_name[orign] = opl
                self.places.append(opl)
            else:
                opl = self.places_by_name[orign]
            if destn not in self.places_by_name:
                dpl = Place(self, destn)
                self.places_by_name[destn] = dpl
                self.places.append(dpl)
            else:
                dpl = self.places_by_name[destn]
            if orign not in self.portals_by_orign_destn:
                self.portals_by_orign_destn[orign] = {}
            po = Portal(self, opl, dpl)
            self.portals_by_orign_destn[orign][destn] = po
            self.portals.append(po)
        # Contrary to the tutorial, the graph starts out with vertex 0
        # already in it.
        self.graph.add_vertices(len(self.places) - 1)
        self.graph.vs["place"] = self.places
        edges = [(int(portal.orig), int(portal.dest)) for portal in self.portals]
        self.graph.add_edges(edges)
        self.graph.es["portal"] = self.portals

    def load_board(self, gw, i):
        while len(self.boards) <= i:
            self.boards.append(None)
        # basic information for this board
        self.db.c.execute(self.board_qry_start, (str(self), i))
        for row in self.db.c:  # there is only one
            (wallpaper, width, height) = row
            b = Board(gw, self, i, width, height, wallpaper)
            self.boards[i] = b
        # spots in this board
        self.db.c.execute(self.spot_board_qry_start, (str(self), i))
        for row in self.db.c:
            (placen, branch, tick_from, tick_to, x, y) = row
            place = self.places_by_name[placen]  # i hope you loaded *me* first
            if not hasattr(place, 'spots'):
                place.spots = []
            while len(place.spots) <= i:
                place.spots.append(None)
            place.spots[i] = Spot(b, place)
            place.spots[i].set_coords(x, y, branch, tick_from, tick_to)
        # images for the spots
        imgs = set()
        self.db.c.execute(self.spot_img_qry_start, (str(self), i))
        spot_rows = self.db.c.fetchall()
        for row in spot_rows:
            imgs.add(row[4])
        # interactivity for the spots
        self.db.c.execute(self.spot_inter_qry_start, (str(self), i))
        for row in self.db.c:
            (placen, branch, tick_from, tick_to) = row
            place = self.places_by_name[placen]
            place.spots[i].set_interactive(branch, tick_from, tick_to)
        # arrows in this board
        for portal in self.portals:
            if i in portal.orig.spots and i in portal.dest.spots:
                if not hasattr(portal, 'arrows'):
                    portal.arrows = []
                while len(portal.arrows) <= i:
                    portal.arrows.append(None)
                portal.arrows[i] = Arrow(b, portal)
        # pawns in this board, and their images
        self.db.c.execute(self.pawn_img_qry_start, (str(self), i))
        pawn_rows = self.db.c.fetchall()
        for row in pawn_rows:
            imgs.add(row[4])
        imgnames = tuple(imgs)
        self.db.c.execute(
            "SELECT name, path, rltile FROM img WHERE name IN ({0})".format(
                ", ".join(["?"] * len(imgnames))), imgnames)
        for row in self.db.c:
            (name, path, rltile) = row
            Img(self.db, name, path, rltile)
        for row in pawn_rows:
            (thingn, branch, tick_from, tick_to, imgn) = row
            thing = self.things_by_name[thingn]
            if not hasattr(thing, 'pawns'):
                thing.pawns = []
            while len(thing.pawns) <= i:
                thing.pawns.append(None)
            thing.pawns[i] = Pawn(b, thing)
            thing.pawns[i].set_img(self.db.imgdict[imgn], branch, tick_from, tick_to)
        for row in spot_rows:
            (placen, branch, tick_from, tick_to, imgn) = row
            place = self.places_by_name[placen]
            # assume spots got assigned to places already
            place.spots[i].set_img(self.db.imgdict[imgn], branch, tick_from, tick_to)
        # interactivity for the pawns
        self.db.c.execute(self.pawn_inter_qry_start, (str(self), i))
        for row in self.db.c:
            (thingn, branch, tick_from, tick_to) = row
            thing = self.things_by_name[thingn]
            thing.pawns[i].set_interactive(branch, tick_from, tick_to)
