from util import SaveableMetaclass, dictify_row, stringlike
from effect import read_effect_decks
from style import read_styles
from effect import (
    EffectDeck,
    make_menu_toggler,
    make_calendar_toggler)
import re
import pyglet


__metaclass__ = SaveableMetaclass


MENU_TOGGLER_RE = re.compile("toggle_menu\((.*)\)")
CALENDAR_TOGGLER_RE = re.compile("toggle_calendar\((.*)\)")


class MenuItem:
    tables = [
        ('menu_item',
         {'board': "text default 'Physical'",
          'menu': 'text',
          'idx': 'integer',
          'text': 'text',
          'effect_deck': 'text',
          'closer': "boolean default 1",
          'visible': "boolean default 1",
          'interactive': "boolean default 1"},
         ('board', 'menu', 'idx'),
         {"board, menu": ("menu", "board, name"),
          "effect_deck": ("effect_deck_link", "deck")},
         [])]

    def __init__(self, board, menu, idx, text, effect_deck, closer,
                 visible, interactive, db=None):
        self.board = board
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
        self.tweaks = 0
        if db is not None:
            if stringlike(self.board):
                boardname = self.board
            else:
                if stringlike(self.board.dimension):
                    boardname = self.board.dimension
                else:
                    boardname = self.board.dimension.name
            if stringlike(self.menu):
                menuname = self.menu
            else:
                menuname = self.menu.name
            if boardname not in db.menuitemdict:
                db.menuitemdict[boardname] = {}
            if menuname not in db.menuitemdict[boardname]:
                db.menuitemdict[boardname][menuname] = []
            ptr = db.menuitemdict[boardname][menuname]
            while len(ptr) <= self.idx:
                ptr.append(None)
            ptr[self.idx] = self

    def unravel(self, db):
        if stringlike(self.board):
            self.board = db.boarddict[self.board]
        if stringlike(self.menu):
            self.menu = db.menudict[self.board.dimension.name][self.menu]
        self.parse_effect_deck(db)
        while len(self.menu.items) < self.idx:
            self.menu.items.append(None)
        if self.text[0] == "@":
            self.text = db.get_text(self.text[1:])

    def onclick(self, button, modifiers):
        self.effect_deck.do()

    def set_hovered(self):
        if not self.hovered:
            self.hovered = True
            self.tweaks += 1

    def unset_hovered(self):
        if self.hovered:
            self.hovered = False
            self.tweaks += 1

    def set_pressed(self):
        pass

    def unset_pressed(self):
        pass

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
        return (self.get_center_x(), self.get_center_y())

    def get_center_x(self):
        return self.getleft() + self.getrx()

    def get_center_y(self):
        return self.getbot() + self.getry()

    def getleft(self):
        return self.menu.getleft() + self.menu.style.spacing

    def getright(self):
        return self.menu.getright() - self.menu.style.spacing

    def gettop(self):
        return self.top

    def getbot(self):
        return self.bot

    def getwidth(self):
        return self.getright() - self.getleft()

    def getheight(self):
        return self.menu.style.fontsize + self.menu.style.spacing

    def getrx(self):
        return self.getwidth() / 2

    def getry(self):
        return self.getheight() / 2

    def toggle_visibility(self):
        self.visible = not self.visible
        self.tweaks += 1

    def hide(self):
        if self.visible:
            self.toggle_visibility()

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def get_state_tup(self):
        return (
            hash(self.menu.get_state_tup()),
            self.idx,
            self.text,
            self.visible,
            self.interactive,
            self.grabpoint,
            self.hovered,
            self.pressed,
            self.tweaks)

    def parse_effect_deck(self, db):
        efd = self.effect_deck
        if isinstance(efd, EffectDeck) or db is None:
            self.effect_deck = efd
            return
        menutogmatch = re.match(MENU_TOGGLER_RE, efd)
        if menutogmatch is not None:
            menuspec = menutogmatch.groups()[0]
            menuspec_split = menuspec.split(".")
            if len(menuspec_split) == 2:
                (b, m) = menuspec_split
                self.effect_deck = make_menu_toggler(b, m, db)
            else:
                if stringlike(self.menu.board):
                    boardname = self.menu.board
                else:
                    if stringlike(self.menu.board.dimension):
                        boardname = self.menu.board.dimension
                    else:
                        boardname = self.menu.board.dimension.name
                self.effect_deck = make_menu_toggler(boardname, menuspec, db)
                return
        caltogmatch = re.match(CALENDAR_TOGGLER_RE, efd)
        if caltogmatch is not None:
            calspec = caltogmatch.groups()[0]
            calspec_split = calspec.split(".")
            if len(calspec_split) == 2:
                (dimn, itn) = calspec_split
                self.effect_deck = make_calendar_toggler(dimn, itn, db)
            else:
                if stringlike(self.menu.board):
                    dimname = self.menu.board
                else:
                    if stringlike(self.menu.board.dimension):
                        dimname = self.menu.board.dimension
                    else:
                        dimname = self.menu.board.dimension.name
                self.effect_deck = make_calendar_toggler(dimname, calspec, db)
            return
        if efd in db.effectdeckdict:
            self.effect_deck = db.effectdeckdict[efd]

    def is_visible(self):
        return self.visible


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
         {'board': "text default 'Physical'"
          'name': 'text',
          'left': "float default 0.2",
          'bottom': "float default 0.0",
          'top': 'float default 1.0',
          'right': 'float default 0.3'
          'style': "text default 'SmallDark'",
          "main_for_window": "boolean default 0",
          "visible": "boolean default 0"},
         ('name',),
         {},
         [])]
    interactive = True

    def get_tabdict(self):
        return {
            "menu": self.get_rowdict(),
            "menu_item": [it.get_rowdict() for it in self.items]
        }

    def __init__(self, board, name, left, bottom, top, right, style,
                 main_for_window, visible, db=None):
        self.board = board
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
        self.sprite = None
        self.oldstate = None
        self.newstate = None
        self.pressed = False
        self.tweaks = 0
        if db is not None:
            if stringlike(self.board):
                boardname = self.board
            else:
                boardname = self.board.name
            if boardname not in db.menudict:
                db.menudict[boardname] = {}
            db.menudict[boardname][self.name] = self

    def unravel(self, db):
        if stringlike(self.style):
            self.style = db.styledict[self.style]
        self.style.unravel(db)
        self.rowheight = self.style.fontsize + self.style.spacing
        bgi = self.style.bg_inactive.tup
        bga = self.style.bg_active.tup
        self.inactive_pattern = pyglet.image.SolidColorImagePattern(bgi)
        self.active_pattern = pyglet.image.SolidColorImagePattern(bga)
        if stringlike(self.board):
            boardname = self.board
        else:
            boardname = self.board.name
        self.items = db.menuitemdict[boardname][self.name]
        for item in self.items:
            item.unravel(db)

    def set_gw(self, gw):
        self.gw = gw
        self.adjust()

    def adjust(self):
        self.left_abs = int(self.gw.width * self.left)
        self.right_abs = int(self.gw.width * self.right)
        self.width_abs = int(self.gw.width * self.width)
        self.top_abs = int(self.gw.height * self.top)
        self.bot_abs = int(self.gw.height * self.bot)
        self.height_abs = int(self.gw.height * self.height)
        self.rx_abs = (self.right_abs - self.left_abs) / 2
        self.ry_abs = (self.top_abs - self.bot_abs) / 2
        self.center_abs = (self.rx_abs + self.left_abs,
                           self.ry_abs + self.bot_abs)
        i = 0
        for item in self.items:
            item.top_from_top = i * self.rowheight
            item.bot_from_top = item.top_from_top + self.rowheight
            item.top = self.top_abs - item.top_from_top
            item.bot = item.top - self.rowheight
            i += 1

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
        return self.left_abs

    def getbot(self):
        return self.bot_abs

    def gettop(self):
        return self.top_abs

    def getright(self):
        return self.right_abs

    def getcenter(self):
        fx = self.center_abs[0]
        fy = self.center_abs[1]
        return (fx, fy)

    def getwidth(self):
        return self.width_abs

    def getheight(self):
        return self.height_abs

    def getrx(self):
        return self.rx_abs

    def getry(self):
        return self.ry_abs

    def is_visible(self):
        return self.visible

    def is_interactive(self):
        return self.interactive

    def toggle_visibility(self):
        print "toggling visibility of menu {0}".format(self.name)
        self.visible = not self.visible
        self.tweaks += 1

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def hide(self):
        if self.visible:
            self.toggle_visibility()

    def onclick(self, button, modifiers):
        if self.hovered is not None:
            self.hovered.onclick(button, modifiers)

    def set_hovered(self):
        pass

    def unset_hovered(self):
        pass

    def set_pressed(self):
        pass

    def unset_pressed(self):
        pass

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
            self.tweaks)


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
        if stringlike(numi.effect_deck):
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


