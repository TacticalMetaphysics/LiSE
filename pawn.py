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

    def __init__(self, db, dimension, thing, img, visible, interactive):
        """Return a pawn on the board for the given dimension, representing
the given thing with the given image. It may be visible or not,
interactive or not.

With db, register in db's pawndict.

        """
        self.dimension = dimension
        self.thing = thing
        self.img = img
        self._visible = visible
        self._interactive = interactive
        self.grabpoint = None
        self.sprite = None
        self.oldstate = None
        self.newstate = None
        self.hovered = False
        self.tweaks = 0
        dimname = str(self.dimension)
        thingname = str(self.thing)
        if dimname not in db.pawndict:
            db.pawndict[dimname] = {}
        db.pawndict[dimname][thingname] = self
        self.db = db

    def __getattr__(self, attrn):
        if attrn == 'board':
            return self.db.boarddict[str(self.dimension)]
        elif attrn == 'gw':
            return self.board.gw
        elif attrn == 'window':
            return self.gw.window
        elif attrn == 'interactive':
            return self._interactive
        elif attrn == 'window_left':
            return self.getcoords()[0]
        elif attrn == 'window_bot':
            return self.getcoords()[1]
        elif attrn == 'width':
            return self.img.width
        elif attrn == 'height':
            return self.img.height
        elif attrn == 'window_right':
            return self.window_left + self.width
        elif attrn == 'window_top':
            return self.window_bot + self.height
        elif attrn == 'rx':
            return self.width / 2
        elif attrn == 'ry':
            return self.height / 2
        elif attrn == 'r':
            if self.rx > self.ry:
                return self.rx
            else:
                return self.ry
        elif attrn == 'visible':
            return (
                self._visible and
                self.window_right > 0 and
                self.window_left < self.gw.window.width and
                self.window_top > 0 and
                self.window_bot < self.gw.window.height)
        else:
            raise AttributeError(
                "Pawn instance has no such attribute: " +
                attrn)

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

    def unravel(self):
        """On the assumption that my thing has already been unraveled,
dereference it, the board, and the image.

Then store myself as an attribute of the thing, and the thing's
schedule and calendar column as an attribute of myself.

In the absence of a calendar column, but the presence of a schedule,
make a new, hidden calendar column to represent the schedule.

        """
        # Invariant: things have already been unraveled
        db = self.db
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        self.board = db.boarddict[self.dimension.name]
        if stringlike(self.thing):
            self.thing = db.itemdict[self.board.dimension.name][self.thing]
        self.thing.pawn = self
        if hasattr(self, 'calcol') and self.calcol is not None:
            self.calcol.unravel()
        else:
            if hasattr(self.thing, 'schedule'):
                self.calcol = CalendarCol(
                    db, self.board.dimension.name,
                    self.thing.name, True, True, "BigLight", "SmallDark")
        if stringlike(self.img):
            self.img = db.imgdict[self.img]

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
                raise Exception(
                    """Tried to draw a pawn {0} before loading
portal {1} properly.""".format(repr(self), repr(port)))
            start = port.orig.spot
            end = port.dest.spot
            hdist = end.window_x - start.window_x
            vdist = end.window_y - start.window_y
            p = self.thing.journey_progress
            x = start.window_x + hdist * p
            y = start.window_y + vdist * p
            return (x, y)
        else:
            ls = self.thing.location.spot
            return (ls.window_x, ls.window_y)

    def onclick(self):
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


def unravel_pawns(pawnd):
    """Unravel pawns in a dictionary keyed by thing name, and return
it."""
    for pawn in pawnd.itervalues():
        pawn.unravel()
    return pawnd


def unravel_pawns_in_boards(pawnd):
    """Unravel pawns read in by read_pawns_in_boards"""
    for pawns in pawnd.itervalues():
        unravel_pawns(pawns)
    return pawnd


def load_pawns_in_boards(db, names):
    """Load all pawns in the given boards, and return them in a 2D
dictionary keyed first by board name, then by thing name."""
    return unravel_pawns_in_boards(read_pawns_in_boards(db, names))
