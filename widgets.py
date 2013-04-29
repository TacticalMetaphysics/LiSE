# This file is for the controllers for the things that show up on the
# screen when you play.
import pyglet
from util import SaveableMetaclass, dictify_row
import world


__metaclass__ = SaveableMetaclass

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


