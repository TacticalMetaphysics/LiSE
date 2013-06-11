from util import SaveableMetaclass, stringlike, dictify_row
from pyglet.image import SolidColorImagePattern as color_pattern
from collections import OrderedDict

"""User's view on a given item's schedule.

Usually there should be only one calendar per board, but it can switch
between showing various schedules, or even show many in parallel.

"""


class CalendarCell:
    """A block of time in a calendar.

Uses information from the CalendarCol it's in and the Event it
represents to calculate its dimensions and coordinates.

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
        self.was_hovered = False
        self.old_width = None
        self.old_height = None
        self.old_active_image = None
        self.old_inactive_image = None
        self.sprite = None
        self.label = None
        self._visible = True
        self._interactive = True
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

    def __getattr__(self, attrn):
        if attrn == 'interactive':
            return self._interactive
        elif attrn == 'start':
            if self.event is not None:
                return self.event.start
            else:
                return None
        elif attrn == 'end':
            if self.event is not None:
                return self.event.start + self.event.length
            else:
                return None
        elif attrn == 'window_top':
            return (
                self.start +
                self.col.cal.scrolled_to) * self.col.cal.row_height
        elif attrn == 'window_bot':
            return self.window_top - (self.col.cal.row_height * len(self))
        elif attrn == 'window_left':
            return self.col.window_left + self.style.spacing
        elif attrn == 'window_right':
            return self.col.window_right - self.style.spacing
        elif attrn == 'width':
            return self.window_right - self.window_left
        elif attrn == 'height':
            return self.window_top - self.window_bot
        elif attrn == 'label_height':
            return self.style.fontsize + self.style.spacing
        elif attrn == 'visible':
            return (
                self._visible and
                self.col.visible)
        else:
            raise AttributeError(
                "CalendarCell instance has no such attribute: " +
                attrn)

    def get_state_tup(self):
        """Return a tuple containing information enough to tell the difference
between any two states that should appear different on-screen."""
        return (
            self.window_top,
            self.window_bot,
            self.text,
            self.visible,
            self.interactive,
            self.tweaks)

    def toggle_visibility(self):
        self.visible = not self.visible
        self.tweaks += 1

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def hide(self):
        if self.visible:
            self.toggle_visibility()


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
         {"dimension": "text not null DEFAULT 'Physical'",
          "item": "text not null",
          "visible": "boolean not null DEFAULT 1",
          "interactive": "boolean not null DEFAULT 1",
          "style": "text not null DEFAULT 'BigLight'",
          "cel_style": "text not null DEFAULT 'SmallDark'"},
         ("dimension", "item"),
         {"dimension, item": ("item", "dimension, name"),
          "style": ("style", "name"),
          "cel_style": ("style", "name")},
         []
         )]

    def __init__(self, db, dimension, item,
                 visible, interactive, style, cel_style):
        self.dimension = dimension
        self.item = item
        self._visible = visible
        self.tweaks = 0
        self._interactive = interactive
        self.style = style
        self.cel_style = cel_style
        self.oldstate = None
        self.old_width = None
        self.old_image = None
        self.sprite = None
        self.celldict = {}
        self.cell_cache = {}
        self.oldwidth = None
        if stringlike(self.dimension):
            dimname = self.dimension
        else:
            dimname = self.dimension.name
        if stringlike(self.item):
            itname = self.item
        else:
            itname = self.item.name
        if dimname not in db.calcoldict:
            db.calcoldict[dimname] = {}
        db.calcoldict[dimname][itname] = self
        self.db = db

    def __iter__(self):
        return self.celldict.itervalues()

    def __eq__(self, other):
        return (
            isinstance(other, CalendarCol) and
            other.board == self.board and
            other.item == self.item)

    def __getattr__(self, attrn):
        if attrn == 'visible':
            return self._visible and self.item.name in self.cal.coldict
        elif attrn == 'interactive':
            return self._interactive
        elif attrn == 'window_top':
            return self.cal.window_top
        elif attrn == 'window_bot':
            return self.cal.window_bot
        elif attrn == 'window_left':
            return self.cal.window_left + self.idx * self.cal.col_width
        elif attrn == 'window_right':
            return self.window_left + self.cal.col_width
        elif attrn == 'width':
            return self.cal.col_width
        elif attrn == 'height':
            return self.cal.height
        else:
            raise AttributeError(
                "CalendarCol instance has no such attribute: " +
                attrn)

    def get_tabdict(self):
        return {
            "calendar_col": {
                "board": self.board.dimension.name,
                "item": self.item.name,
                "visible": self.visible,
                "interactive": self.interactive,
                "style": self.style.name,
                "cel_style": self.cel_style.name}}

    def toggle_visibility(self):
        if self in self.cal:
            self.cal.remove(self)
            self.visible = False
        else:
            self.cal.add(self)
            self.visible = True
        self.cal.adjust()
        self.tweaks += 1

    def hide(self):
        if self.visible:
            self.toggle_visibility()

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def unravel(self):
        db = self.db
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        self.board = db.boarddict[self.dimension.name]
        if stringlike(self.item):
            self.item = db.itemdict[self.dimension.name][self.item]
        self.item.pawn.calcol = self
        if stringlike(self.style):
            self.style = db.styledict[self.style]
        self.style.unravel()
        self.inactive_pattern = color_pattern(self.style.bg_inactive.tup)
        if stringlike(self.cel_style):
            self.cel_style = db.styledict[self.cel_style]
        self.cel_style.unravel()
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

    def celhash(self):
        hashes = [
            hash(cel.get_state_tup())
            for cel in self.celldict.itervalues()]
        return hash(tuple(hashes))

    def get_state_tup(self):
        """Return a tuple containing information enough to tell the difference
