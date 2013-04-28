# This file is for the controllers for the things that show up on the
# screen when you play.
import pyglet
from util import SaveableMetaclass, dictify_row


__metaclass__ = SaveableMetaclass


class Color:
    """Color(red=0, green=0, blue=0, alpha=255) => color

    This is just a container class for the (red, green, blue, alpha)
tuples that Pyglet uses to identify colors.

    """
    tablenames = ["color"]
    coldecls = {"color":
                {'name': 'text',
                 'red': 'integer not null ',
                 'green': 'integer not null ',
                 'blue': 'integer not null ',
                 'alpha': 'integer default 255 '}}
    primarykeys = {"color": ("name",)}
    checks = {"color":
              ["red between 0 and 255",
              "green between 0 and 255",
              "blue between 0 and 255",
              "alpha between 0 and 255"]}

    def pull(self, db, keydicts):
        colornames = [keydict["name"] for keydict in keydicts]
        qryfmt = "SELECT {0} FROM color WHERE name IN ({1})"
        qms = ["?"] * len(colornames)
        qrystr = qryfmt.format(
            ", ".join(self.colnames["color"]),
            ", ".join(qms))
        db.c.execute(qrystr, colornames)
        return [
            dictify_row(self.colnames["color"], row)
            for row in db.c]

    def parse(self, rows):
        r = {}
        for row in rows:
            r[row["name"]] = row
        return r

    def __init__(self, name, red, green, blue, alpha, db=None):
        self.name = name
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha
        self.tup = (self.red, self.green, self.blue, self.alpha)
        self.pattern = pyglet.image.SolidColorImagePattern(self.tup)
        if db is not None:
            db.colordict[self.name] = self

    def __eq__(self, other):
        return (
            isinstance(other, Color) and
            self.name == other.name)

    def __hash__(self):
        return hash(self.name)

    def __iter__(self):
        return iter(self.tup)

    def __str__(self):
        return "(" + ", ".join(self.tup) + ")"


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
                    "onclick": ("effect", "name")}}

    def pull(self, db, keydicts):
        pass

    def pull_in_menus(self, db, menunames):
        qryfmt = "SELECT {0} FROM menu_item WHERE menu IN ({1})"
        qms = ["?"] * len(menunames)
        qrystr = qryfmt.format(
            self.colnamestr["menu_item"],
            ", ".join(qms))
        db.c.execute(qrystr, menunames)
        return [
            dictify_row(self.colnames["menu_item"], row)
            for row in db.c]

    def parse(self, rows):
        r = {}
        for row in rows:
            if row["menu"] not in r:
                r[row["menu"]] = {}
        r[row["menu"]][row["idx"]] = row

    def __init__(self, menu, idx, text, onclick, closer,
                 visible, interactive):
        self.menu = menu
        self.idx = idx
        self.text = text
        self.onclick = onclick
        self.closer = closer
        self.visible = visible
        self.interactive = interactive
        if isinstance(self.menu, str):
            self.hsh = hash(self.menu + str(self.idx))
        else:
            self.hsh = hash(self.menu.name + str(self.idx))

    def unravel(self, db):
        self.menu = db.menudict[self.menu]
        self.onclick = db.effectdict[self.onclick]
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

    def pull(self, db, keydicts):
        menunames = [keydict["name"] for keydict in keydicts]
        return self.pull_named(db, menunames)

    def pull_named(self, db, menunames):
        qryfmt = "SELECT {0} FROM menu WHERE name IN ({1})"
        qrystr = qryfmt.format(
            self.colnamestr["menu"],
            ", ".join(["?"] * len(menunames)))
        db.c.execute(qrystr, menunames)
        return [
            dictify_row(self.colnames["menu"], row)
            for row in db.c]

    def parse(self, rows):
        r = {}
        for row in rows:
            r[row["name"]] = row
        return r

    def combine(self, menudict, menuitemdict):
        for menu in menudict.itervalues():
            if "items" not in menu:
                menu["items"] = []
            mitems = menuitemdict[menu["name"]]
            i = 0
            while i < len(mitems):
                menu["items"].append(mitems[i])
                i += 1

    def __init__(self, name, left, bottom, top, right,
                 style, main_for_window, visible, db=None):
        self.name = name
        self.left = left
        self.bottom = bottom
        self.top = top
        self.right = right
        self.style = style
        self.main_for_window = main_for_window
        self.visible = visible
        self.items = []
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


