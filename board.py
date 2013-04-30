from util import SaveableMetaclass, dictify_row
import style
Style = style.Style
Color = style.Color
from menu import Menu, MenuItem
import dimension
import img
Img = img.Img
import pawn
Pawn = pawn.Pawn
import spot
Spot = spot.Spot


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
                 width, height, wallpaper, db=None)
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
        self.wallpaper = db.imgdict[self.wallpaper]
        self.dimension.unravel(db)
        for menu in self.menus.itervalues():
            menu.unravel()

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


pull_board_style_cols = (
    Board.colnames["board"] +
    Img.valnames["img"] +
    ["menu"] +
    Menu.valnames["menu"] +
    ["idx"] +
    MenuItem.valnames["menu_item"] +
    Style.valnames["style"] +
    Color.valnames["color"])

pull_board_style_qualified_cols = (
    ["board." + col for col in Board.colnames["board"]] +
    ["img." + val for val in Img.valnames["img"]] +
    ["board_menu.menu"] +
    ["menu." + col for col in Menu.valnames["menu"]] +
    ["menu_item.idx"] +
    ["menu_item." + col for col in MenuItem.valnames["menu_item"]] +
    ["style." + col for col in Style.valnames["style"]])

pull_board_style_qryfmt = (
    "SELECT {0} FROM board, img, board_menu, menu, menu_item, style"
    "WHERE board.dimension=board_menu.board "
    "AND board.wallpaper=img.name "
    "AND board_menu.menu=menu.name "
    "AND menu_item.menu=menu.name "
    "AND menu.style=style.name "
    "AND board.dimension IN ({1})".format(
        ", ".join(pull_board_style_qualified_cols),
        "{0}"))


pull_board_pawn_cols = (
    Pawn.colnames["pawn"] +
    Img.valnames["img"])


pull_board_pawn_qualified_cols = (
    ["pawn." + col for col in Pawn.colnames["pawn"]] +
    ["img." + val for val in Img.valnames["img"]])


pull_board_pawn_qryfmt = (
    "SELECT {0} FROM pawn, img WHERE "
    "pawn.img=img.name AND "
    "dimension IN ({1})".format(
        ", ".join(pull_board_pawn_qualified_cols),
        "{0}"))


pull_board_spot_cols = (
    Spot.colnames["spot"] +
    Img.valnames["img"])


pull_board_spot_qualified_cols = (
    ["spot." + col for col in Spot.colnames["spot"]] +
    ["img." + val for val in Img.valnames["img"]])


pull_board_spot_qryfmt = (
    "SELECT {0} FROM spot, img WHERE "
    "spot.img=img.name AND "
    "dimension IN ({1})".format(
        ", ".join(pull_board_spot_qualified_cols),
        "{0}"))


