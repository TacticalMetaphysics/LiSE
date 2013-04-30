from util import SaveableMetaclass, dictify_row
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
            db.boarddict[self.dimension.name] = self

    def unravel(self, db):
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
            % (self.width, self.height, self.dimension, len(self.spots),
               len(self.pawns), len(self.menus))


def load_boards(db, names):
    boarddict = {}
    imgs2load = set()
    for name in names:
        boarddict[name] = {
            "dimension": name,
            "db": db}
    qrystr = "SELECT {0} FROM board WHERE name IN ({1})".format(
        ", ".join(Board.colnames["board"]), ", ".join(["?"] * len(names)))
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
    load_imgs(db, iter(imgs2load))
    for board in boarddict.itervalues():
        nubd = dict(board)
        dim = board["dimension"]
        nubd["pawndict"] = db.pawndict[dim]
        nubd["spotdict"] = db.spotdict[dim]
        nubd["menudict"] = db.boardmenudict[dim]
        board = Board(**nubd)
        board.unravel(db)
    return boarddict
