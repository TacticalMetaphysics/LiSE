from util import SaveableMetaclass
from collections import OrderedDict


"""Class for user's view on gameworld, and support functions."""


class BoardDimIter:
    def __init__(self, boardi, boardlst, sublst):
        self.i = boardi
        self.it = iter(boardlst)
        self.sublst = sublst

    def __iter__(self):
        return self

    def next(self):
        r = self.it.next()
        while (len(getattr(r, self.sublst)) < self.i or
               getattr(r, self.sublst)[self.i] is None):
            r = self.it.next()
        return r


class BoardPortIter(BoardDimIter):
    def __init__(self, board):
        return BoardDimIter.__init__(self, board.i, board.dimension.portals, 'arrows')


class BoardArrowIter:
    def __init__(self, board):
        self.it = BoardPortIter(board)

    def __iter__(self):
        return self

    def next(self):
        return self.it.next().arrows[self.it.i]


class BoardPlaceIter(BoardDimIter):
    def __init__(self, board):
        return BoardDimIter.__init__(self, board.i, board.dimension.places, 'spots')


class BoardSpotIter:
    def __init__(self, board):
        self.it = BoardPlaceIter(board)

    def __iter__(self):
        return self

    def next(self):
        return self.it.next().spots[self.it.i]


class BoardThingIter(BoardDimIter):
    def __init__(self, board):
        return BoardDimIter.__init__(self, board.i, board.dimension.things, 'pawns')


class BoardPawnIter:
    def __init__(self, board):
        self.it = BoardThingIter(board)

    def __iter__(self):
        return self

    def next(self):
        return self.it.next().pawns[self.it.i]


class Board:
    """A widget notionally representing the game board on which the rest
of the game pieces lie.

Each board represents exactly one dimension in the world model, but
you can have more than one board to a dimension. It has a width and
height in pixels, which do not necessarily match the width or height
of the window it's displayed in--a board may be scrolled horizontally
or vertically. Every board has a static background image, and may have
menus. The menus' positions are relative to the window rather than the
board, but they are linked to the board anyhow, on the assumption that
each board will be open in at most one window at a time.

    """
    __metaclass__ = SaveableMetaclass
    tables = [
        ("board",
         {"dimension": "text not null default 'Physical'",
          "i": "integer not null default 0",
          "wallpaper": "text not null default 'default_wallpaper'",
          "width": "integer not null default 4000",
          "height": "integer not null default 3000"},
         ("dimension", "i"),
         {"wallpaper": ("image", "name")},
         []),
    ]

    def __init__(self, gw, dimension, i, width, height, wallpaper):
        """Return a board representing the given dimension.

        """
        self.window = gw
        self.dimension = dimension
        self.db = self.dimension.db
        self.i = i
        self.width = width
        self.height = height
        self.wallpaper = wallpaper
        self.menu_by_name = OrderedDict()
        self.calendar_by_name = OrderedDict()

    def __getattr__(self, attrn):
        if attrn == "places":
            return BoardPlaceIter(self)
        elif attrn == "things":
            return BoardThingIter(self)
        elif attrn == "pawns":
            return BoardPawnIter(self)
        elif attrn == "spots":
            return BoardSpotIter(self)
        elif attrn == "portals":
            return BoardPortIter(self)
        elif attrn == "arrows":
            return BoardArrowIter(self)
        elif attrn == "menus":
            return self.menu_by_name.itervalues()
        elif attrn == "calendars":
            return self.calendar_by_name.itervalues()
        else:
            raise AttributeError("Board has no attribute named " + attrn)

    def __int__(self):
        return self.i

    def get_spot_at(self, x, y):
        for spot in self.spots:
            if (
                    spot.window_left < x < spot.window_right and
                    spot.window_bot < y < spot.window_top):
                return spot
        return None
