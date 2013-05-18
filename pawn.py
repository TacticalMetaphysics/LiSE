from util import SaveableMetaclass, dictify_row, stringlike
from calendar import CalendarCol


__metaclass__ = SaveableMetaclass


class Pawn:
    """A token to represent something that moves about between Places.

    Pawn(thing, place, x, y) => pawn

    thing is the game-logic item that the Pawn represents.
    It should be of class Thing.

    place is the name of a Place that is already represented by a Spot
    in the same Board. pawn will appear here to begin with. Note that
    the Spot need not be visible. You can supply the Place name for an
    invisible spot to make it appear that a Pawn is floating in that
    nebulous dimension between Places.

    """

    tables = [
        ("pawn",
         {"board": "text",
          "thing": "text",
          "img": "text",
          "visible": "boolean",
          "interactive": "boolean"},
         ("board", "thing"),
         {"img": ("img", "name"),
          "board, thing": ("thing", "dimension, name")},
         [])]

    def __init__(self, board, thing, img, visible, interactive, db=None):
        self.board = board
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
            if stringlike(self.board):
                dimname = self.board
            else:
                if stringlike(self.board.dimension):
                    dimname = self.board.dimension
                else:
                    dimname = self.board.dimension.name
            if stringlike(self.thing):
                thingname = self.thing
            else:
                thingname = self.thing.name
            if dimname not in db.pawndict:
                db.pawndict[dimname] = {}
            db.pawndict[dimname][thingname] = self

    def __eq__(self, other):
        return (
            isinstance(other, Pawn) and
            self.dimension == other.dimension and
            self.thing == other.thing and
            self.img == other.img and
            self.visible == other.visible and
            self.interactive == other.interactive and
            self.grabpoint == other.grabpoint)

    def unravel(self, db):
        # Invariant: things have already been unraveled
        if stringlike(self.board):
            self.board = db.boarddict[self.board]
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
           self.thing.journey.stepsleft() > 0:
            j = self.thing.journey
            port = j.getstep(0)
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
            return (ls.x, ls.y)

    def getcenter(self):
        (x, y) = self.getcoords()
        return (x + self.rx, y + self.ry)

    def getleft(self):
        return self.getcoords()[0]

    def getright(self):
        return self.getcoords()[0] + self.img.getwidth()

    def getrx(self):
        return self.rx

    def getry(self):
        return self.ry

    def gettop(self):
        return self.getcoords()[1] + self.img.getheight()

    def getbot(self):
        return self.getcoords()[1]

    def is_visible(self):
        return self.visible

    def is_interactive(self):
        return self.interactive

    def onclick(self, button, modifiers):
        # strictly a hack. replace with effectdeck as soon as reasonable
        print "pawn for {0} clicked".format(self.thing.name)
        if hasattr(self, 'calcol'):
            self.calcol.toggle_visibility()

    def set_hovered(self):
        if not self.hovered:
            self.hovered = True
            self.tweaks += 1

    def unset_hovered(self):
        if self.hovered:
            self.hovered = False
            self.tweaks += 1

    def set_pressed(self):
        pass

    def unset_pressed(self):
        pass

    def get_state_tup(self):
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


pawncolstr = ", ".join(Pawn.colnames["pawn"])

pawn_dimension_qryfmt = (
    "SELECT {0} FROM pawn WHERE board IN ({1})".format(pawncolstr, "{0}"))


def read_pawns_in_boards(db, names):
    qryfmt = pawn_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, names)
    r = {}
    for name in names:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Pawn.colnames["pawn"])
        rowdict["db"] = db
        r[rowdict["board"]][rowdict["thing"]] = Pawn(**rowdict)
    return r


def unravel_pawns(db, pawnd):
    for pawn in pawnd.itervalues():
        pawn.unravel(db)
    return pawnd


def unravel_pawns_in_boards(db, pawnd):
    for pawns in pawnd.itervalues():
        unravel_pawns(db, pawns)
    return pawnd


def load_pawns_in_boards(db, names):
    return unravel_pawns_in_dimensions(db, read_pawns_in_boards(db, names))
