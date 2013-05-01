from util import SaveableMetaclass, dictify_row, stringlike
from effect import read_effect_decks


__metaclass__ = SaveableMetaclass


class MenuItem:
    tablenames = ["menu_item"]
    coldecls = {'menu_item':
                {'menu': 'text',
                 'idx': 'integer',
                 'text': 'text',
                 'onclick': 'text',
                 'closer': 'boolean',
                 'visible': 'boolean',
                 'interactive': 'boolean'}}
    primarykeys = {'menu_item': ('menu', 'idx')}
    foreignkeys = {'menu_item':
                   {"menu": ("menu", "name"),
                    "onclick": ("effect_deck", "name")}}

    def __init__(self, menu, idx, text, onclick, closer,
                 visible, interactive, db=None):
        self.menu = menu
        self.idx = idx
        self.text = text
        self.onclick = onclick
        self.closer = closer
        self.visible = visible
        self.interactive = interactive
        if db is not None:
            menun = None
            if isinstance(self.menu, Menu):
                menun = self.menu.name
            else:
                menun = self.menu
            if not menun in db.menuitemdict:
                db.menuitemdict[menun] = []
            while len(db.menuitemdict[menun]) < self.idx:
                db.menuitemdict[menun].append(None)
            db.menuitemdict[menun][self.idx] = self

    def unravel(self, db):
        if stringlike(self.menu):
            self.menu = db.menudict[self.menu]
        if stringlike(self.onclick):
            self.onclick = db.effectdeckdict[self.onclick]
        while len(self.menu.items) < self.idx:
            self.menu.items.append(None)
        self.menu.items[self.idx] = self

    def __eq__(self, other):
        return (
            isinstance(other, MenuItem) and
            self.menu == other.menu and
            self.idx == other.idx)

    def __hash__(self):
        return self.hsh

    def __gt__(self, other):
        if isinstance(other, str):
            return self.text > other
        return self.text > other.text

    def __ge__(self, other):
        if isinstance(other, str):
            return self.text >= other
        return self.text >= other.text

    def __lt__(self, other):
        if isinstance(other, str):
            return self.text < other
        return self.text < other.text

    def __le__(self, other):
        if isinstance(other, str):
            return self.text <= other
        return self.text <= other.text

    def __repr__(self):
        return self.text

    def getcenter(self):
        width = self.getwidth()
        height = self.getheight()
        rx = width / 2
        ry = height / 2
        x = self.getleft()
        y = self.getbot()
        return (x + rx, y + ry)

    def getleft(self):
        if not hasattr(self, 'left'):
            self.left = self.menu.getleft() + self.menu.style.spacing
        return self.left

    def getright(self):
        if not hasattr(self, 'right'):
            self.right = self.menu.getright() - self.menu.style.spacing
        return self.right

    def gettop(self):
        if not hasattr(self, 'top'):
            self.top = (self.menu.gettop() - self.menu.style.spacing -
                        (self.idx * self.getheight()))
        return self.top

    def getbot(self):
        if not hasattr(self, 'bot'):
            self.bot = self.gettop() - self.menu.style.fontsize
        return self.bot

    def getwidth(self):
        if not hasattr(self, 'width'):
            self.width = self.getright() - self.getleft()
        return self.width

    def getheight(self):
        if not hasattr(self, 'height'):
            self.height = self.menu.style.fontsize + self.menu.style.spacing
        return self.height

    def onclick(self, button, modifiers):
        return self.onclick_core(self.onclick_arg)

    def toggle_visibility(self):
        self.visible = not self.visible
        for item in self.items:
            item.toggle_visibility()


def pull_items_in_menus(db, menunames):
    qryfmt = "SELECT {0} FROM menu_item WHERE menu IN ({1})"
    qms = ["?"] * len(menunames)
    qrystr = qryfmt.format(
        MenuItem.colnamestr["menu_item"],
        ", ".join(qms))
    db.c.execute(qrystr, menunames)
    return parse_menu_item([
        dictify_row(MenuItem.colnames["menu_item"], row)
        for row in db.c])


def parse_menu_item(rows):
    r = {}
    for row in rows:
        if row["menu"] not in r:
            r[row["menu"]] = {}
        r[row["menu"]][row["idx"]] = row
    return r


