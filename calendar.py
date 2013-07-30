from util import SaveableMetaclass, stringlike
from pyglet.image import SolidColorImagePattern as color_pattern

"""User's view on a given item's schedule.

Usually there should be only one calendar per board, but it can switch
between showing various schedules, or even show many in parallel.

"""


class CalendarCell:
    """A block of time in a calendar.

Uses information from the CalendarCol it's in and the Event it
represents to calculate its dimensions and coordinates.

    """
    visible = True

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
            return self.col.cal.interactive
        elif attrn == 'window':
            return self.col.cal.board.gw.window
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
                self.col.cal.window_top -
                (self.start - self.col.cal.scrolled_to) *
                self.col.cal.row_height)
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
        self._visibility = not self._visibility
        self.tweaks += 1

    def show(self):
        if not self._visible:
            self.toggle_visibility()

    def hide(self):
        if self._visible:
            self.toggle_visibility()


class CalendarCol:
    def __init__(self, calendar, visible, interactive, style):
        self.calendar = calendar
        self.board = self.calendar.board
        self.db = self.calendar.db
        self.dimension = self.calendar.dimension
        self.visible = visible
        self.interactive = interactive
        self.style = style
        self.oldstate = None
        self.old_width = None
        self.old_image = None
        self.sprite = None
        self.celldict = {}
        self.cell_cache = {}
        self.oldwidth = None

    def __iter__(self):
        return self.celldict.itervalues()

    def __getattr__(self, attrn):
        if attrn == 'dimension':
            return self.db.get_dimension(self._dimension)
        elif attrn == 'idx':
            return self.cal.index(self)
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

    def delete(self):
        del self.db.calcoldict[self._dimension][self._item]
        self.erase()

    def toggle_visibility(self):
        self._visible = not self._visible
        if not self.visible:  # no underscore!
            try:
                self.sprite.delete()
            except:
                pass
            self.sprite = None
            for cel in self.celldict.itervalues():
                try:
                    cel.sprite.delete()
                except:
                    pass
                try:
                    cel.label.delete()
                except:
                    pass
                cel.sprite = None
                cel.label = None
                cel.tweaks += 1
        self.tweaks += 1

    def hide(self):
        if self._visible:
            self.toggle_visibility()

    def show(self):
        if not self._visible:
            self.toggle_visibility()

    def unravel(self):
        db = self.db
        if stringlike(self.style):
            self.style = db.styledict[self.style]
        self.style.unravel()
        self.inactive_pattern = color_pattern(self.style.bg_inactive.tup)
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
            self._dimension,
            self._item,
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
    __metaclass__ = SaveableMetaclass
    tables = [
        (
            "calendar",
            {"window": "text not null default 'Main'",
             "i": "integer not null default 0",
             "left": "float not null default 0.8",
             "right": "float not null default 1.0",
             "top": "float not null default 1.0",
             "bot": "float not null default 0.0",
             "style": "text not null default 'default_style'",
             "interactive": "boolean not null default 1",
             "rows_shown": "integer not null default 240",
             "scrolled_to": "integer default null",
             "scroll_factor": "integer not null default 4"},
            ("window", "i"),
            {"window": ("window", "name"),
             "style": ("style", "name")},
            ["rows_shown>0", "left>=0.0", "right<=1.0",
             "top<=1.0", "bot>=0.0"])]
    visible = True

    def __init__(
            self, window, i, left, right, top, bot, style, interactive,
            rows_shown, scrolled_to, scroll_factor):
        self.window = window
        self.i = i
        self.board = self.window.board
        self.db = self.board.db
        self.left_prop = left
        self.right_prop = right
        self.top_prop = top
        self.bot_prop = bot
        self.interactive = interactive
        self.rows_shown = rows_shown
        self.style = style
        if scrolled_to is None:
            scrolled_to = self.db.tick
        self.scrolled_to = scrolled_to
        self.scroll_factor = scroll_factor
        self.oldstate = None
        self.sprite = None
        self.tweaks = 0
        self.cols = []
        self.timeline = None

    def __iter__(self):
        return iter(self.cols)

    def __len__(self):
        return len(self.cols)

    def __getattr__(self, attrn):
        if attrn == 'board':
            return self.db.boarddict[self._dimension]
        elif attrn == 'gw':
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
            return self._visible and len(self.cols) > 0
        elif attrn == 'interactive':
            return self._interactive
        else:
            raise AttributeError(
                "Calendar instance has no such attribute: " +
                attrn)

    def __getitem__(self, i):
        return self.cols[i]

    def __contains__(self, col):
        return col in self.cols

    def __int__(self):
        return self.i

    def colhash(self):
        hashes = [
            hash(col.get_state_tup())
            for col in self.cols]
        return hash(tuple(hashes))

    def get_state_tup(self):
        """Return a tuple containing information enough to tell the difference
between any two states that should appear different on-screen."""
        return (
            self.i,
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

    def get_tabdict(self):
        return {
            "calendar": [
                {
                    "window": str(self.window),
                    "i": self.i,
                    "left": self.left_prop,
                    "right": self.right_prop,
                    "top": self.top_prop,
                    "bot": self.bot_prop,
                    "style": str(self.style),
                    "interactive": self.interactive,
                    "rows_shown": self.rows_shown,
                    "scrolled_to": self.scrolled_to,
                    "scroll_factor": self.scroll_factor}]}