def load_named(db, names):
    qmstr = ["?"] * len(names)
    qryfmt = pull_board_style_qryfmt
    qrystr = qryfmt.format(qmstr)
    dim = dimension.load_named(db, names)
    db.c.execute(qrystr, names)
    colornames = set()
    instantiated = {
        'board': [],
        'dimension': [],
        'thing': [],
        'place': [],
        'portal': [],
        'pawn': [],
        'spot': [],
        'event': [],
        'effect': [],
        'event_deck': [],
        'effect_deck': [],
        'character': [],
        'menu': [],
        'menu_item': []}
    styledict = {}
    rowdicts = [
        dictify_row(row, pull_board_style_cols)
        for row in db.c]
    boarddict = {}
    # boarddict will have dimension names for keys. It's easy to get
    # those: they are in the arguments.
    for name in names:
        boarddict[name] = {
            "dimension": dim[name],
            "pawndict": {},
            "spotdict": {},
            "menudict": {}}
    for row in rowdicts:
        # The general theme is, for foreign keys, add a new dictionary
        # by that key to the existing dictionary by the name of the
        # table linked-to. For other keys, assign their values
        # straight to the appropriate dictionary representing their
        # table, preferably iterating over the field names provided by
        # the class rather than hard-coding them. The dictionaries
        # will be multiply nested...don't worry, I'll get the data out
        # of there by the end of this function.
        boardptr = boarddict[row["dimension"]]
        if "width" not in boardptr:
            boardptr["width"] = row["width"]
        if "height" not in boardptr:
            boardptr["height"] = row["height"]
        if "wallpaper" not in boardptr:
            imgdict = {
                "name": rowdict["wallpaper"],
                "path": rowdict["path"],
                "rltile": rowdict["rltile"],
                "db": db}
            boardptr["wallpaper"] = Img(**imgdict)
            instantiated.append(boardptr["wallpaper"])
        boardptr["dimension"] = dim[boardptr["dimension"]]
        for coln in Board.colnames["board"]:
            if coln not in boardptr:
                boardptr[coln] = row[coln]
        if row["menu"] not in boardptr["menudict"]:
            boardptr["menudict"][row["menu"]] = {
                "name": row["menu"],
                "items": []}
            for val in Menu.valnames["menu"]:
                boardptr["menudict"][row["menu"]][val] = row[val]
        menuptr = boardptr["menudict"][row["menu"]]
        if isinstance(menuptr["style"], str):
            menuptr["style"] = {
                "name": row["style"]}
            for val in Style.valnames["style"]:
                menuptr["style"][val] = row[val]
            styledict[row["style"]] = menuptr["style"]
        for colorcol in ["bg_inactive", "bg_active",
                         "fg_inactive", "fg_active"]:
            colornames.add(row[colorcol])
        while len(menuptr["items"]) < row["idx"]:
            menuptr.append(None)
        if menuptr["items"][row["idx"]] is None:
            menuptr["items"][row["idx"]] = {
                "menu": row["menu"],
                "idx": row["idx"]}
            for val in MenuItem.valnames["menu_item"]:
                menuptr["items"][row["idx"]][val] = row[val]
    # I've been collecting the names of colors I need. Time to load
    # their values.
    style.load_colors_named(db, iter(colornames))
    for val in styledict.itervalues():
        val["db"] = db
        val = Style(**val)
        instantiated.append(val)
    for board in boarddict.itervalues():
        for menu in board["menus"].itervalues():
            menu["style"] = styledict[menu["style"]]
    # Now I want to load the widgets representing the Items in the
    # Dimension.  Pawns and Spots both get their graphics from the
    # same places, and Portals don't have graphics per se. So I'll
    # pull Pawns and Spots now.
    qryfmt = pull_board_pawn_qryfmt
    qrystr = qryfmt.format(qmstr)
    db.c.execute(qrystr, names)
    for row in db.c:
        rowdict = dictify_row(row, pull_board_pawn_cols)
        imgrowdict = {
            "name": rowdict["img"],
            "path": rowdict["path"],
            "rltile": rowdict["rltile"],
            "db": db}
        rowdict["img"] = Img(**imgrowdict)
        instantiated.append(rowdict["img"])
        pawndict = boarddict[rowdict["dimension"]]["pawndict"]
        pawndict[rowdict["thing"]] = Pawn(**rowdict)
        instantiated.append(pawndict[rowdict["thing"]])
    qryfmt = pull_board_spot_qryfmt
    qrystr = qryfmt.format(qmstr)
    db.c.execute(qrystr, names)
    for row in db.c:
        rowdict = dictify_row(row, pull_board_spot_cols)
        imgrowdict = {
            "name": rowdict["img"],
            "path": rowdict["path"],
            "rltile": rowdict["rltile"],
            "db": db}
        for valn in Img.valnames["img"]:
            if valn not in imgrowdict:
                imgrowdict[valn] = rowdict[valn]
        spotrowdict = {
            "dimension": rowdict["dimension"],
            "place": rowdict["place"],
            "img": Img(**imgrowdict)}
        instantiated['img'].append(spotrowdict["img"])
        for valn in Spot.valnames["spot"]:
            if valn not in spotrowdict:
                spotrowdict[valn] = rowdict[valn]