menu_qcols = ["menu." + coln for coln in Menu.colns]
menu_item_qvals = ["menu_item.idx"] + ["menu_item." + valn for valn in MenuItem.valns]
mbqcols = menu_qcols + menu_item_qvals
mbcols = Menu.colns + ["idx"] + MenuItem.valns
menu_board_qryfmt = (
    "SELECT {0} FROM menu JOIN menu_item ON "
    "menu.board=menu_item.board AND "
    "menu.name=menu_item.menu WHERE menu.board IN ({1})".format(
        ", ".join(mbqcols), "{0}"))


def read_menus_in_boards(db, boards):
    qryfmt = menu_board_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(boards)))
    db.c.execute(qrystr, boards)
    r = {}
    for board in boards:
        r[board] = {}
    for row in db.c:
        rowdict = dictify_row(row, mbqcols)
        if rowdict["menu.name"] not in r[rowdict["menu.board"]]:
            menurd = {"db": db}
            for coln in Menu.colns:
                menurd[coln] = rowdict["menu." + coln]
            r[rowdict["menu.board"]][rowdict["menu.name"]] = Menu(**menurd)
        menuitemrd = {"db": db,
                      "board": rowdict["menu.board"],
                      "menu": rowdict["menu.name"],
                      "idx": rowdict["menu_item.idx"]}
        for valn in MenuItem.valns:
            menuitemrd[valn] = rowdict["menu_item." + valn]
        mi = MenuItem(**menuitemrd)
    return r