class CalendarCell:
    # Being a block of time in a calendar, with or without an event in
    # it. This isn't stored in the database because really, why would
    # I store *empty calendar cells* in the database?
    __metaclass__ = type

    def __init__(self, col, start, end, color, text=""):
        self.col = col
        self.start = start
        self.end = end
        self.color = color
        self.text = text
        self.hsh = hash(str(start) + str(end) + text)

    def unravel(self, db):
        self.col = db.calendarcoldict[self.col]
        self.color = db.colordict[self.color]

    def __eq__(self, other):
        if not isinstance(other, CalendarCell):
            return False
        return (
            self.start == other.start and
            self.end == other.end and
            self.text == other.text)

    def __hash__(self):
        return self.hsh


class CalendarCol:
    # A board may have up to one of these. It may be toggled. It
    # may display any schedule or combination thereof, distinguishing
    # them by color or not at all. It has only one column.
    tablenames = ["calendar_col", "calendar_schedule_link"]
    coldecls = {"calendar_col":
                {"dimension": "text",
                 "item": "text",
                 "visible": "boolean",
                 "interactive": "boolean",
                 "rows_on_screen": "integer",
                 "scrolled_to": "integer",
                 "left": "float",
                 "top": "float",
                 "bot": "float",
                 "right": "float"},
                "calendar_schedule_link":
                {"calendar": "text",
                 "schedule": "text"}}
    primarykeys = {"calendar_col": ("dimension",),
                   "calendar_schedule_link": ("calendar", "schedule")}
    foreignkeys = {"calendar_col":
                   {"dimension": ("dimension", "name")},
                   "calendar_schedule":
                   {"calendar": ("calendar_col", "name"),
                    "schedule": ("schedule", "name")}}
    checks = {"calendar_col": ["rows_on_screen>0", "scrolled_to>=0"]}

    def __init__(self, dimension, item, visible, interactive,
                 rows_on_screen, scrolled_to,
                 left, top, bot, right, db=None):
        self.dimension = dimension
        self.item = item
        self.visible = visible
        self.interactive = interactive
        self.rows_on_screen = rows_on_screen
        self.scrolled_to = scrolled_to
        self.left = left
        self.top = top
        self.bot = bot
        self.right = right
        if db is not None:
            dimname = None
            itname = None
            if isinstance(self.dimension, str):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if isinstance(self.item, str):
                itname = self.item
            else:
                itname = self.item.name
            if dimname not in db.calendardict:
                db.calendardict[dimname] = {}
            db.calendardict[dimname][itname] = self

    def unravel(self, db):
        self.dimension = db.dimensiondict[self.dimension]
        self.item = db.itemdict[self.dimension.name][self.item]
        self.schedule = db.scheduledict[self.dimension.name][self.item.name]

    def __eq__(self, other):
        # not checking for gw this time, because there can only be one
        # CalendarWall per Board irrespective of if it's got a window
        # or not.
        return (
            isinstance(other, CalendarCol) and
            other.dimension == self.dimension)

    def __hash__(self):
        return self.hsh

    def no_window(self):
        raise Exception("I can't do this without a GameWindow. "
                        "Set %s.gw to a GameWindow object." % (self.__name__,))

    def getleft(self):
        if not hasattr(self, 'gw'):
            self.no_window()
        return self.gw.mainmenu.getright() + self.gutter

    def getright(self):
        if not hasattr(self, 'gw'):
            self.no_window()
        return self.gw.window.width - self.gutter

    def gettop(self):
        if not hasattr(self, 'gw'):
            self.no_window()
        return self.gw.window.height - self.gutter

    def getbot(self):
        if not hasattr(self, 'gw'):
            self.no_window()
        return self.gutter

    def getwidth(self):
        return self.getright() - self.getleft()

    def getheight(self):
        return self.gettop() - self.getbot()


