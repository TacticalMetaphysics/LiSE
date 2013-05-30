from util import SaveableMetaclass, dictify_row, stringlike
from effect import read_effect_decks
from effect import (
    EffectDeck,
    make_menu_toggler,
    make_calendar_toggler)
import re
import pyglet


"""Simple menu widgets"""


__metaclass__ = SaveableMetaclass


MENU_TOGGLER_RE = re.compile("toggle_menu\((.*)\)")
CALENDAR_TOGGLER_RE = re.compile("toggle_calendar\((.*)\)")


class MenuItem:
    """A thing in a menu that you can click to make something happen."""
    tables = [
        ('menu_item',
         {'board': "text default 'Physical'",
          'menu': 'text not null',
          'idx': 'integer not null',
          'text': 'text not null',
          'effect_deck': 'text not null',
          'closer': "boolean not null default 1",
          'visible': "boolean not null default 1",
          'interactive': "boolean not null default 1"},
         ('board', 'menu', 'idx'),
         {"board, menu": ("menu", "board, name"),
          "effect_deck": ("effect_deck_link", "deck")},
         [])]

    def __init__(self, db, board, menu, idx, text, effect_deck, closer,
                 visible, interactive):
        """Return a menu item in the given board, the given menu; at the given
index in that menu; with the given text; which executes the given
effect deck when clicked; closes or doesn't when clicked; starts
visible or doesn't; and starts interactive or doesn't.

With db, register in db's menuitemdict.

        """
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
        self.db = db

    def unravel(self):
        """Dereference the board, the menu, the effect deck, and the text if
it starts with an @ character."""
        db = self.db
        if stringlike(self.board):
            self.board = db.boarddict[self.board]
        if stringlike(self.menu):
            self.menu = db.menudict[self.board.dimension.name][self.menu]
        self.parse_effect_deck()
        while len(self.menu.items) < self.idx:
            self.menu.items.append(None)
        if self.text[0] == "@":
            self.text = db.get_text(self.text[1:])

    def onclick(self, button, modifiers):
        """Event handler that fires the effect deck."""
        self.effect_deck.do()

    def set_hovered(self):
        """Become hovered if I'm not already."""
        if not self.hovered:
            self.hovered = True
            self.tweaks += 1

    def unset_hovered(self):
        """If I'm being hovered, stop it."""
        if self.hovered:
            self.hovered = False
            self.tweaks += 1

    def set_pressed(self):
        """Become pressed if I'm not already."""
        pass

    def unset_pressed(self):
        """If I'm being pressed, stop it."""
        pass

    def __eq__(self, other):
        """Compare the menu and the idx to see if these menu items ought to be
the same."""
        return (
            isinstance(other, MenuItem) and
            self.menu == other.menu and
            self.idx == other.idx)

    def __gt__(self, other):
        """Compare the text"""
        if isinstance(other, str):
            return self.text > other
        return self.text > other.text

    def __ge__(self, other):
        """Compare the text"""
        if isinstance(other, str):
            return self.text >= other
        return self.text >= other.text

    def __lt__(self, other):
        """Compare the text"""
        if isinstance(other, str):
            return self.text < other
        return self.text < other.text

    def __le__(self, other):
        """Compare the text"""
        if isinstance(other, str):
            return self.text <= other
        return self.text <= other.text

    def __repr__(self):
        """Show my text"""
        return self.text

    def getcenter(self):
        """Return a pair with my center's x and y coords"""
        return (self.get_center_x(), self.get_center_y())

    def get_center_x(self):
        """Return the x at my center"""
        return self.getleft() + self.getrx()

    def get_center_y(self):
        """Return the y at my center"""
        return self.getbot() + self.getry()

    def getleft(self):
        """Return the x at my leftmost edge"""
        return self.menu.getleft() + self.menu.style.spacing

    def getright(self):
        """Return the x at my rightmost edge"""
        return self.menu.getright() - self.menu.style.spacing

    def gettop(self):
        """Return the y at my upper edge"""
        return self.top

    def getbot(self):
        """Return the y at my lower edge"""
        return self.bot

    def getwidth(self):
        """How many pixels wide am I?"""
        return self.getright() - self.getleft()

    def getheight(self):
        """How many pixels tall am I?"""
        return self.menu.style.fontsize + self.menu.style.spacing

    def getrx(self):
        """Return half my width"""
        return self.getwidth() / 2

    def getry(self):
        """Return half my height"""
        return self.getheight() / 2

    def toggle_visibility(self):
        """Become visible if invisible or vice versa"""
        self.visible = not self.visible
        self.tweaks += 1

    def hide(self):
        """Become invisible"""
        if self.visible:
            self.toggle_visibility()

    def show(self):
        """Become visible"""
        if not self.visible:
            self.toggle_visibility()

    def get_state_tup(self):
        """Return a tuple containing everything that's relevant to deciding
just how to display this widget"""
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

    def parse_effect_deck(self):
        """Dereference the effect deck, possibly making a new one if it's
named a certain way."""
        db = self.db
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
                self.effect_deck = make_menu_toggler(db, b, m)
            else:
                if stringlike(self.menu.board):
                    boardname = self.menu.board
                else:
                    if stringlike(self.menu.board.dimension):
                        boardname = self.menu.board.dimension
                    else:
                        boardname = self.menu.board.dimension.name
                self.effect_deck = make_menu_toggler(db, boardname, menuspec)
                return
        caltogmatch = re.match(CALENDAR_TOGGLER_RE, efd)
        if caltogmatch is not None:
            calspec = caltogmatch.groups()[0]
            calspec_split = calspec.split(".")
            if len(calspec_split) == 2:
                (dimn, itn) = calspec_split
                self.effect_deck = make_calendar_toggler(db, dimn, itn)
            else:
                if stringlike(self.menu.board):
                    dimname = self.menu.board
                else:
                    if stringlike(self.menu.board.dimension):
                        dimname = self.menu.board.dimension
                    else:
                        dimname = self.menu.board.dimension.name
                self.effect_deck = make_calendar_toggler(db, dimname, calspec)
            return
        if efd in db.effectdeckdict:
            self.effect_deck = db.effectdeckdict[efd]

    def is_visible(self):
        """Can you see me?"""
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
    """Container for MenuItems; not interactive unto itself."""
    tables = [
        ('menu',
         {'board': "text not null default 'Physical'",
          'name': 'text not null',
          'left': "float not null default 0.1",
          'bottom': "float not null default 0.0",
          'top': 'float not null default 1.0',
          'right': 'float not null default 0.2',
          'style': "text not null default 'SmallDark'",
          "main_for_window": "boolean not null default 0",
          "visible": "boolean not null default 0"},
         ('name',),
         {},
         [])]
    interactive = True

    def get_tabdict(self):
        return {
            "menu": self.get_rowdict(),
            "menu_item": [it.get_rowdict() for it in self.items]
        }

    def __init__(self, db, board, name, left, bottom, top, right, style,
                 main_for_window, visible):
        """Return a menu in the given board, with the given name, bounds,
style, and flags main_for_window and visible.

Bounds are proportional with respect to the lower left corner of the
window. That is, they are floats, never below 0.0 nor above 1.0, and
they express a portion of the window's width or height.

main_for_window prevents the menu from ever being hidden. visible
determines if you can see it at the moment.

With db, register with db's menudict.

        """
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
        if stringlike(self.board):
            boardname = self.board
        else:
            boardname = self.board.name
        if boardname not in db.menudict:
            db.menudict[boardname] = {}
        db.menudict[boardname][self.name] = self
        self.db = db

    def unravel(self):
        """Dereference style and board; fetch items from db's menuitemdict;
and unravel style and all items."""
        db = self.db
        if stringlike(self.style):
            self.style = db.styledict[self.style]
        self.style.unravel()
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
            item.unravel()

    def set_gw(self, gw):
        """Remember the given gamewindow for use in later graphics
calculations. Then do the calculations once."""
        self.gw = gw
        self.adjust()

    def adjust(self):
        """Assign absolute coordinates to myself and all my items."""
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
        """Return true if the names and boards match"""
        return (
            self.name == other.name and
            self.board == other.board)

    def __getitem__(self, i):
        """Return an item herein"""
        return self.items[i]

    def __setitem__(self, i, to):
        """Set a menuitem"""
        self.items[i] = to

    def __delitem__(self, i):
        """Delete a menuitem"""
        return self.items.__delitem__(i)

    def getstyle(self):
        """Return my style"""
        return self.style

    def getleft(self):
        """Return the x at my left edge"""
        return self.left_abs

    def getbot(self):
        """Return the y at my bottom edge"""
        return self.bot_abs

    def gettop(self):
        """Return the y at my top edge"""
        return self.top_abs

    def getright(self):
        """Return the x at my right edge"""
        return self.right_abs

    def getcenter(self):
        """Return a pair, being coordinates of my center point"""
        fx = self.center_abs[0]
        fy = self.center_abs[1]
        return (fx, fy)

    def getwidth(self):
        """Return width in pixels"""
        return self.width_abs

    def getheight(self):
        """Return height in pixels"""
        return self.height_abs

    def getrx(self):
        """Return half width in pixels"""
        return self.rx_abs

    def getry(self):
        """Return half height in pixels"""
        return self.ry_abs

    def is_visible(self):
        """Can you see me?"""
        return self.visible

    def is_interactive(self):
        """Can you touch me?"""
        return self.interactive

    def toggle_visibility(self):
        """Make myself visible if hidden, invisible if shown."""
        print "toggling visibility of menu {0}".format(self.name)
        self.visible = not self.visible
        self.tweaks += 1

    def show(self):
        """Show myself if I am hidden"""
        if not self.visible:
            self.toggle_visibility()

    def hide(self):
        """Hide myself if I am visible"""
        if self.visible:
            self.toggle_visibility()

    def onclick(self, button, modifiers):
        """If one of my items is hovered, activate it"""
        if self.hovered is not None:
            self.hovered.onclick(button, modifiers)

    def set_hovered(self):
        """Make myself hovered"""
        pass

    def unset_hovered(self):
        """Make myself not hovered"""
        pass

    def set_pressed(self):
        """Make myself pressed"""
        pass

    def unset_pressed(self):
        """Make myself not pressed"""
        pass

    def get_state_tup(self):
        """Return a tuple containing everything you need to decide how to draw
me"""
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
    """Read all items in the named menus."""
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


