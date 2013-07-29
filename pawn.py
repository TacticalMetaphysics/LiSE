from util import (
    SaveableMetaclass,
    TerminableImg,
    TerminableInteractivity)
from logging import getLogger


logger = getLogger(__name__)


"""Widget representing things that move about from place to place."""


class Pawn(object, TerminableImg, TerminableInteractivity):
    """A token to represent something that moves about between places."""
    __metaclass__ = SaveableMetaclass
    tables = [
        ("pawn_img",
         {"dimension": "text not null default 'Physical'",
          "board": "integer not null default 0",
          "thing": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "img": "text not null default 'default_pawn'"},
         ("dimension", "board", "thing", "tick_from"),
         {"dimension, board": ("board", "dimension, i"),
          "dimension, thing": ("thing_location", "dimension, name"),
          "img": ("img", "name")},
         []),
        ("pawn_interactive",
         {"dimension": "text not null default 'Physical'",
          "board": "integer not null default 0",
          "thing": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null"},
         ("dimension", "board", "thing", "tick_from"),
         {"dimension, board": ("board", "dimension, i"),
          "dimension, thing": ("thing_location", "dimension, name")},
         [])]

    def __init__(self, board, thing):
        """Return a pawn on the board for the given dimension, representing
the given thing with the given image. It may be visible or not,
interactive or not.

With db, register in db's pawndict.

        """
        self.board = board
        self.db = board.db
        self.thing = thing
        self.imagery = {}
        self.indefinite_imagery = {}
        self.interactivity = {}
        self.indefinite_interactivity = {}
        self.grabpoint = None
        self.sprite = None
        self.oldstate = None
        self.tweaks = 0
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.selectable = True
        self.box_edges = (None, None, None, None)

    def __str__(self):
        return str(self.thing)

    def __getattr__(self, attrn):
        if attrn == 'gw':
            return self.board.gw
        elif attrn == 'img':
            return self.get_img()
        elif attrn == 'highlit':
            return self in self.gw.selected
        elif attrn == 'hovered':
            return self.gw.hovered is self
        elif attrn == 'pressed':
            return self.gw.pressed is self
        elif attrn == 'grabbed':
            return self.gw.grabbed is self
        elif attrn == 'selected':
            return self in self.gw.selected
        elif attrn == 'window':
            return self.gw.window
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
        elif attrn == 'onscreen':
            return (
                self.window_right > 0 and
                self.window_left < self.window.width and
                self.window_top > 0 and
                self.window_bot < self.window.height)
        elif attrn == 'rx':
            return self.width / 2
        elif attrn == 'ry':
            return self.height / 2
        elif attrn == 'r':
            if self.rx > self.ry:
                return self.rx
            else:
                return self.ry
        elif attrn == 'state':
                return self.get_state_tup()
        else:
            raise AttributeError(
                "Pawn instance has no such attribute: " +
                attrn)

    def __setattr__(self, attrn, val):
        if attrn == "img":
            self.set_img(val)
        elif attrn == "interactive":
            self.set_interactive(val)
        else:
            super(Pawn, self).__setattr__(attrn, val)

    def __eq__(self, other):
        """Essentially, compare the state tuples of the two pawns."""
        return self.state == other.state

    def get_state_tup(self, branch=None, tick=None):
        """Return a tuple containing everything you might need to draw me."""
        return (
            self.get_img(branch, tick),
            self.interactive,
            self.onscreen,
            self.grabpoint,
            self.hovered,
            self.window_left,
            self.window_bot,
            self.tweaks)

    def move_with_mouse(self, x, y, dx, dy, buttons, modifiers):
        self.drag_offset_x += dx
        self.drag_offset_y += dy
        self.tweaks += 1

    def dropped(self, x, y, button, modifiers):
        logger.debug("Dropped the pawn %s at (%d,%d)",
                     str(self), x, y)
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        spot = self.board.get_spot_at(x, y)
        if spot is not None:
            logger.debug("Hit the spot %s", str(spot))
            destplace = spot.place
            try:
                startplacen = self.thing.journey.steps[-1][1]
            except IndexError:
                startplacen = str(self.thing.location)
            startplace = self.db.get_place(self._dimension, startplacen)
            logger.debug("Plotting a course from %s to %s",
                         startplacen, str(destplace))
            path = self.dimension.shortest_path(startplace, destplace)
            logger.debug("Got the path: " + str(path))
            if path is None:
                return
            self.thing.journey.add_path(path)
            self.db.caldict[self._dimension].adjust()

    def get_tabdict(self):
        dimn = str(self.dimension)
        thingn = str(self.thing)
        boardi = int(self.board)
        pawncols = ("dimension", "thing", "board", "tick_from", "tick_to", "img")
        pawn_img_rows = set()
        for branch in self.imagery:
            for (tick_from, (img, tick_to)) in self.imagery.iteritems():
                pawn_img_rows.add((
                    dimn,
                    thingn,
                    boardi,
                    tick_from,
                    tick_to,
                    str(img)))
        intercols = ("dimension", "thing", "board", "tick_from", "tick_to")
        pawn_interactive_rows = set()
        for branch in self.interactivity:
            for (tick_from, tick_to) in self.interactivity[branch].iteritems():
                pawn_interactive_rows.add((
                    dimn,
                    thingn,
                    boardi,
                    tick_from,
                    tick_to))
        return {
            "pawn_img": [dictify_row(row, pawncols)
                         for row in iter(pawn_img_rows)],
            "pawn_interactive": [dictify_row(row, intercols)
                                 for row in iter(pawn_interactive_rows)]}
