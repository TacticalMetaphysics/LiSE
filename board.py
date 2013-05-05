from util import SaveableMetaclass, dictify_row, stringlike
from menu import read_menus_in_boards
from img import load_imgs
from spot import read_spots_in_dimensions
from pawn import read_pawns_in_dimensions
from dimension import read_dimensions


__metaclass__ = SaveableMetaclass


class Board:
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

    def __init__(self, dimension, pawndict, spotdict, menudict,
                 width, height, wallpaper, db=None):
        self.dimension = dimension
        self.pawndict = pawndict
        self.spotdict = spotdict
        self.menudict = menudict
        self.width = width
        self.height = height
        self.wallpaper = wallpaper
        if db is not None:
            dimname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            db.boarddict[dimname] = self

    def unravel(self, db):
        if stringlike(self.wallpaper):
            self.wallpaper = db.imgdict[self.wallpaper]
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        self.dimension.unravel(db)
        for pwn in self.pawndict.itervalues():
            pwn.unravel(db)
        for spt in self.spotdict.itervalues():
            spt.unravel(db)
        for mnu in self.menudict.itervalues():
            mnu.unravel(db)

    def __eq__(self, other):
        return (
            isinstance(other, Board) and
            self.dimension == other.dimension)

    def __hash__(self):
        return self.hsh

    def getwidth(self):
        return self.width

    def getheight(self):
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
        dim = board["dimension"]
        nubd["pawndict"] = db.pawndict[dim]
        nubd["spotdict"] = db.spotdict[dim]
        nubd["menudict"] = db.boardmenudict[dim]
        nubd["db"] = db
        boarddict[key] = Board(**nubd)
        boarddict[key].unravel(db)
    return boarddict


def load_all_boards(db):
    return load_boards(db, None)


def load_board(db, name):
    return load_boards(db, [name])
