from util import SaveableMetaclass, stringlike, dictify_row
from pyglet.image import SolidColorImagePattern as color_pattern
from style import read_styles


"""User's view on a given item's schedule.

Usually there should be only one calendar per board, but it can switch
between showing various schedules, or even show many in parallel.

"""


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

    def __init__(self, calendar, start, end, empty, text=""):
        self.calendar = calendar
        self.start = start
        self.end = end
        self.empty = empty
        self.text = text
        self.oldstate = None
        self.newstate = None
        self.visible = True
        self.interactive = True
        self.inactive_pattern = color_pattern(calendar.style.bg_inactive.tup)
        self.active_pattern = color_pattern(calendar.style.bg_active.tup)

    def unravel(self, db):
        if stringlike(self.calendar):
            self.calendar = db.calendarcoldict[self.calendar]
        if stringlike(self.color):
            self.color = db.colordict[self.color]

    def __eq__(self, other):
        if not isinstance(other, CalendarCell):
            return False
        return (
            self.start == other.start and
            self.end == other.end and
            self.text == other.text)

    def __len__(self):
        return self.end - self.start

    def get_state_tup(self):
        return (
            hash(self.calendar.get_state_tup()),
            self.start,
            self.end,
            self.empty,
            self.text)

    def gettop(self):
        return self.top

    def getbot(self):
        return self.bot

    def getleft(self):
        return self.calendar.celleft

    def getright(self):
        return self.calendar.celright

    def getwidth(self):
        return self.calendar.celwidth

    def getheight(self):
        return self.gettop() - self.getbot()

    def label_bot(self):
        return self.gettop() - self.style.fontsize - self.style.spacing

    def getstart(self):
        if hasattr(self, 'event'):
            return self.event.start
        elif hasattr(self, 'start'):
            return self.start
        else:
            return None

    def getend(self):
        if self.event is not None:
            return self.event.start + self.event.length
        elif hasattr(self, 'start') and hasattr(self, 'length'):
            return self.start + self.length
        elif hasattr(self, 'end'):
            return self.end
        else:
            return None

    def toggle_visibility(self):
        self.visible = not self.visible
        self.tweaks += 1

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def hide(self):
        if self.visible:
            self.toggle_visibility()

    def is_visible(self):
        return self.visible and self.gettop() > 0


class CalendarCol:
    """A single-column visual representation of a schedule.

As schedules are uniquely associated with Item objects, so are the
calendar-columns representing those schedules. They are drawn by
fetching events in the time period that's on screen, instantiating
CalendarCells for those, and drawing boxes to represent those
cells.

    """
    __metaclass__ = SaveableMetaclass
    tables = [
        ("calendar_col",
         {"dimension": "text",
          "item": "text",
          "visible": "boolean",
          "interactive": "boolean",
          "rows_on_screen": "integer",
          "scrolled_to": "integer",
          "left": "float",
          "top": "float",
          "bot": "float",
          "right": "float",
          "style": "text"},
         ("dimension", "item"),
         {"dimension, item": ("item", "dimension, name"),
          "style": ("style", "name")},
         ["rows_on_screen>0", "scrolled_to>=0"]
         )]

    def __init__(self, dimension, item, visible, interactive,
                 rows_on_screen, scrolled_to,
                 left, top, bot, right, style,
                 db=None):
        self.dimension = dimension
        self.item = item
        self.visible = visible
        self.toggles = 0
        self.interactive = interactive
        self.rows_on_screen = rows_on_screen
        self.scrolled_to = scrolled_to
        self.left = left
        self.top = top
        self.bot = bot
        self.right = right
        self.height = self.top - self.bot
        self.width = self.right - self.left
        self.style = style
        self.oldstate = None
        self.newstate = None
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

    def toggle_visibility(self):
        self.visible = not self.visible
        self.toggles += 1

    def hide(self):
        if self.visible:
            self.toggle_visibility()

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def unravel(self, db):
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        dn = self.dimension.name
        if stringlike(self.item):
            self.item = db.itemdict[dn][self.item]
        if stringlike(self.style):
            self.style = db.styledict[self.style]
        self.style.unravel(db)
        self.inactive_pattern = color_pattern(self.style.bg_inactive.tup)
        self.active_pattern = color_pattern(self.style.bg_active.tup)
        if not hasattr(self, 'schedule'):
            self.schedule = self.item.schedule
        else:
            assert(self.item.schedule == self.schedule)
        if self.visible:
            self.show()
        else:
            self.hide()

    def set_cal(self, cal):
        if cal is not self.cal:
            self.cal = cal
            self.adjust()

    def gettop(self):
        return self.top_abs

    def getbot(self):
        return self.bot_abs

    def getleft(self):
        return self.left_abs

    def getright(self):
        return self.right_abs

    def getwidth(self):
        return self.width_abs

    def getheight(self):
        return self.height_abs

    def adjust(self):
        """Create calendar cells for all events in the schedule.

Cells already here will be reused."""
        schevs = iter(self.item.schedule)
        for ev in schevs:
            if ev.name not in self.cells:
                self.cells[ev.name] = CalendarCell(self, ev)
        for k in self.cells.iterkeys():
            if k not in self.item.schedule.events:
                try:
                    ptr.sprite.delete()
                except AttributeError:
                    pass
                try:
                    ptr.label.delete()
                except AttributeError:
                    pass
        self.tweaks += 1


    def __eq__(self, other):
        return (
            isinstance(other, CalendarCol) and
            other.dimension == self.dimension and
            other.item == self.item)

    def get_state_tup(self):
        return (
            self.dimension.name,
            self.item.name,
            self.visible,
            self.interactive,
            self.rows_on_screen,
            self.scrolled_to,
            self.toggles)


cal_dim_qryfmt = (
    "SELECT {0} FROM calendar_col WHERE dimension IN ({1})".format(
        ", ".join(CalendarCol.colns), "{0}"))


def read_calendars_in_dimensions(db, names):
    qryfmt = cal_dim_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, names)
    r = {}
    stylenames = set()
    for name in names:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, CalendarCol.colns)
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["item"]] = CalendarCol(**rowdict)
        stylenames.add(rowdict["style"])
    read_styles(db, list(stylenames))
    return r