def unravel_items(itd):
    """Unravel items from a given board"""
    for it in itd.itervalues():
        it.unravel()
    return itd


def unravel_items_in_menus(mitd):
    """Unravel items from read_items_in_menus"""
    for its in mitd.itervalues():
        unravel_items(its)
    return mitd


def load_items_in_menus(db, menus):
    """Load items in the named menus. Return a 2D dict keyed by menu, then
index."""
    return unravel_items_in_menus(read_items_in_menus(db, menus))


menu_qcols = ["menu." + coln for coln in Menu.colns]
menu_item_qvals = (
    ["menu_item.idx"] +
    ["menu_item." + valn for valn in MenuItem.valns])
mbqcols = menu_qcols + menu_item_qvals
mbcols = Menu.colns + ["idx"] + MenuItem.valns
menu_board_qryfmt = (
    "SELECT {0} FROM menu JOIN menu_item ON "
    "menu.board=menu_item.board AND "
    "menu.name=menu_item.menu WHERE menu.board IN ({1})".format(
        ", ".join(mbqcols), "{0}"))


def read_menus_in_boards(db, boards):
    """Read all menus in the given boards, and all items therein; but
don't unravel anything just yet.

Return a 2D dict keyed first by board dimension name, then by menu name.

    """
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
        MenuItem(**menuitemrd)
    return r