class Spot:
    """Controller for the icon that represents a Place.

    Spot(place, x, y, spotgraph) => a Spot representing the given
    place; at the given x and y coordinates on the screen; in the
    given graph of Spots. The Spot will be magically connected to the other
    Spots in the same way that the underlying Places are connected."""
    tablenames = ["spot"]
    coldecls = {"spot":
                {"dimension": "text",
                 "place": "text",
                 "img": "text",
                 "x": "integer",
                 "y": "integer",
                 "visible": "boolean",
                 "interactive": "boolean"}}
    primarykeys = {"spot": ("dimension", "place")}
    foreignkeys = {"spot":
                   {"dimension, place": ("place", "dimension, name"),
                    "img": ("img", "name")}}

    def __init__(self, dimension, place, img, x, y,
                 visible, interactive, db=None):
        self.dimension = dimension
        self.place = place
        self.img = img
        self.x = x
        self.y = y
        self.visible = visible
        self.interactive = interactive
        if db is not None:
            dimname = None
            placename = None
            if isinstance(self.dimension, str):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if isinstance(self.place, str):
                placename = self.place
            else:
                placename = self.place.name
            if dimname not in db.spotdict:
                db.spotdict[dimname] = {}
            db.spotdict[dimname][placename] = self

    def __repr__(self):
        return "spot(%i,%i)->%s" % (self.x, self.y, str(self.place))

    def __eq__(self, other):
        return (
            isinstance(other, Spot) and
            self.dimension == other.dimension and
            self.name == other.name)

    def __hash__(self):
        return self.hsh

    def getleft(self):
        return self.x - self.r

    def getbot(self):
        return self.y - self.r

    def gettop(self):
        return self.y + self.r

    def getright(self):
        return self.x + self.r

    def getcenter(self):
        return (self.x, self.y)

    def gettup(self):
        return (self.img, self.getleft(), self.getbot())

    def is_visible(self):
        return self.visible

    def is_interactive(self):
        return self.interactive

    def onclick(self, button, modifiers):
        pass

    def dropped(self, x, y, button, modifiers):
        self.grabpoint = None

    def move_with_mouse(self, x, y, dx, dy, buttons, modifiers):
        if self.grabpoint is None:
            self.grabpoint = (x - self.x, y - self.y)
        (grabx, graby) = self.grabpoint
        self.x = x - grabx + dx
        self.y = y - graby + dy


