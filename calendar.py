from util import SaveableMetaclass, stringlike, dictify_row
from pyglet.image import SolidColorImagePattern as color_pattern
from style import read_styles
from collections import OrderedDict


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

    def __init__(self, col, event):
        self.col = col
        self.event = event
        self.style = self.col.cel_style
        if self.event is None:
            self.text = ""
        else:
            self.text = self.event.text
        self.oldstate = None
        self.sprite = None
        self.tweaks = 0
        self.inactive_pattern = color_pattern(self.style.bg_inactive.tup)
        if event is None:
            self.active_pattern = self.inactive_pattern
        else:
            self.active_pattern = color_pattern(self.style.bg_active.tup)

    def __eq__(self, other):
        if not isinstance(other, CalendarCell):
            return False
        return (
            self.start == other.start and
            self.end == other.end and
            self.text == other.text)

    def __hash__(self):
        return hash((
            self.col.board.dimension,
            self.col.item,
            self.event))

    def __len__(self):
        return self.event.length

    def get_state_tup(self):
        return (
            hash(self.col.get_state_tup()),
            self.gettop(),
            self.getbot(),
            self.text,
            self.visible,
            self.interactive,
            self.tweaks)

    def getstart(self):
        return self.event.start

    def gettop(self):
        return (self.getstart() - self.col.cal.scrolled_to) * self.col.cal.rowheight()

    def getbot(self):
        return self.gettop() - (self.col.cal.rowheight() * len(self))

    def getleft(self):
        return self.col.getleft() + self.style.spacing

    def getright(self):
        return self.col.getright() - self.style.spacing

    def getwidth(self):
        return self.getright() - self.getleft()

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

<<<<<<< HEAD
    def is_visible(self):
        return self.visible and self.gettop() > 0

=======
>>>>>>> a6f74e7a1143235f13dfbad0c049ced680772436

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
         {"board": "text",
          "item": "text",
          "visible": "boolean",
          "interactive": "boolean",
          "style": "text DEFAULT 'BigLight'",
          "cel_style": "text DEFAULT 'SmallDark'"},
         ("board", "item"),
         {"board, item": ("item", "board, name"),
          "style": ("style", "name"),
          "cel_style": ("style", "name")},
         []
         )]

    def __init__(self, board, item, visible, interactive,
                 style, cel_style,
                 db=None):
        self.board = board
        self.item = item
        self.visible = visible
        self.tweaks = 0
        self.interactive = interactive
        self.style = style
        self.cel_style = cel_style
        self.oldstate = None
        self.sprite = None
        self.cells = {}
        self.left = 0
        self.right = 0
        self.cell_cache = {}
        if db is not None:
            if stringlike(self.board):
                boardname = self.board
            else:
                if stringlike(self.board.dimension):
                    boardname = self.board.dimension
                else:
                    boardname = self.board.dimension.name
            if stringlike(self.item):
                itname = self.item
            else:
                itname = self.item.name
            if boardname not in db.calcoldict:
                db.calcoldict[boardname] = {}
            db.calcoldict[boardname][itname] = self

    def __iter__(self):
        return self.cells.itervalues()

    def toggle_visibility(self):
        if self in self.cal:
            self.cal.remove(self)
        else:
            self.cal.add(self)
        self.tweaks += 1

    def hide(self):
        if self.visible:
            self.toggle_visibility()

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def is_visible(self):
        return self.visible and self.item.name in self.cal.coldict

    def unravel(self, db):
        if stringlike(self.board):
            self.board = db.boarddict[self.board]
        if stringlike(self.item):
            self.item = db.itemdict[self.board.dimension.name][self.item]
        self.item.pawn.calcol = self
        if stringlike(self.style):
            self.style = db.styledict[self.style]
        self.style.unravel(db)
        self.inactive_pattern = color_pattern(self.style.bg_inactive.tup)
        if stringlike(self.cel_style):
            self.cel_style = db.styledict[self.cel_style]
        self.cel_style.unravel(db)
        self.inactive_pattern = color_pattern(self.style.bg_inactive.tup)
        self.active_pattern = color_pattern(self.style.bg_active.tup)
        self.cal = self.board.calendar
        if not hasattr(self, 'schedule'):
            self.schedule = self.item.schedule
        else:
            assert(self.item.schedule == self.schedule)
        if self.visible:
            self.show()
        else:
            self.hide()

