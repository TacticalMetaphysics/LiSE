from util import SaveableMetaclass, stringlike, dictify_row
from pyglet.image import SolidColorImagePattern as color_pattern


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

    def __init__(self, calendar, start, end, empty, text=""):
        self.calendar = calendar
        self.start = start
        self.end = end
        self.empty = empty
        self.text = text
        self.pattern_inactive = color_pattern(calendar.style.bg_inactive)
        self.pattern_active = color_pattern(calendar.style.bg_active)

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
        self.height = 1.0 - self.top - self.bot
        self.width = 1.0 - self.right - self.left
        self.style = style
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

    def toggle(self):
        self.visible = not self.visible
        self.toggles += 1

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
            self.schedule = db.scheduledict[dn][self.item]

    def set_gw(self, gw):
        self.top_abs = self.top * gw.height
        self.bot_abs = self.bot * gw.height
        self.height_abs = self.height * gw.height
        self.left_abs = self.left * gw.width
        self.right_abs = self.right * gw.width
        self.width_abs = self.width * gw.width
        self.gw = gw
        self.adjust()

    def adjust(self):
        self.cells = []
        calstart = self.scrolled_to
        calend = calstart + self.rows_on_screen
        evl = sorted(list(self.schedule.timeframe(calstart, calend)))
        if evl == []:
            self.fill_empty()
        celll = [
            CalendarCell(
                self, ev.start, ev.end, False, ev.display_str())
            for ev in evl]
        # I now have CalendarCells to represent the events; but I also
        # need CalendarCells to represent the spaces between
        # them. Those will always be one tick long. I'm not sure this
        # is a sustainable assumption; if CalendarCols get to showing
        # a lot of stuff at once, there will be a whole bunch of
        # sprites in them. Is that a problem? I'll see, I suppose.
        i = calstart
        while celll != []:
            cell = celll.pop()
            while i < cell.start:
                self.cells.append(CalendarCell(self, i, i+1, True))
                i += 1
            i = cell.end
            self.cells.append(cell)
        # There are now cells in self.cells to fill me up. There are
        # also some that overrun my bounds. I'll have to take that
        # into account when drawing.

    def __eq__(self, other):
        return (
            isinstance(other, CalendarCol) and
            other.dimension == self.dimension and
            other.item == self.item)

    def get_state_tup(self):
        return (
            self,
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
    for name in names:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, CalendarCol.colns)
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["item"]] = CalendarCol(**rowdict)
    return r
