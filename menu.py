from util import SaveableMetaclass, dictify_row, stringlike
from effect import read_effect_decks
from style import read_styles
from effect import Effect, EffectDeck
from copy import copy
import re
import pyglet


__metaclass__ = SaveableMetaclass


class MenuItem:
    tables = [
        ('menu_item',
         {'menu': 'text',
          'idx': 'integer',
          'text': 'text',
          'effect_deck': 'text',
          'closer': 'boolean',
          'visible': 'boolean',
          'interactive': 'boolean'},
         ('menu', 'idx'),
         {"menu": ("menu", "name"),
          "effect_deck": ("effect_deck_link", "deck")},
         [])]

    def __init__(self, menu, idx, text, effect_deck, closer,
                 visible, interactive, db=None):
        self.menu = menu
        self.idx = idx
        self.text = text
        self.effect_deck = effect_deck
        self.closer = closer
        self.visible = visible
        self.interactive = interactive
        self.grabpoint = None
        self.hovered = False
        self.label = None
        self.oldstate = None
        self.newstate = None
        self.pressed = False
        self.toggles = 0
        if db is not None:
            menun = None
            if isinstance(self.menu, Menu):
                menun = self.menu.name
            else:
                menun = self.menu
            if not menun in db.menuitemdict:
                db.menuitemdict[menun] = []
            while len(db.menuitemdict[menun]) <= self.idx:
                db.menuitemdict[menun].append(None)
            db.menuitemdict[menun][self.idx] = self

    def unravel(self, db):
        if stringlike(self.menu):
            self.menu = db.menudict[self.menu]
        if stringlike(self.effect_deck):
            menu_tog_match = re.match(
                'toggle_menu_visibility\((.*)\)', self.effect_deck)
            if menu_tog_match is not None:
                menuspec = menu_tog_match.groups()[0]
                self.make_toggler(menuspec, db)
            else:
                self.effect_deck = db.effectdeckdict[self.effect_deck]
        while len(self.menu.items) < self.idx:
            self.menu.items.append(None)
        self.menu.items[self.idx] = self

    def onclick(self, button, modifiers):
        self.effect_deck.do()

    def make_toggler(self, menuspec, db):
        boardname = None
        if stringlike(self.menu.board):
            boardname = self.menu.board
        else:
            boardname = self.menu.board.name
        menuspec = "{0}.{1}".format(boardname, menuspec)
        togglername = "toggle_menu_visibility({0})".format(menuspec),
        toggler = Effect(togglername, "toggle_menu_visibility", menuspec, db)
        togdeck = EffectDeck(togglername, [toggler], db)
        toggler.unravel(db)
        togdeck.unravel(db)
        db.effectdict[togglername] = toggler
        db.effectdeckdict[togglername] = togdeck
        self.effect_deck = togdeck

    def __eq__(self, other):
        return (
            isinstance(other, MenuItem) and
            self.menu == other.menu and
            self.idx == other.idx)

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

    def toggle_visibility(self):
        self.visible = not self.visible
        self.toggles += 1
        for item in self.items:
            item.toggle_visibility()

    def get_state_tup(self):
        return (
            self.menu.get_state_tup(),
            copy(self.idx),
            copy(self.text),
            copy(self.visible),
            copy(self.interactive),
            copy(self.grabpoint),
            copy(self.hovered),
            copy(self.pressed),
            copy(self.toggles))


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
    tables = [
        ('menu',
         {'name': 'text',
          'left': 'float not null',
          'bottom': 'float not null',
          'top': 'float not null',
          'right': 'float not null',
          'style': "text default 'Default'",
          "main_for_window": "boolean default 0",
          "visible": "boolean default 0"},
         ('name',),
         {},
         [])]
    interactive = True

    def __init__(self, name, left, bottom, top, right, style,
                 main_for_window, visible, db=None, board=None):
        self.name = name
        self.left = left
        self.bot = bottom
        self.top = top
        self.right = right
        self.width = self.right - self.left
        self.height = self.top - self.bot
        self.style = style
        self.main_for_window = main_for_window
        self.visible = visible
        self.interactive = True
        self.hovered = False
        self.grabpoint = None
        self.board = board
        self.sprite = None
        self.oldstate = None
        self.newstate = None
        self.pressed = False
        self.toggles = 0
        if db is not None:
            db.menudict[self.name] = self

    def unravel(self, db):
        if stringlike(self.style):
            self.style = db.styledict[self.style]
        self.style.unravel(db)
        bgi = self.style.bg_inactive.tup
        bga = self.style.bg_active.tup
        self.inactive_pattern = pyglet.image.SolidColorImagePattern(bgi)
        self.active_pattern = pyglet.image.SolidColorImagePattern(bga)
        self.items = db.menuitemdict[self.name]
        for item in self.items:
            item.unravel(db)
        if self.board is not None:
            if stringlike(self.board):
                self.board = db.boarddict[self.board]
            boardname = self.board.dimension.name
            if boardname not in db.boardmenudict:
                db.boardmenudict[boardname] = {}
            db.boardmenudict[boardname][self.name] = self

    def set_gw(self, gw):
        self.left_abs = gw.width * self.left
        self.right_abs = gw.width * self.right
        self.width_abs = gw.width * self.width
        self.top_abs = gw.height * self.top
        self.bot_abs = gw.height * self.bot
        self.height_abs = gw.height * self.height
        self.gw = gw

    def __eq__(self, other):
        return (
            self.name == other.name and
            self.board == other.board)

    def __getitem__(self, i):
        return self.items[i]

    def __setitem__(self, i, to):
        self.items[i] = to

    def __delitem__(self, i):
        return self.items.__delitem__(i)

    def getstyle(self):
        return self.style

    def getleft(self):
        return int(self.left_abs)

    def getbot(self):
        return int(self.bot_abs)

    def gettop(self):
        return int(self.top_abs)

    def getright(self):
        return int(self.right_abs)

    def getwidth(self):
        return int(self.width_abs)

    def getheight(self):
        return int(self.height_abs)

    def is_visible(self):
        return self.visible

    def is_interactive(self):
        return self.interactive

    def toggle_visibility(self):
        print "toggling visibility of menu {0}".format(self.name)
        self.visible = not self.visible
        self.toggles += 1

    def get_state_tup(self):
        return (
            self,
            self.left,
            self.bot,
            self.top,
            self.right,
            self.style,
            self.main_for_window,
            self.visible,
            self.hovered,
            self.grabpoint,
            self.pressed,
            self.toggles)


item_menu_qryfmt = (
    "SELECT {0} FROM menu_item WHERE menu IN ({1})".format(
        ", ".join(MenuItem.colns), "{0}"))


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
        while len(r[rowdict["menu"]]) <= rowdict["idx"]:
            r[rowdict["menu"]].append(None)
        rowdict["db"] = db
        numi = MenuItem(**rowdict)
        r[rowdict["menu"]][rowdict["idx"]] = numi
        decknames.add(numi.effect_deck)
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
    stylenames = set()
    menus = []
    for board in boards:
        r[board] = {}
    for row in db.c:
        rowdict = dictify_row(row, ["board"] + Menu.colnames["menu"])
        rowdict["db"] = db
        numenu = Menu(**rowdict)
        r[rowdict["board"]][rowdict["name"]] = numenu
        menunames.add(rowdict["name"])
        stylenames.add(rowdict["style"])
        menus.append(numenu)
        if rowdict["board"] not in db.boardmenudict:
            db.boardmenudict[rowdict["board"]] = {}
        db.boardmenudict[rowdict["board"]][rowdict["name"]] = numenu
    read_items_in_menus(db, list(menunames))
    read_styles(db, list(stylenames))
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
