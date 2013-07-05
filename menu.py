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


ON_CLICK_RE = re.compile("""([a-zA-Z0-9_]+)\((.*)\)""")


class MenuItem:
    """A thing in a menu that you can click to make something happen."""
    tables = [
        ('menu_item',
         {'board': "text default 'Physical'",
          'menu': 'text not null',
          'idx': 'integer not null',
          'text': 'text not null',
          'on_click': 'text not null',
          'closer': "boolean not null default 1",
          'visible': "boolean not null default 1",
          'interactive': "boolean not null default 1"},
         ('board', 'menu', 'idx'),
         {"board, menu": ("menu", "board, name")},
         [])]

    def __init__(self, db, board, menu, idx, text, on_click, closer,
                 visible, interactive):
        """Return a menu item in the given board, the given menu; at the given
index in that menu; with the given text; which executes the given
effect deck when clicked; closes or doesn't when clicked; starts
visible or doesn't; and starts interactive or doesn't.

With db, register in db's menuitemdict.

        """
        self.db = db
        self._board = str(board)
        self._menu = str(menu)
        self.idx = idx
        self._text = text
        self._on_click = on_click
        self.closer = closer
        self._visible = visible
        self.interactive = interactive
        self.grabpoint = None
        self.label = None
        self.oldstate = None
        self.newstate = None
        self.pressed = False
        self.tweaks = 0
        if self._board not in db.menuitemdict:
            db.menuitemdict[self._board] = {}
        if self._menu not in db.menuitemdict[self._board]:
            db.menuitemdict[self._board][self._menu] = []
        ptr = db.menuitemdict[self._board][self._menu]
        while len(ptr) <= self.idx:
            ptr.append(None)
        ptr[self.idx] = self

    def __getattr__(self, attrn):
        if attrn == 'board':
            return self.db.boarddict[self._board]
        elif attrn == 'menu':
            return self.db.menudict[self._board][self._menu]
        elif attrn == 'text':
            if self._text[0] == '@':
                return self.db.get_text(self._text[1:])
            else:
                return self._text
        elif attrn == 'gw':
            return self.board.gw
        elif attrn == 'hovered':
            return self.gw.hovered is self
        elif attrn == 'pressed':
            return self.gw.pressed is self
        elif attrn == 'visible':
            return self.menu.visible and self._visible
        elif attrn == 'window_left':
            return self.menu.window_left + self.menu.style.spacing
        elif attrn == 'window_right':
            return self.menu.window_right - self.menu.style.spacing
        elif attrn == 'width':
            return self.window_right - self.window_left
        elif attrn == 'height':
            return self.window_top - self.window_bot
        elif attrn == 'rx':
            return self.width / 2
        elif attrn == 'ry':
            return self.height / 2
        elif attrn == 'r':
            if self.rx > self.ry:
                return self.rx
            else:
                return self.ry
        else:
            raise AttributeError(
                "MenuItem instance has no such attribute: " +
                attrn)

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

    def unravel(self):
        db = self.db
        onclickmatch = re.match(ON_CLICK_RE, self._on_click)
        if onclickmatch is None:
            raise Exception("Couldn't understand this function for this menu item.")
        ocmg = onclickmatch.groups()
        if len(ocmg) == 2:
            self.func = self.db.func[ocmg[0]]
            self.arg = ocmg[1]
        elif len(ocmg) == 1:
            self.func = self.db.func[ocmg[0]]
            self.arg = None
        else:
            raise Exception("This is a weird expression to use for an on_click.")

    def onclick(self):
        """Look in self.db.func for an appropriately named function. Call that
function on myself and whatever other argument was specified.

        """
        if self.arg is None:
            return self.func(self)
        else:
            return self.func(self, self.arg)

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
            self._menu,
            self.idx,
            self.text,
            self.visible,
            self.interactive,
            self.grabpoint,
            self.pressed,
            self.tweaks)


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
        self.db = db
        self._board = str(board)
        self.name = name
        if self._board not in self.db.menudict:
            self.db.menudict[self._board] = {}
        self.db.menudict[self._board][self.name] = self
        self.left_prop = left
        self.bot_prop = bottom
        self.top_prop = top
        self.right_prop = right
        self._style = str(style)
        self.main_for_window = main_for_window
        self._visible = visible
        self.interactive = True
        self.grabpoint = None
        self.sprite = None
        self.oldstate = None
        self.newstate = None
        self.pressed = False
        self.freshly_adjusted = False
        self.tweaks = 0

    def __getattr__(self, attrn):
        if attrn == 'board':
            return self.db.boarddict[self._board]
        elif attrn == 'items':
            return self.db.menuitemdict[self._board][self.name]
        elif attrn == 'style':
            return self.db.styledict[self._style]
        elif attrn == 'gw':
            if not hasattr(self.board, 'gw'):
                return None
            else:
                return self.board.gw
        elif attrn == 'window':
            return self.gw.window
        elif attrn == 'hovered':
            return self.gw.hovered is self
        elif attrn == 'visible':
            return self._visible
        elif attrn == 'window_left':
            if self.gw is None:
                return 0
            else:
                return int(self.gw.width * self.left_prop)
        elif attrn == 'window_bot':
            if self.gw is None:
                return 0
            else:
                return int(self.gw.height * self.bot_prop)
        elif attrn == 'window_top':
            if self.gw is None:
                return 0
            else:
                return int(self.gw.height * self.top_prop)
        elif attrn == 'window_right':
            if self.gw is None:
                return 0
            else:
                return int(self.gw.width * self.right_prop)
        elif attrn == 'width':
            return self.window_right - self.window_left
        elif attrn == 'height':
            return self.window_top - self.window_bot
        elif attrn == 'rx':
            return int(
                (self.gw.width * self.right_prop -
                 self.gw.width * self.left_prop)
                / 2)
        elif attrn == 'ry':
            return int(
                (self.gw.height * self.top_prop -
                 self.gw.height * self.bot_prop)
                / 2)
        elif attrn == 'r':
            if self.rx > self.ry:
                return self.rx
            else:
                return self.ry
        else:
            raise AttributeError(
                "Menu instance has no such attribute: " +
                attrn)

    def unravel(self):
        """Dereference style and board; fetch items from db's menuitemdict;
and unravel style and all items."""
        db = self.db
        self.style.unravel()
        self.rowheight = self.style.fontsize + self.style.spacing
        bgi = self.style.bg_inactive.tup
        bga = self.style.bg_active.tup
        self.inactive_pattern = pyglet.image.SolidColorImagePattern(bgi)
        self.active_pattern = pyglet.image.SolidColorImagePattern(bga)
        boardname = str(self.board)
        for item in self.items:
            item.unravel()

    def adjust(self):
        """Assign absolute coordinates to myself and all my items."""
        i = 0
        for item in self.items:
            item.top_from_top = i * self.rowheight
            item.bot_from_top = item.top_from_top + self.rowheight
            item.window_top = self.window_top - item.top_from_top
            item.window_bot = item.window_top - self.rowheight
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

    def toggle_visibility(self):
        """Make myself visible if hidden, invisible if shown."""
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

    def get_state_tup(self):
        """Return a tuple containing everything you need to decide how to draw
me"""
        return (
            self,
            self.window_left,
            self.window_bot,
            self.window_top,
            self.window_right,
            self.style,
            self.main_for_window,
            self.visible,
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