class Menu:
    tablenames = ["menu"]
    coldecls = {'menu':
                {'name': 'text',
                 'left': 'float not null',
                 'bottom': 'float not null',
                 'top': 'float not null',
                 'right': 'float not null',
                 'style': "text default 'Default'",
                 "main_for_window": "boolean default 0",
                 "visible": "boolean default 0"}}
    primarykeys = {'menu': ('name',)}
    interactive = True

    def __init__(self, name, left, bottom, top, right, style,
                 main_for_window, visible,
                 items=[], db=None, board=None):
        self.name = name
        self.left = left
        self.bottom = bottom
        self.top = top
        self.right = right
        self.style = style
        self.main_for_window = main_for_window
        self.visible = visible
        self.interactive = True
        self.items = items
        self.board = board
        if db is not None:
            db.menudict[self.name] = self

    def unravel(self, db):
        self.style = db.styledict[self.style]

    def __eq__(self, other):
        if hasattr(self, 'gw'):
            return (
                hasattr(other, 'gw') and
                other.gw == self.gw and
                other.name == self.name)
        else:
            return (
                other.name == self.name)

    def __hash__(self):
        if hasattr(self, 'gw'):
            return hash(self.name) + hash(self.gw)
        else:
            return hash(self.name)

    def __iter__(self):
        return (self.name, self.left, self.bottom, self.top,
                self.right, self.style.name, self.visible)

    def __getitem__(self, i):
        return self.items[i]

    def __setitem__(self, i, to):
        self.items[i] = to

    def __delitem__(self, i):
        return self.items.__delitem__(i)

    def getstyle(self):
        return self.style

    def getleft(self):
        return int(self.left * self.window.width)

    def getbot(self):
        return int(self.bottom * self.window.height)

    def gettop(self):
        return int(self.top * self.window.height)

    def getright(self):
        return int(self.right * self.window.width)

    def getwidth(self):
        return int((self.right - self.left) * self.window.width)

    def getheight(self):
        return int((self.top - self.bottom) * self.window.height)

    def is_visible(self):
        return self.visible

    def is_interactive(self):
        return self.interactive

    def toggle_visibility(self):
        self.visible = not self.visible


item_qualified_cols = ["menu_item." + col
                       for col in MenuItem.colnames["menu_item"]]

item_menu_qryfmt = (
    "SELECT {0}, effect_deck_link.idx, effect.func, effect.arg "
    "FROM menu_item, effect_deck_link, effect "
    "WHERE menu_item.onclick=effect_deck_link.deck "
    "AND effect_deck_link.effect=effect.name "
    "AND menu_item.menu IN ({1})".format(
        ", ".join(item_qualified_cols), "{0}"))


def read_items_in_menus(db, menus):
    # Assumes menus are already in db.menudict
    qryfmt = item_menu_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(menus)))
    db.c.execute(qrystr, tuple(menus))
    r = {}
    decknames = set()
    for menu in menus:
        r[menu] = []
    for row in db.c:
        rowdict = dictify_row(row, MenuItem.colnames["menu_item"])
        while len(r[rowdict["menu"]]) < rowdict["idx"]:
            r[rowdict["menu"]].append(None)
        rowdict["db"] = db
        numi = MenuItem(**rowdict)
        r[rowdict["menu"]][rowdict["idx"]] = numi
        decknames.add(numi.onclick)
    read_effect_decks(db, list(decknames))
    return r


def unravel_items(db, itd):
    for it in itd.itervalues():
        it.unravel(db)
    return itd


def unravel_items_in_menus(db, mitd):
    for its in mitd.itervalues():
        unravel_items(db, its)
    return mitd


def load_items_in_menus(db, menus):
    return unravel_items_in_menus(db, read_items_in_menus(db, menus))


menu_qualified_cols = ["menu." + col for col in Menu.colnames["menu"]]
menu_board_qryfmt = (
    "SELECT board_menu.board, {0} FROM menu, board_menu WHERE "
    "menu.name=board_menu.menu AND "
    "board_menu.board IN ({1})".format(
        ", ".join(menu_qualified_cols), "{0}"))


def read_menus_in_boards(db, boards):
    qryfmt = menu_board_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(boards)))
    db.c.execute(qrystr, boards)
    r = {}
    menunames = set()
    menus = []
    for board in boards:
        r[board] = {}
    for row in db.c:
        rowdict = dictify_row(row, ["board"] + Menu.colnames["menu"])
        rowdict["db"] = db
        numenu = Menu(**rowdict)
        r[rowdict["board"]][rowdict["name"]] = numenu
        menunames.add(rowdict["name"])
        menus.append(numenu)
    items = read_items_in_menus(db, menunames)
    for menu in menus:
        menu.items = items[menu.name]
    return r


def unravel_menus(db, md):
    for menu in md.itervalues():
        menu.unravel()
    return md


def unravel_menus_in_boards(db, bmd):
    for menus in bmd.itervalues():
        unravel_menus(db, menus)
    return bmd


def load_menus_in_boards(db, boards):
    return unravel_menus_in_boards(db, read_menus_in_boards(db, boards))