<<<<<<< HEAD
    def set_cal(self, cal):
        if cal is not self.cal:
            self.cal = cal
            self.adjust()
=======
    def set_gw(self, gw):
        self.top_abs = int(self.top * gw.height)
        self.bot_abs = int(self.bot * gw.height)
        self.height_abs = int(self.height * gw.height)
        self.left_abs = int(self.left * gw.width)
        self.right_abs = int(self.right * gw.width)
        self.width_abs = int(self.width * gw.width)
        self.gw = gw
        self.adjust(gw.db)
>>>>>>> a6f74e7a1143235f13dfbad0c049ced680772436

    def gettop(self):
        return self.cal.gettop()

    def getbot(self):
        return self.cal.getbot()

    def getleft(self):
        return self.cal.getleft() + self.cal.index(self) * self.cal.colwidth()

    def getright(self):
        return self.getleft() + self.cal.colwidth()

    def getwidth(self):
        return self.cal.colwidth()

    def getheight(self):
        return self.cal.getheight()

<<<<<<< HEAD
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

=======
    def adjust(self, db):
        self.cells = []
        calstart = self.scrolled_to
        calend = calstart + self.rows_on_screen
        rowheight = self.rowheight()
        (s, c, e) = self.schedule.events_between(calstart, calend)
        start_set = set()
        for val in s.itervalues():
            start_set.update(val)
        continue_set = set()
        for val in c.itervalues():
            continue_set.update(val)
        end_set = set()
        for val in e.itervalues():
            end_set.update(val)
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
            if ev.text[0] == "@":
                celtext = db.get_text(ev.text[1:])
            else:
                celtext = ev.text
            cel = CalendarCell(self, ev.start, ev.start + ev.length,
                               False, celtext)
            cel.top = self.gettop() + self.style.spacing
            cel.bot = self.getbot() - self.style.spacing
            self.cells = [cel]
            return self.cells
        enclosed = set.intersection(start_set, continue_set, end_set)
        overrun_before = set.intersection(continue_set, end_set) - start_set
        assert(len(overrun_before)) <= 1
        overrun_after = set.intersection(start_set, continue_set) - end_set
        assert(len(overrun_after)) <= 1
        # The events that overrun the calendar should be drawn that
        # way--just a little over the edge.
        last_cel = None
        if len(overrun_before) == 1:
            ob_event = overrun_before.pop()
            if ob_event.text[0] == "@":
                celtext = db.get_text(ob_event.text[1:])
            else:
                celtext = ob_event.text
            ob_cel = CalendarCell(self, ob_event, self.cel_style, celtext)
            ob_cel.top = self.gettop() + self.style.spacing  # overrun
            cel_rows_on_screen = (
                ob_event.start +
                ob_event.length -
                self.scrolled_to)
            ob_cel.bot = self.gettop() - cel_rows_on_screen * rowheight
            last_cel = ob_cel
        else:
            # This won't be drawn
            last_cel = CalendarCell(self, None, self.cel_style)
            last_cel.end = self.scrolled_to
            last_cel.top = self.gettop()
            last_cel.bot = self.gettop()
        el = sorted(list(enclosed))
        for event in el:
            if event.text[0] == "@":
                celtext = db.get_text(event.text[1:])
            else:
                celtext = event.text
            cel = CalendarCell(self, event, self.cel_style, celtext)
            cel.top = self.gettop() - event.start * rowheight
            cel.bot = cel.top - event.length * rowheight
            cel.height = cel.top - cel.bot
            if last_cel.bot > cel.bot:
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
            ticks_between = oa.start - last_cel.getend()
            last_bot = last_cel.bot
            while ticks_between > 0:
                empty = CalendarCell(self, None, self.cel_style)
                empty.top = last_bot
                empty.bot = empty.top - rowheight
                self.cells.append(empty)
                last_bot = empty.bot
                ticks_between -= 1
            if oa.text[0] == "@":
                celtext = db.get_text(oa.text[1:])
            else:
                celtext = oa.text
            cel = CalendarCell(self, oa, self.cel_style, celtext)
            cel.top = last_bot
            cel.bot = self.getbot() - self.style.spacing
            self.cells.append(cel)
