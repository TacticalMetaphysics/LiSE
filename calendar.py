from util import SaveableMetaclass, stringlike, dictify_row
from pyglet.image import SolidColorImagePattern as color_pattern
from style import read_styles


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

    def __init__(self, calendar, event, style, text=""):
        self.calendar = calendar
        self.event = event
        self.text = text
        self.oldstate = None
        self.newstate = None
        self.visible = True
        self.interactive = True
        self.inactive_pattern = color_pattern(style.bg_inactive.tup)
        if event is None:
            self.active_pattern = self.inactive_pattern
        else:
            self.active_pattern = color_pattern(style.bg_active.tup)

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
          "style": "text",
          "cel_style": "text"},
         ("dimension", "item"),
         {"dimension, item": ("item", "dimension, name"),
          "style": ("style", "name"),
          "cel_style": ("style", "name")},
         ["rows_on_screen>0", "scrolled_to>=0"]
         )]

    def __init__(self, dimension, item, visible, interactive,
                 rows_on_screen, scrolled_to,
                 left, top, bot, right, style, cel_style,
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
        self.cel_style = cel_style
        self.oldstate = None
        self.cells = []
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
        if stringlike(self.cel_style):
            self.cel_style = db.styledict[self.cel_style]
        self.cel_style.unravel(db)
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
        (s, c, e) = self.schedule.events_between(calstart, calend)
        start_set = set(s.viewvalues())
        continue_set = set(c.viewvalues())
        end_set = set(e.viewvalues())
        top = self.gettop()
        self.celleft = self.getleft() + self.style.spacing
        self.celright = self.getright() - self.style.spacing
        self.celwidth = self.celright - self.celleft
        # Events that start or end in the visible timeframe, but do
        # not continue in it, aren't visible; don't collect those.
        # Otherwise collect all events into four piles. One for those
        # that start and end inside the visible timeframe. One for
        # those that end in it, but start earlier. One for those that
        # begin in it, but end later. And one for those that overrun
        # it in both directions.
        # 
        # If there's an event that overruns in both directions, it's
        # the only one that gets drawn, due to an invariant: one event
        # at a time for each item in the game world.
        overrun_both = continue_set.difference(start_set, end_set)
        assert(len(overrun_both) <= 1)
        if len(overrun_both) == 1:
            ev = overrun_both.pop()
            cel = CalendarCell(self, ev.start, ev.start + ev.length, False, ev.name)
            self.cells = [cel]
            return self.cells
        enclosed = set.intersection(start_set, continue_set, end_set)
        overrun_before = set.intersection(continue_set, end_set) - start_set
        assert(len(overrun_before)) <= 1
        overrun_after = set.intersection(start_set, continue_set) - end_set
        assert(len(overrun_after)) <= 1
        # The events that overrun the calendar should be drawn that way--just a little.
        if len(overrun_before) == 1:
            ob_event = overrun_before.pop()
            ob_cel = CalendarCell(self, ob_event, self.cel_style, ob_event.name)
            ob_cel.top = self.gettop() + self.style.spacing  # overrun
            cel_rows_on_screen = ob_event.start + ob_event.length - self.scrolled_to
            ob_cel.bot = self.gettop() - cel_rows_on_screen * rowheight
            ob_cel.height = ob_cel.top - ob_cel.bot
            last_cel = ob_cel
        else:
            last_cel = None
        el = sorted(list(enclosed))
        for event in el:
            cel = CalendarCell(self, event, self.cel_style, event.name)
            cel.top = self.gettop() - event.start * rowheight
            cel.bot = cel.top - event.length * rowheight
            cel.height = cel.top - cel.bot
            if last_cel is not None and last_cel.bot > cel.bot:
                last_end = last_cel.event.start + last_cel.event.length
                last_bot = last_cel.bot
                ticks_between = event.start - last_end
                while ticks_between > 0:
                    empty = CalendarCell(self, None, self.cel_style)
                    empty.top = last_bot
                    empty.bot = empty.top - rowheight
                    self.cells.append(empty)
                    last_bot = empty.bot
                    ticks_between -= 1
            self.cells.append(cel)
            last_cel = cel
        if len(overrun_after) == 1:
            oa = overrun_after.pop()
            last_start = last_cel.event.start
            last_end = last_start + last_cel.event.length
            ticks_between = (oa.start + oa.length) - last_end
            last_bot = last_cel.bot
            ticks_between = oa.start - last_end
            while ticks_between > 0:
                empty = CalendarCell(self, None, self.cel_style)
                empty.top = last_bot
                empty.bot = empty.top - rowheight
                self.cells.append(empty)
                last_bot = empty.bot
                ticks_between -= 1
            cel = CalendarCell(self, oa, self.cel_style, oa.name)
            self.cells.append(cel)

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