class Pawn:
    """A token to represent something that moves about between Places.

    Pawn(thing, place, x, y) => pawn

    thing is the game-logic item that the Pawn represents.
    It should be of class Thing.

    place is the name of a Place that is already represented by a Spot
    in the same Board. pawn will appear here to begin with. Note that
    the Spot need not be visible. You can supply the Place name for an
    invisible spot to make it appear that a Pawn is floating in that
    nebulous dimension between Places.

    """
    tablenames = ["pawn"]
    coldecls = {"pawn":
                {"dimension": "text",
                 "thing": "text",
                 "img": "text",
                 "visible": "boolean",
                 "interactive": "boolean"}}
    primarykeys = {"pawn": ("dimension", "thing")}
    fkeydict = {"pawn":
                {"img": ("img", "name"),
                 "dimension, thing": ("thing", "dimension, name")}}

    def __init__(self, dimension, thing, img, visible, interactive, db=None):
        self.dimension = dimension
        self.thing = thing
        self.img = img
        self.visible = visible
        self.interactive = interactive
        if db is not None:
            dimname = None
            thingname = None
            if isinstance(self.dimension, str):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if isinstance(self.thing, str):
                thingname = self.thing
            else:
                thingname = self.thing.name
            if dimname not in db.pawndict:
                db.pawndict[dimname] = {}
            db.pawndict[dimname][thingname] = self

    def __eq__(self, other):
        return (
            isinstance(other, Pawn) and
            self.dimension == other.dimension and
            self.thingname == other.thingname)

    def __hash__(self):
        return self.hsh

    def getcoords(self):
        # Assume I've been provided a spotdict. Use it to get the
        # spot's x and y, as well as that of the spot for the next
        # step on my thing's journey. If my thing doesn't have a
        # journey, return the coords of the spot. If it does, return a
        # point between the start and end spots in proportion to the
        # journey's progress. If there is no end spot, behave as if
        # there's no journey.
        #
        # I can't assume that img is an actual image because the
        # loader instantiates things before assigning them data that's
        # not strings or numbers. Calculate self.rx to save some
        # division.
        if not hasattr(self, 'rx'):
            self.rx = self.img.width / 2
        if not hasattr(self, 'ry'):
            self.ry = self.img.height / 2
        if hasattr(self.thing, 'journey') and\
           self.thing.journey.stepsleft() > 0:
            j = self.thing.journey
            port = j.getstep(0)
            start = port.orig.spot
            end = port.dest.spot
            hdist = end.x - start.x
            vdist = end.y - start.y
            p = j.progress
            x = start.x + hdist * p
            y = start.y + vdist * p
            return (x, y)
        else:
            ls = self.thing.location.spot
            return (ls.x, ls.y)

    def getcenter(self):
        (x, y) = self.getcoords()
        return (x, y + self.ry)

    def getleft(self):
        return self.getcoords()[0] - self.rx

    def getright(self):
        return self.getcoords()[0] + self.rx

    def gettop(self):
        return self.getcoords()[1] + self.img.height

    def getbot(self):
        return self.getcoords()[1]

    def is_visible(self):
        return self.visible

    def is_interactive(self):
        return self.interactive

    def onclick(self, button, modifiers):
        pass


class Img:
    tablenames = ["img"]
    coldecls = {"img":
                {"name": "text",
                 "path": "text",
                 "rltile": "boolean"}}
    primarykeys = {"img": ("name",)}
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

    def pull_named(self, db, name):
        qryfmt = "SELECT {0} FROM board, boardmenu WHERE "
        colnames = self.colnames["board"] + ["menu"]
        boardcols = ["board." + col for col in self.colnames["board"]]
        qrycols = boardcols + ["boardmenu.menu"]
        qrystr = qryfmt.format(", ".join(qrycols))
        db.c.execute(qrystr, (name,))
        return [
            dictify_row(colnames, row) for row in db.c]

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

    def __init__(self, dimension, width, height, wallpaper, db=None):
        self.dimension = dimension
        self.width = width
        self.height = height
        self.wallpaper = wallpaper
        if db is not None:
            if isinstance(self.dimension, str):
                db.boarddict[self.dimension] = self
            else:
                db.boarddict[self.dimension.name] = self

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


class Style:
    tablenames = ["style"]
    coldecls = {"style":
                {"name": "text",
                 "fontface": "text not null",
                 "fontsize": "integer not null",
                 "spacing": "integer default 6",
                 "bg_inactive": "text not null",
                 "bg_active": "text not null",
                 "fg_inactive": "text not null",
                 "fg_active": "text not null"}}
    primarykeys = {"style": ("name",)}
    foreignkeys = {"style":
                   {"bg_inactive": ("color", "name"),
                    "bg_active": ("color", "name"),
                    "fg_inactive": ("color", "name"),
                    "fg_active": ("color", "name")}}

    def __init__(self, name, fontface, fontsize, spacing,
                 bg_inactive, bg_active, fg_inactive, fg_active,
                 db=None):
        self.name = name
        self.fontface = fontface
        self.fontsize = fontsize
        self.spacing = spacing
        self.bg_inactive = bg_inactive
        self.bg_active = bg_active
        self.fg_inactive = fg_inactive
        self.fg_active = fg_active
        if db is not None:
            db.styledict[self.name] = self

    def __eq__(self, other):
        return (
            isinstance(other, Style) and
            self.name == other.name)

    def __hash__(self):
        return self.hsh
