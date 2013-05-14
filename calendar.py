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
        return self.height


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

    def set_gw(self, gw):
        self.top_abs = int(self.top * gw.height)
        self.bot_abs = int(self.bot * gw.height)
        self.height_abs = int(self.height * gw.height)
        self.left_abs = int(self.left * gw.width)
        self.right_abs = int(self.right * gw.width)
        self.width_abs = int(self.width * gw.width)
        self.gw = gw
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
        self.cells = []
        calstart = self.scrolled_to
        calend = calstart + self.rows_on_screen
        rowheight = self.getheight() / self.rows_on_screen
        evl = sorted(list(self.schedule.timeframe(calstart, calend)))
        top = self.gettop()
        self.celleft = self.getleft() + self.style.spacing
        self.celright = self.getright() - self.style.spacing
        self.celwidth = self.celright - self.celleft
        if evl == []:
            for i in xrange(self.scrolled_to, self.rows_on_screen - 1):
                c = CalendarCell(self, i, i+1, True)
                c.top = top
                top -= rowheight
                c.bot = top
            return
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
                c = CalendarCell(self, i, i+1, True)
                c.top = top
                top -= rowheight
                c.bot = top
                self.cells.append(c)
                i += 1
            cell.top = top
            top -= len(cell) * rowheight
            cell.bot = top
            i += len(cell)
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
    for name in names:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, CalendarCol.colns)
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["item"]] = CalendarCol(**rowdict)
    return r
