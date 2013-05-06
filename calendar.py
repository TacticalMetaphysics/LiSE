from util import SaveableMetaclass, stringlike


"""User's view on a given item's schedule."""


class CalendarCell:
    """A block of time in a calendar.

Every calendar cell must be in a CalendarCol. Everything else in the
constructor may be chosen arbitrarily, although it would be most
helpful to match the CalendarCell's values with those of an Event
instance.

Calendar cells are not stored in the database. Many of them are
created on the fly to fill in space on the calendar where/when nothing
is happening.

    """

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
    """A single-column visual representation of a schedule.

As schedules are uniquely associated with Item objects, so are the
calendar-columns representing those schedules. They are drawn by
fetching events in the time period that's on screen, instantiating
CalendarCells for those, and drawing boxes to represent those
cells.

    """
    __metaclass__ = SaveableMetaclass
    tablenames = ["calendar_col"]
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
                 "right": "float"}}
    primarykeys = {"calendar_col": ("dimension", "item")}
    foreignkeys = {"calendar_col":
                   {"dimension, item": ("item", "dimension, name")}}
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
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if stringlike(self.item):
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
