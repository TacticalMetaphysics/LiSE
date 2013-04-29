from util import SaveableMetaclass, dictify_row
from style import Color, Style
from menu import Menu, MenuItem
import world


__metaclass__ = SaveableMetaclass


class Board:
    tablenames = ["board", "boardmenu"]
    coldecls = {"board":
                {"dimension": "text",
                 "width": "integer",
                 "height": "integer",
                 "wallpaper": "text"},
                "boardmenu":
                {"board": "text",
                 "menu": "text"}}
    primarykeys = {"board": ("dimension",),
                   "boardmenu": ("board", "menu")}
    foreignkeys = {"board":
                   {"dimension": ("dimension", "name"),
                    "wallpaper": ("image", "name")},
                   "boardmenu":
                   {"board": ("board", "name"),
                    "menu": ("menu", "name")}}

    def __init__(self, dimension, menus, width, height, wallpaper, db=None):
        self.dimension = dimension
        self.menus = menus
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

    def pull_named(self, db, name):
        qryfmt = "SELECT {0} FROM board, boardmenu WHERE "
        colnames = self.colnames["board"] + ["menu"]
        boardcols = ["board." + col for col in self.colnames["board"]]
        qrycols = boardcols + ["boardmenu.menu"]
        qrystr = qryfmt.format(", ".join(qrycols))
        db.c.execute(qrystr, (name,))
        return self.parse([
            dictify_row(colnames, row) for row in db.c])

    def parse(self, rows):
        boarddict = {}
        for row in rows:
            if row["dimension"] in boarddict:
                row["dimension"]["menu"].append(row["menu"])
            else:
                boarddict["dimension"] = {
                    "dimension": row["dimension"],
                    "width": row["width"],
                    "height": row["height"],
                    "menu": [row["menu"]]}
        return boarddict

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


pull_board_cols = (
    Board.colnames["board"] +
    ["menu"] +
    Menu.valnames["menu"] +
    ["idx"] +
    MenuItem.valnames["menu_item"] +
    Style.valnames["style"] +
    Color.valnames["color"])

pull_board_qualified_cols = (
    ["board." + col for col in Board.colnames["board"]] +
    ["board_menu.menu"] +
    ["menu." + col for col in Menu.valnames["menu"]] +
    ["menu_item.idx"] +
    ["menu_item." + col for col in MenuItem.valnames["menu_item"]] +
    ["style." + col for col in Style.valnames["style"]] +
    ["color." + col for col in Color.valnames["color"]])

pull_board_colstr = ", ".join(pull_board_qualified_cols)

pull_board_qrystr = (
    "SELECT {0} FROM board, board_menu, menu, menu_item, style, color "
    "WHERE board.dimension=board_menu.board "
    "AND board_menu.menu=menu.name "
    "AND menu_item.menu=menu.name "
    "AND menu_item.style=style.name "
    "AND ("
    "style.bg_inactive=color.name OR "
    "style.bg_active=color.name OR "
    "style.fg_inactive=color.name OR "
    "style.fg_active=color.name "
    "AND board.dimension=?".format(pull_board_colstr))


def pull_named(db, name):
    dimension = world.pull_dimension(db, name)
    db.c.execute(pull_board_qrystr, (name,))
    boarddict = {
        "dimension": dimension,
        "db": db}
    menudict = {}
    for row in db.c:
        rowdict = dictify_row(pull_board_qualified_cols, row)
        if "width" not in boarddict:
            boarddict["width"] = rowdict["width"]
            boarddict["height"] = rowdict["height"]
            boarddict["wallpaper"] = rowdict["wallpaper"]
        for colorfield in ["style.bg_inactive", "style.bg_active",
                           "style.fg_inactive", "style.fg_active"]:
            if rowdict[colorfield] not in db.colordict:
                db.colordict[rowdict[colorfield]] = Color(
                    rowdict[colorfield], rowdict["red"], rowdict["green"],
                    rowdict["blue"], rowdict["alpha"])
        if rowdict["menu.style"] not in db.styledict:
            db.styledict[rowdict["menu.style"]] = Style(
                rowdict["menu.style"], rowdict["style.fontface"],
                rowdict["style.fontsize"],
                rowdict["style.bg_inactive"], rowdict["style.bg_active"],
                rowdict["style.fg_inactive"], rowdict["style.fg_active"])
        if rowdict["board_menu.menu"] not in menudict:
            menudict[rowdict["board_menu.menu"]] = Menu(
                rowdict["menu.name"], rowdict["menu.left"],
                rowdict["menu.bottom"], rowdict["menu.top"],
                rowdict["menu.right"], rowdict["menu.style"],
                rowdict["menu.main_for_window"],
                rowdict["menu.visible"], rowdict["menu.interactive"],
                db)
    boarddict["menus"] = menudict
    return boarddict


def load_named(db, name):
    return Board(**pull_named(db, name))