between any two states that should appear different on-screen."""
        return (
            self.celhash(),
            self.dimension.name,
            self.item.name,
            self.window_left,
            self.window_right,
            self.window_top,
            self.window_bot,
            self.visible,
            self.interactive,
            self.tweaks)


class Calendar:
    """A collection of calendar columns representing at least one
schedule, possibly several.

"""
    scroll_factor = 1

    def __init__(
            self, board, left, right, top, bot, visible, interactive,
            rows_on_screen, scrolled_to):
        self.db = board.db
        self.board = board
        self.left_prop = left
        self.right_prop = right
        self.top_prop = top
        self.bot_prop = bot
        self._visible = visible
        self._interactive = interactive
        self.rows_on_screen = rows_on_screen
        self.scrolled_to = scrolled_to
        self.oldstate = None
        self.sprite = None
        self.tweaks = 0
        self.db.caldict[str(self.board)] = self


    def __iter__(self):
        return self.coldict.itervalues()

    def __len__(self):
        return len(self.coldict)

    def __getattr__(self, attrn):
        if attrn == 'gw':
            if not hasattr(self.board, 'gw'):
                return None
            else:
                return self.board.gw
        elif attrn == 'window_top':
            if self.gw is None:
                return 0
            else:
                return int(self.top_prop * self.gw.height)
        elif attrn == 'window_bot':
            if self.gw is None:
                return 0
            else:
                return int(self.bot_prop * self.gw.height)
        elif attrn == 'window_left':
            if self.gw is None:
                return 0
            else:
                return int(self.left_prop * self.gw.width)
        elif attrn == 'window_right':
            if self.gw is None:
                return 0
            else:
                return int(self.right_prop * self.gw.width)
        elif attrn == 'width':
            return self.window_right - self.window_left
        elif attrn == 'height':
            return self.window_top - self.window_bot
        elif attrn == 'visible':
            return self._visible and len(self.coldict) > 0
        elif attrn == 'interactive':
            return self._interactive
        else:
            raise AttributeError(
                "Calendar instance has no such attribute: " +
                attrn)

    def __getitem__(self, colname):
        """Return the CalendarCol by the given name."""
        return self.coldict[colname]

    def __contains__(self, col):
        return col.item.name in self.coldict

    def colhash(self):
        hashes = [
            hash(col.get_state_tup())
            for col in self.coldict.itervalues()]
        return hash(tuple(hashes))

    def get_state_tup(self):
        """Return a tuple containing information enough to tell the difference