>>>>>>> a6f74e7a1143235f13dfbad0c049ced680772436

    def __eq__(self, other):
        return (
            isinstance(other, CalendarCol) and
            other.board == self.board and
            other.item == self.item)

    def get_state_tup(self):
        return (
            hash(self.cal.get_state_tup()),
            self.getleft(),
            self.getright(),
            self.gettop(),
            self.getbot(),
            self.visible,
            self.interactive,
            self.tweaks)

class Calendar:
    """A collection of calendar columns representing at least one
schedule, possibly several.

This really can't be used without a database, but you can assign said
database without passing it to the constructor by use of the set_gw
method.

"""
    def __init__(
            self, board, left, right, top, bot, visible, interactive,
            rows_on_screen, scrolled_to, db=None):
        self.board = board
        self.left = left
        self.right = right
        self.top = top
        self.bot = bot
        self.visible = visible
        self.interactive = interactive
        self.rows_on_screen = rows_on_screen
        self.scrolled_to = scrolled_to
        self.tweaks = 0
        if db is not None:
            if stringlike(self.board):
                boardname = self.board
            else:
                if stringlike(self.board.dimension):
                    boardname = board.dimension
                else:
                    boardname = board.dimension.name
            db.caldict[boardname] = self

    def __iter__(self):
        return self.coldict.itervalues()

    def __len__(self):
        return len(self.coldict)

    def get_state_tup(self):
        return (
            len(self),
            self.getleft(),
            self.getright(),
            self.gettop(),
            self.getbot(),
            self.visible,
            self.interactive,
            self.rows_on_screen,
            self.scrolled_to,
            self.tweaks)
            

    def unravel(self, db):
        if stringlike(self.board):
            self.board = db.boarddict[self.board]
        if self.board.dimension.name in db.calcoldict:
            self.coldict = db.calcoldict[self.board.dimension.name]
        else:
            self.coldict = OrderedDict()
        for column in self.coldict.itervalues():
            column.unravel(db)

    def set_gw(self, gw):
        self.gw = gw
        self.gw.db.caldict[self.board.dimension.name] = self
        for col in self.coldict.itervalues():
            col.set_cal(self)

    def gettop(self):
        return int(self.top * self.gw.getheight())

    def getbot(self):
        return int(self.bot * self.gw.getheight())

    def getleft(self):
        return int(self.left * self.gw.getwidth())

    def getright(self):
        return int(self.right * self.gw.getwidth())

    def getwidth(self):
        return self.getright() - self.getleft()

    def getheight(self):
        return self.gettop() - self.getbot()

    def getstart(self):
        return self.scrolled_to

    def getend(self):
        return self.scrolled_to + self.rows_on_screen

    def add(self, col):
        if col.item.name not in self.coldict:
            self.coldict[col.item.name] = col
        self.tweaks += 1

    def remove(self, col):
        del self.coldict[col.item.name]
        self.tweaks += 1

    def discard(self, col):
        if col.item.name in self.coldict:
            del self.coldict[col.item.name]
        self.tweaks += 1

    def index(self, col):
        return sorted(self.coldict.keys()).index(col.item.name)

    def pop(self, colname):
        return self.coldict.pop(colname)

    def __getitem__(self, colname):
        return self.coldict[colname]

    def toggle_visibility(self):
        self.visible = not self.visible
        self.tweaks += 1

    def hide(self):
        if self.visible:
            self.toggle_visibility()

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def colwidth(self):
        return self.getwidth() / len(self.coldict)

    def rowheight(self):
        return self.getheight() / self.rows_on_screen

    def is_visible(self):
        return self.visible and len(self.coldict) > 0


rcib_format = (
    "SELECT {0} FROM calendar_col WHERE board IN ({1})".format(
        ", ".join(CalendarCol.colns), "{0}"))

def read_calendar_cols_in_boards(db, boardnames):
    qryfmt = rcib_format
    qrystr = qryfmt.format(", ".join(["?"] * len(boardnames)))
    db.c.execute(qrystr, boardnames)
    r = {}
    for boardname in boardnames:
        r[boardname] = {}
    for row in db.c:
        rowdict = dictify_row(row, CalendarCol.colns)
        rowdict["db"] = db
        r[rowdict["board"]][rowdict["item"]] = CalendarCol(**rowdict)
    return r
