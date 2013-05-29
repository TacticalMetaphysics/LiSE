from util import SaveableMetaclass, dictify_row, stringlike
from calendar import CalendarCol


"""Widget representing things that move about from place to place."""


__metaclass__ = SaveableMetaclass


class Pawn:
    """A token to represent something that moves about between places."""

    tables = [
        ("pawn",
         {"dimension": "text not null default 'Physical'",
          "thing": "text not null",
          "img": "text not null default 'troll_m'",
          "visible": "boolean not null default 1",
          "interactive": "boolean not null default 1"},
         ("dimension", "thing"),
         {"img": ("img", "name"),
          "dimension, thing": ("thing", "dimension, name")},
         [])]

    def __init__(self, dimension, thing, img, visible, interactive, db=None):
        """Return a pawn on the board for the given dimension, representing
the given thing with the given image. It may be visible or not,
interactive or not.

With db, register in db's pawndict.

        """
        self.dimension = dimension
        self.thing = thing
        self.img = img
        self.visible = visible
        self.interactive = interactive
        self.grabpoint = None
        self.sprite = None
        self.oldstate = None
        self.newstate = None
        self.hovered = False
        self.tweaks = 0
        if db is not None:
            dimname = None
            thingname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if stringlike(self.thing):
                thingname = self.thing
            else:
                thingname = self.thing.name
            if dimname not in db.pawndict:
                db.pawndict[dimname] = {}
            db.pawndict[dimname][thingname] = self

    def __eq__(self, other):
        """Essentially, compare the state tuples of the two pawns."""
        return (
            isinstance(other, Pawn) and
            self.dimension == other.dimension and
            self.thing == other.thing and
            self.img == other.img and
            self.visible == other.visible and
            self.interactive == other.interactive and
            self.grabpoint == other.grabpoint)

    def unravel(self, db):
        """On the assumption that my thing has already been unraveled,
dereference it, the board, and the image.

Then store myself as an attribute of the thing, and the thing's
schedule and calendar column as an attribute of myself.

In the absence of a calendar column, but the presence of a schedule,
make a new, hidden calendar column to represent the schedule.

        """
        # Invariant: things have already been unraveled
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        self.board = db.boarddict[self.dimension.name]
        if stringlike(self.thing):
            self.thing = db.itemdict[self.board.dimension.name][self.thing]
        self.thing.pawn = self
        if not hasattr(self, 'calcol'):
            if hasattr(self.thing, 'schedule'):
                self.calcol = CalendarCol(
                    self.board.dimension.name, self.thing.name,
                    True, True, "BigLight", "SmallDark")
        if hasattr(self, 'calcol'):
            self.calcol.unravel(db)
        if stringlike(self.img):
            self.img = db.imgdict[self.img]
        self.rx = self.img.getwidth() / 2
        self.ry = self.img.getheight() / 2

    def getcoords(self):
        """Return my x and y in a pair."""
        # Assume I've been provided a spotdict. Use it to get the
        # spot's x and y, as well as that of the spot for the next
        # step on my thing's journey. If my thing doesn't have a
        # journey, return the coords of the spot. If it does, return a
        # point between the start and end spots in proportion to the
        # journey's progress. If there is no end spot, behave as if
        # there's no journey.
        #
        # I can't assume that img is an actual image because the
        # loader instantiates things before assigning them data that's
        # not strings or numbers. Calculate self.rx to save some
        # division.
        if hasattr(self.thing, 'journey') and\
           self.thing.journey.steps_left() > 0:
            j = self.thing.journey
            port = j[0]
            if stringlike(port.orig) or stringlike(port.dest):
                # The portals haven't actually been loaded yet
                raise Exception('Tried to draw a pawn {0} before loading portal {1} properly.'.format(repr(self), repr(port)))
            start = port.orig.spot
            end = port.dest.spot
            hdist = end.x - start.x
            vdist = end.y - start.y
            p = self.thing.journey_progress
            x = start.x + hdist * p
            y = start.y + vdist * p
            return (x, y)
        else:
            ls = self.thing.location.spot
            return ls.getcenter()

    def getcenter(self):
        """Return the x and y of my centerpoint in a pair."""
        (x, y) = self.getcoords()
        return (x + self.rx, y + self.ry)

    def getleft(self):
        """Return the x of my leftmost edge."""
        return self.getcoords()[0]

    def getright(self):
        """Return the x of my rightmost edge."""
        return self.getcoords()[0] + self.img.getwidth()

    def getrx(self):
        """Return half my width."""
        return self.rx

    def getry(self):
        """Return half my height."""
        return self.ry

    def gettop(self):
        """Return the y of my top edge."""
        return self.getcoords()[1] + self.img.getheight()

    def getbot(self):
        """Return the y of my bottom edge."""
        return self.getcoords()[1]

    def is_visible(self):
        """Can you see me?"""
        return self.visible

    def is_interactive(self):
        """Can you touch me?"""
        return self.interactive

    def onclick(self, button, modifiers):
        """For now, pawns toggle their associated calendar columns on being
clicked. This is probably not the ideal."""
        # strictly a hack. replace with effectdeck as soon as reasonable
        if hasattr(self, 'calcol'):
            self.calcol.toggle_visibility()

    def set_hovered(self):
        """Become hovered."""
        if not self.hovered:
            self.hovered = True
            self.tweaks += 1

    def unset_hovered(self):
        """Stop being hovered."""
        if self.hovered:
            self.hovered = False
            self.tweaks += 1

    def set_pressed(self):
        """Become pressed."""
        pass

    def unset_pressed(self):
        """Stop being pressed."""
        pass

    def get_state_tup(self):
        """Return a tuple containing everything you might need to draw me."""
        (x, y) = self.getcoords()
        return (
            self.img.name,
            self.visible,
            self.interactive,
            self.grabpoint,
            self.hovered,
            x,
            y,
            self.tweaks)

    def is_visible(self):
        return self.visible


pawncolstr = ", ".join(Pawn.colnames["pawn"])

pawn_dimension_qryfmt = (
    "SELECT {0} FROM pawn WHERE dimension IN ({1})".format(pawncolstr, "{0}"))


def read_pawns_in_boards(db, names):
    """Read all pawns in the given boards. Don't unravel them yet.

They'll be in a 2D dictionary, keyed first by board name, then by
thing name.

    """
    qryfmt = pawn_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, names)
    r = {}
    for name in names:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Pawn.colnames["pawn"])
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["thing"]] = Pawn(**rowdict)
    return r


def unravel_pawns(db, pawnd):
    """Unravel pawns in a dictionary keyed by thing name, and return
it."""
    for pawn in pawnd.itervalues():
        pawn.unravel(db)
    return pawnd


def unravel_pawns_in_boards(db, pawnd):
    """Unravel pawns read in by read_pawns_in_boards"""
    for pawns in pawnd.itervalues():
        unravel_pawns(db, pawns)
    return pawnd


def load_pawns_in_boards(db, names):
    """Load all pawns in the given boards, and return them in a 2D
dictionary keyed first by board name, then by thing name."""
    return unravel_pawns_in_dimensions(db, read_pawns_in_boards(db, names))