def unravel_menus(db, md):
    for menu in md.itervalues():
        menu.unravel(db)
    return md


def unravel_menus_in_boards(db, bmd):
    for menus in bmd.itervalues():
        unravel_menus(db, menus)
    return bmd


def load_menus_in_boards(db, boards):
    return unravel_menus_in_boards(db, read_menus_in_boards(db, boards))


def make_menu_toggler_menu_item(
        target_menu, menu_of_residence, idx, txt,
        closer, visible, interactive, db):
    if stringlike(menu_of_residence.board):
        boardname = menu_of_residence.board
    else:
        boardname = menu_of_residence.board.dimension.name
    if stringlike(target_menu):
        menuname = target_menu
    else:
        menuname = target_menu.name
    togdeck = make_menu_toggler(boardname, menuname, db)
    return MenuItem(menu_of_residence, idx, txt, togdeck,
                    closer, visible, interactive, db)


def make_calendar_toggler_menu_item(
        menu, item, txt, idx, closer, visible, interactive, db):
    if stringlike(item.dimension):
        dimname = item.dimension
    else:
        dimname = item.dimension.name
    itname = item.name
    togdeck = make_calendar_toggler(dimname, itname, db)
    return MenuItem(menu, idx, txt, togdeck,
                    closer, visible, interactive, db)