def unravel_menus(md):
    """Unravel a dict of menus keyed by name"""
    for menu in md.itervalues():
        menu.unravel()
    return md


def unravel_menus_in_boards(bmd):
    """Unravel a 2D dict of menus keyed by board dimension name, then menu
name"""
    for menus in bmd.itervalues():
        unravel_menus(menus)
    return bmd


def load_menus_in_boards(db, boards):
    """Load all menus in the given boards.

Return them in a 2D dict keyed first by board dimension name, then by
menu name.

    """
    return unravel_menus_in_boards(read_menus_in_boards(db, boards))


def make_menu_toggler_menu_item(
        db, target_menu, menu_of_residence, idx, txt,
        closer, visible, interactive):
    """Return a MenuItem that toggles some target_menu other than the
menu_of_residence it's in."""
    if stringlike(menu_of_residence.board):
        boardname = menu_of_residence.board
    else:
        boardname = menu_of_residence.board.dimension.name
    if stringlike(target_menu):
        menuname = target_menu
    else:
        menuname = target_menu.name
    togdeck = make_menu_toggler(db, boardname, menuname)
    return MenuItem(db, menu_of_residence, idx, txt, togdeck,
                    closer, visible, interactive)


def make_calendar_toggler_menu_item(
        menu, item, txt, idx, closer, visible, interactive, db):
    """Return a MenuItem that toggles the calendar column for a particular
item."""
    if stringlike(item.dimension):
        dimname = item.dimension
    else:
        dimname = item.dimension.name
    itname = item.name
    togdeck = make_calendar_toggler(db, dimname, itname)
    return MenuItem(db, menu, idx, txt, togdeck,
                    closer, visible, interactive)
