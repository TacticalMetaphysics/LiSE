# This file is for the controllers for the things that show up on the
# screen when you play.
import pyglet
from saveload import SaveableMetaclass


__metaclass__ = SaveableMetaclass


class Color:
    """Color(red=0, green=0, blue=0, alpha=255) => color

    This is just a container class for the (red, green, blue, alpha)
tuples that Pyglet uses to identify colors.

    """
    maintab = "color"
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

    def setup(self):
        rowdict = self.tabdict["color"][0]
        self.name = rowdict["name"]
        self.red = rowdict["red"]
        self.green = rowdict["green"]
        self.blue = rowdict["blue"]
        self.alpha = rowdict["alpha"]
        self.tup = (self.red, self.green, self.blue, self.alpha)
        self.pattern = pyglet.image.SolidColorImagePattern(self.tup)

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
    coldecls = {'menuitem':
                {'menu': 'text',
                 'idx': 'integer',
                 'text': 'text',
                 'onclick': 'text',
                 'onclick_arg': 'text',
                 'closer': 'boolean',
                 'visible': 'boolean',
                 'interactive': 'boolean'}}
    primarykeys = {'menuitem': ('menu', 'idx')}
    foreignkeys = {'menuitem': {"menu": ("menu", "name")}}

    def setup(self):
        db = self.db
        rowdict = self.tabdict["menu"][0]
        self.menuname = rowdict["menu"]
        self.idx = rowdict["idx"]
        self.text = rowdict["text"]
        self.onclick_core = db.func[rowdict["onclick"]]
        self.onclick_arg = rowdict["onclick_arg"]
        self.closer = rowdict["closer"]
        self.visible = rowdict["visible"]
        self.interactive = rowdict["interactive"]
        self.hsh = hash(self.menuname + str(self.idx))

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
    maintab = "menu"
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

    def setup(self):
        rowdict = self.tabdict["menu"][0]
        db = self.db
        self.name = rowdict["name"]
        self.left = rowdict["left"]
        self.bottom = rowdict["bottom"]
        self.top = rowdict["top"]
        self.right = rowdict["right"]
        self.style = db.styledict[rowdict["style"]]
        self.visible = rowdict["visible"]
        self.main_for_window = rowdict["main_for_window"]
        self.items = []
        # In order to actually draw these things you need to give them
        # an attribute called window, and it should be a window of the
        # pyglet kind. It isn't in the constructor because that would
        # make loading inconvenient.

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


class CalendarBrick:
    # Being a block of time in a calendar, with or without an event in
    # it. This isn't stored in the database because really, why would
    # I store *empty calendar cells* in the database?
    def __init__(self, start, end, color, text=""):
        self.start = start
        self.end = end
        self.color = color
        self.text = text
        self.hsh = hash(str(start) + str(end) + text)

    def __eq__(self, other):
        if not isinstance(other, CalendarBrick):
            return False
        return (
            self.start == other.start and
            self.end == other.end and
            self.text == other.text)

    def __hash__(self):
        return self.hsh


class CalendarWall:
    # A board may have up to one of these. It may be toggled. It
    # may display any schedule or combination thereof, distinguishing
    # them by color or not at all. It has only one column.
    coldecls = {"calendar_wall":
                {"dimension": "text",
                 "visible": "boolean",
                 "interactive": "boolean",
                 "rows_on_screen": "integer",
                 "scrolled_to": "integer",
                 "gutter": "integer"},
                "calendar_schedule":
                {"calendar": "text",
                 "schedule": "text"}}
    primarykeys = {"calendar_wall": ("dimension",),
                   "calendar_schedule": ("calendar", "schedule")}
    foreignkeys = {"calendar_wall":
                   {"dimension": ("dimension", "name")},
                   "calendar_schedule":
                   {"calendar": ("calendar", "name"),
                    "schedule": ("schedule", "name"),
                    "color": ("color", "name")}}
    checks = {"calendar_wall": ["rows_on_screen>0", "scrolled_to>=0"]}

    def __init__(self, db, rowdict):
        # TODO pull in schedules.
        #
        # I also need the window, but I'm not adding that yet because
        # it's not instantiated at load time.
        self.visible = rowdict["visible"]
        self.interactive = rowdict["interactive"]
        self.screenful = rowdict["rows_on_screen"]
        self.scrolled = rowdict["scrolled_to"]
        self.gutter = rowdict["gutter"]
        self.hsh = hash(self.dimension)
        self.left = rowdict["left"]
        self.right = rowdict["right"]
        self.top = rowdict["top"]
        self.bottom = rowdict["bottom"]
        self.dimension = rowdict["dimension"]

    def __eq__(self, other):
        # not checking for gw this time, because there can only be one
        # CalendarWall per Board irrespective of if it's got a window
        # or not.
        return (
            isinstance(other, CalendarWall) and
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

    def __init__(self, db, rowdict):
        self.dimension = rowdict["dimension"]
        self.place = db.placedict[self.dimension][rowdict["place"]]
        self.x = rowdict["x"]
        self.y = rowdict["y"]
        self.img = db.imgdict[rowdict["img"]]
        self.visible = rowdict["visible"]
        self.interactive = rowdict["interactive"]
        self.r = self.img.width / 2
        self.grabpoint = None
        self.hsh = hash(self.dimension + self.place.name)

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

    def __init__(self, db, rowdict):
        self.dimension = rowdict["dimension"]
        self.thingname = rowdict["thing"]
        self.thing = db.thingdict[self.dimension][self.thingname]
        self.img = db.imgdict[rowdict["img"]]
        self.visible = rowdict["visible"]
        self.interactive = rowdict["interactive"]
        self.r = self.img.width / 2
        self.hsh = hash(self.dimension + self.thing.name)

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


class Board:
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

    def __init__(self, db, rowdict):
        self.dimension = rowdict["dimension"]
        self.width = rowdict["width"]
        self.height = rowdict["height"]
        self.img = db.imgdict[rowdict["wallpaper"]]
        self.spots = db.spotdict[self.dimension].viewvalues()
        self.pawns = db.pawndict[self.dimension].viewvalues()
        self.menus = db.boardmenudict[self.dimension].viewvalues()
        self.hsh = hash(self.dimension)

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

    def __init__(self, db, rowdict):
        self.name = rowdict["name"]
        self.hsh = hash(self.name)
        self.fontface = rowdict["fontface"]
        self.fontsize = rowdict["fontsize"]
        self.spacing = rowdict["spacing"]
        self.bg_inactive = db.colordict[rowdict["bg_inactive"]]
        self.bg_active = db.colordict[rowdict["bg_active"]]
        self.fg_inactive = db.colordict[rowdict["fg_inactive"]]
        self.fg_active = db.colordict[rowdict["fg_active"]]

    def __eq__(self, other):
        return (
            isinstance(other, Style) and
            self.name == other.name)

    def __hash__(self):
        return self.hsh