between any two states that should appear different on-screen."""
        return (
            self.board.dimension.name,
            self.colhash(),
            self.window_left,
            self.window_right,
            self.window_top,
            self.window_bot,
            self.visible,
            self.interactive,
            self.rows_on_screen,
            self.scrolled_to,
            self.tweaks)

    def unravel(self):
        """Dereference contained strings into Python objects.

Results in self.board being a Board object, self.coldict being the
OrderedDict containing the columns herein, and every CalendarCol in
self.coldict being itself unraveled.

        """
        db = self.db
        if str(self.board) not in db.calcoldict:
            db.calcoldict[str(self.board)] = OrderedDict()
        self.coldict = db.calcoldict[str(self.board)]
        for column in self.coldict.itervalues():
            column.unravel()
        

    def adjust(self):
        """Create missing calendar cells. Delete those whose events are no
longer present.

        """
        if len(self.coldict) > 0:
            self.col_width = self.width / len(self.coldict)
        else:
            self.col_width = 0
        self.row_height = self.height / self.rows_on_screen
        i = 0
        for col in self.coldict.itervalues():
            col.cal = self
            col.idx = i
            i += 1
            for ev in iter(col.item.schedule):
                if ev.name not in col.celldict:
                    col.celldict[ev.name] = CalendarCell(col, ev)
            for evname in col.celldict:
                if evname not in col.item.schedule.events:
                    del col.celldict[evname]

    def gettop(self):
        """Get the absolute Y value of my top edge."""
        return self.top_abs

    def getbot(self):
        """Get the absolute Y value of my bottom edge."""
        return self.bot_abs

    def getleft(self):
        """Get the absolute X value of my left edge."""
        return self.left_abs

    def getright(self):
        """Get the absolute X value of my right edge."""
        return self.right_abs

    def getwidth(self):
        """Get the width of this widget."""
        return self.width_abs

    def getheight(self):
        """Get the height of this widget."""
        return self.height_abs

    def getstart(self):
        """Get the number of ticks between the start of the game and the time
displayed by this calendar."""
        return self.scrolled_to

    def getend(self):
        """Get the last tick of game-time that this calendar displays."""
        return self.scrolled_to + self.rows_on_screen

    def add(self, col):
        """Add a CalendarCol to be displayed.

This method does not affect the CalendarCol, such as by informing it
that it's in this calendar. You'll want to do that elsewhere, using
the CalendarCol's set_cal() method.

        """
        if col.item.name not in self.coldict:
            self.coldict[col.item.name] = col

    def remove(self, col):
        """Remove a CalendarCol.

This doesn't necessarily delete the CalendarCol's graphics."""
        del self.coldict[col.item.name]

    def discard(self, col):
        """Remove a CalendarCol if it's a member.

This doesn't necessarily delete the CalendarCol's graphics."""
        if col.item.name in self.coldict:
            del self.coldict[col.item.name]

    def index(self, col):
        """Get the index of the CalendarCol within the order of displayed
columns."""
        return self.coldict.keys().index(col.item.name)

    def pop(self, colname):
        """Return and remove the CalendarCol by the given name."""
        r = self.coldict.pop(colname)
        return r

    def toggle_visibility(self):
        """Hide or show myself, as applicable."""
        self.visible = not self.visible
        self.tweaks += 1

    def hide(self):
        """Become invisible."""
        if self.visible:
            self.toggle_visibility()

    def show(self):
        """Become visible."""
        if not self.visible:
            self.toggle_visibility()


rcib_format = (
    "SELECT {0} FROM calendar_col WHERE dimension IN ({1})".format(
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
        r[rowdict["dimension"]][rowdict["item"]] = CalendarCol(**rowdict)
    return r
