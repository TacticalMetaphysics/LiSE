from util import SaveableMetaclass, dictify_row, stringlike
from menu import read_menus_in_boards
from img import load_imgs
from style import read_styles
from spot import read_spots_in_boards
from calendar import Calendar, read_calendar_cols_in_boards
from pawn import read_pawns_in_boards
from menu import read_menus_in_boards
from dimension import read_dimensions


"""Class for user's view on gameworld, and support functions."""


__metaclass__ = SaveableMetaclass


class Board:
    """A widget notionally representing the game board on which the rest
of the game pieces lie.

Each board represents exactly one dimension in the world model. It has
a width and height in pixels, which do not necessarily match the width
or height of the window it's displayed in--a board may be scrolled
horizontally or vertically. Every board has a static background image,
and may have menus. The menus' positions are relative to the window
rather than the board, but they are linked to the board anyhow, on the
assumption that each board will be open in at most one window at a
time.

"""
    tables = [
        ("board",
         {"dimension": "text",
          "wallpaper": "text",
          "width": "integer DEFAULT 1024",
          "height": "integer DEFAULT 768",
          "calendar_visible": "boolean DEFAULT 0",
          "calendar_interactive": "boolean DEFAULT 1",
          "calendar_left": "float DEFAULT 0.8",
          "calendar_right": "float DEFAULT 1.0",
          "calendar_top": "float DEFAULT 1.0",
          "calendar_bot": "float DEFAULT 0.0",
          "calendar_rows_on_screen": "integer DEFAULT 240",
          "calendar_scrolled_to": "integer DEFAULT 0"},
         ("dimension",),
         {"dimension": ("dimension", "name"),
          "wallpaper": ("image", "name")},
         ["calendar_rows_on_screen > 0", "calendar_scrolled_to >= 0"])]

    def __init__(self, dimension, width, height, wallpaper,
                 calendar_left, calendar_right, calendar_top,
                 calendar_bot, calendar_visible, calendar_interactive,
                 calendar_rows_on_screen, calendar_scrolled_to, db=None):
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
        caldict = {
            "board": self,
            "left": calendar_left,
            "bot": calendar_bot,
            "right": calendar_right,
            "top": calendar_top,
            "visible": calendar_visible,
            "interactive": calendar_interactive,
            "rows_on_screen": calendar_rows_on_screen,
            "scrolled_to": calendar_scrolled_to,
            "db": db}
        self.calendar = Calendar(**caldict)
        if db is not None:
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
        self.menudict = db.menudict[self.dimension.name]
        for pwn in self.pawndict.itervalues():
            pwn.unravel(db)
        for spt in self.spotdict.itervalues():
            spt.unravel(db)
        for mnu in self.menudict.itervalues():
            mnu.unravel(db)
        self.calendar.unravel(db)
        

    def __eq__(self, other):
        return (
            isinstance(other, Board) and
            self.dimension == other.dimension)

    def __hash__(self):
        return hash(self.dimension) + 1

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


read_some_boards_format = (
    "SELECT {0} FROM board WHERE dimension IN ({1})".format(
        ", ".join(Board.colns), "{0}"))


def read_boards(db, boards):
    qryfmt = read_some_boards_format
    qrystr = qryfmt.format(", ".join(["?"] * len(boards)))
    db.c.execute(qrystr, boards)
    r = {}
    imgs = set()
    styles = set()
    for row in db.c:
        rowdict = dictify_row(row, Board.colns)
        rowdict["db"] = db
        r[rowdict["dimension"]] = Board(**rowdict)
        imgs.add(rowdict["wallpaper"])
    read_dimensions(db, boards)
    for menus in read_menus_in_boards(db, boards).itervalues():
        for menu in menus.itervalues():
            if stringlike(menu.style):
                styles.add(menu.style)
    for spots in read_spots_in_boards(db, boards).itervalues():
        for spot in spots.itervalues():
            if stringlike(spot.img):
                imgs.add(spot.img)
    for pawns in read_pawns_in_boards(db, boards).itervalues():
        for pawn in pawns.itervalues():
            if stringlike(pawn.img):
                imgs.add(pawn.img)
    for calcols in read_calendar_cols_in_boards(db, boards).itervalues():
        for calcol in calcols.itervalues():
            if stringlike(calcol.style):
                styles.add(calcol.style)
            if stringlike(calcol.cel_style):
                styles.add(calcol.cel_style)
    load_imgs(db, list(imgs))
    read_styles(db, list(styles))
    return r


def unravel_boards(db, boardd):
    for board in boardd.itervalues():
        board.unravel(db)
    return boardd


def load_boards(db, boards):
    return unravel_boards(db, read_boards(db, boards))


def load_board(db, boardn):
    return load_boards(db, [boardn])
