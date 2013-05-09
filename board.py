from util import SaveableMetaclass, dictify_row, stringlike
from menu import read_menus_in_boards
from img import load_imgs
from spot import read_spots_in_dimensions
from pawn import read_pawns_in_dimensions
from dimension import read_dimensions


"""Class for user's view on gameworld, and support functions."""


__metaclass__ = SaveableMetaclass


class Board:
    """A widget notionally representing the game board on which the rest
of the game pieces lie.

Each board represents exactly one dimension in the world model. It has
a width and height in pixels, which do not necessarily match the width
or height of the window it's displayed in--a board may be scrolled
horizontally or vertically. Every Board has a static background image,
and may have menus. The menus' positions are relative to the window
rather than the board, but they are linked to the board anyhow, on the
assumption that each board will be open in at most one window at a
time.

"""
    tablenames = ["board", "board_menu"]
    coldecls = {"board":
                {"dimension": "text",
                 "width": "integer",
                 "height": "integer",
                 "wallpaper": "text"},
                "board_menu":
                {"board": "text",
                 "menu": "text"}}
    primarykeys = {"board": ("dimension",),
                   "board_menu": tuple()}
    foreignkeys = {"board":
                   {"dimension": ("dimension", "name"),
                    "wallpaper": ("image", "name")},
                   "board_menu":
                   {"board": ("board", "name"),
                    "menu": ("menu", "name")}}

    def __init__(self, dimension,
                 width, height, wallpaper, db=None):
        """Return a board representing the given dimension.

dimension may be an instance of Dimension or the name of
one. wallpaper may be a pyglet image or the name of one. Boards aren't
very useful without pointers to the stuff that's on them, so you
really should supply a Database instance as db, and then unravel the
board later to get those pointers.

        """
        self.dimension = dimension
        self.width = width
        self.height = height
        self.wallpaper = wallpaper
        self.board_menu = set()
        if db is not None:
            dimname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            db.boarddict[dimname] = self

    def unravel(self, db):
        """Dereference strings into Python objects.

Grab the Python objects referred to by self.wallpaper and
self.dimension, if they are strings; then unravel all pawns, spots,
and menus herein.

        """
        if stringlike(self.wallpaper):
            self.wallpaper = db.imgdict[self.wallpaper]
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        self.dimension.unravel(db)
        self.pawndict = db.pawndict[self.dimension.name]
        self.spotdict = db.spotdict[self.dimension.name]
        self.menudict = db.boardmenudict[self.dimension.name]
        for pwn in self.pawndict.itervalues():
            pwn.unravel(db)
        for spt in self.spotdict.itervalues():
            spt.unravel(db)
        for mnu in self.menudict.itervalues():
            mnu.unravel(db)
            self.board_menu.add((self.name, mnu.name))

    def __eq__(self, other):
        return (
            isinstance(other, Board) and
            self.dimension == other.dimension)

    def __hash__(self):
        return self.hsh

    def getwidth(self):
        """Return the width assigned at instantiation."""
        return self.width

    def getheight(self):
        """Return the height assigned at instantiation."""
        return self.height

    def __repr__(self):
        return "A board, %d pixels wide by %d tall, representing the "\
            "dimension %s, containing %d spots, %d pawns, and %d menus."\
            % (self.width, self.height, self.dimension, len(self.spotdict),
               len(self.pawndict), len(self.menudict))


load_some_boards_qryfmt = (
    "SELECT {0} FROM board WHERE dimension IN ({1})".format(
        Board.colnamestr["board"], "{0}"))


load_all_boards_qrystr = (
    "SELECT {0} FROM board".format(Board.colnamestr["board"]))


def load_boards(db, names):
    """Make boards representing dimensions of the given names, returning a
list."""
    boarddict = {}
    imgs2load = set()
    if names is None or len(names) == 0:
        db.c.execute(load_all_boards_qrystr)
    else:
        qrystr = load_some_boards_qryfmt.format(", ".join(["?"] * len(names)))
        db.c.execute(qrystr, names)
    for row in db.c:
        rowdict = dictify_row(row, Board.colnames["board"])
        boarddict[rowdict["dimension"]] = rowdict
        imgs2load.add(rowdict["wallpaper"])
    read_dimensions(db, names)
    read_menus_in_boards(db, names)
    read_pawns_in_dimensions(db, names)
    for pwns in db.pawndict.itervalues():
        for pwn in pwns.itervalues():
            imgs2load.add(pwn.img)
    read_spots_in_dimensions(db, names)
    for spts in db.spotdict.itervalues():
        for spt in spts.itervalues():
            imgs2load.add(spt.img)
    load_imgs(db, list(imgs2load))
    for item in boarddict.iteritems():
        (key, board) = item
        nubd = dict(board)
        nubd["db"] = db
        boarddict[key] = Board(**nubd)
        boarddict[key].unravel(db)
    return boarddict


def load_all_boards(db):
    """Make every board described in the database, returning a list."""
    return load_boards(db, None)


def load_board(db, name):
    """Load and return the board representing the dimension named thus."""
    return load_boards(db, [name])[name]
