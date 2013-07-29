from util import (
    SaveableMetaclass,
    TerminableImg,
    TerminableInteractivity,
    TerminableCoords,
    dictify_row)


"""Widgets to represent places. Pawns move around on top of these."""


class Spot(object, TerminableImg, TerminableInteractivity, TerminableCoords):
    """The icon that represents a Place.

    The Spot is located on the Board that represents the same
    Dimension that the underlying Place is in. Its coordinates are
    relative to its Board, not necessarily the window the Board is in.

    """
    __metaclass__ = SaveableMetaclass
    tables = [
        ("spot_img",
         {"dimension": "text not null default 'Physical'",
          "place": "text not null",
          "board": "integer not null default 0",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "img": "text not null default 'default_spot'"},
         ("dimension", "place", "board", "branch", "tick_from"),
         {"dimension, board": ("board", "dimension, i"),
          "img": ("img", "name")},
         []),
        ("spot_interactive",
         {"dimension": "text not null default 'Physical'",
          "place": "text not null",
          "board": "integer not null default 0",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null"},
         ("dimension", "place", "board", "branch", "tick_from"),
         {"dimension, board": ("board", "dimension, i")},
         []),
        ("spot_coords",
         {"dimension": "text not null default 'Physical'",
          "place": "text not null",
          "board": "integer not null default 0",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "x": "integer not null default 50",
          "y": "integer not null default 50"},
         ("dimension", "place", "board", "branch", "tick_from"),
         {"dimension, board": ("board", "dimension, i")},
         [])]
    selectable = True

    def __init__(self, board, place):
        """Return a new spot on the board for the given dimension,
representing the given place with the given image. It will be at the
given coordinates, and visible or interactive as indicated.
        """
        self.board = board
        self.db = self.board.db
        self.window = self.board.window
        self.place = place
        self.interactivity = {}
        self.imagery = {}
        self.coord_dict = {}
        self.indefinite_imagery = {}
        self.indefinite_coords = {}
        self.indefinite_interactivity = {}
        self.grabpoint = None
        self.sprite = None
        self.box_edges = (None, None, None, None)
        self.oldstate = None
        self.newstate = None
        self.tweaks = 0

    def __getattr__(self, attrn):
        if attrn == 'dimension':
            return self.board.dimension
        elif attrn == 'interactive':
            return self.is_interactive()
        elif attrn == 'img':
            return self.get_img()
        elif attrn == 'hovered':
            return self.window.hovered is self
        elif attrn == 'pressed':
            return self.window.pressed is self
        elif attrn == 'grabbed':
            return self.window.grabbed is self
        elif attrn == 'coords':
            return self.get_coords()
        elif attrn == 'x':
            return self.coords[0]
        elif attrn == 'y':
            return self.coords[1]
        elif attrn == 'width':
            myimg = self.img
            if myimg is None:
                return 0
            else:
                return myimg.width
        elif attrn == 'height':
            myimg = self.img
            assert(hasattr(myimg, 'tex'))
            if myimg is None:
                return 0
            else:
                return myimg.height
        elif attrn == 'rx':
            return self.width / 2
        elif attrn == 'ry':
            return self.height / 2
        elif attrn == 'r':
            if self.rx > self.ry:
                return self.rx
            else:
                return self.ry
        elif attrn == 'left':
            return self.x - self.rx
        elif attrn == 'bot':
            return self.y - self.ry
        elif attrn == 'top':
            return self.y + self.ry
        elif attrn == 'right':
            return self.x + self.rx
        elif attrn == 'window_x':
            return self.x + self.window.offset_x
        elif attrn == 'window_y':
            return self.y + self.window.offset_y
        elif attrn == 'window_left':
            return self.left + self.window.offset_x
        elif attrn == 'window_bot':
            return self.bot + self.window.offset_y
        elif attrn == 'window_top':
            return self.top + self.window.offset_y
        elif attrn == 'window_right':
            return self.right + self.window.offset_x
        elif attrn == 'in_window':
            return (self.window_top > 0 and
                    self.window_right > 0) or (
                        self.window_bot < self.window.height and
                        self.window_right < self.window.width)
        elif attrn == 'visible':
            return self.img is not None
        else:
            raise AttributeError(
                "Spot instance has no such attribute: " +
                attrn)

    def __setattr__(self, attrn, val):
        if attrn == "img":
            self.set_img(val)
        elif attrn == "interactive":
            self.set_interactive(val)
        elif attrn == "x":
            self.set_coords(val, self.y)
        elif attrn == "y":
            self.set_coords(self.x, val)
        elif attrn == "hovered":
            if val is True:
                self.hovered()
            else:
                self.unhovered()
        elif attrn == "pressed":
            if val is True:
                self.set_pressed()
            else:
                self.unset_pressed()
        else:
            super(Spot, self).__setattr__(attrn, val)

    def __str__(self):
        return str(self.place)

    def __eq__(self, other):
        """Compare the dimension and the name"""
        return (
            isinstance(other, Spot) and
            self.dimension == other.dimension and
            self.name == other.name)

    def onclick(self):
        """Does nothing yet"""
        pass

    def hovered(self):
        """Become hovered"""
        if not self.hovered:
            self.hovered = True
            self.tweaks += 1

    def unhovered(self):
        """Stop being hovered"""
        if self.hovered:
            self.hovered = False
            self.tweaks += 1

    def set_pressed(self):
        """Become pressed"""
        pass

    def unset_pressed(self):
        """Stop being pressed"""
        pass

    def dropped(self, x, y, button, modifiers):
        """Stop being dragged by the mouse, forget the grabpoint"""
        self.grabpoint = None
        self.save()

    def move_with_mouse(self, x, y, dx, dy, buttons, modifiers):
        """Remember where exactly I was grabbed, then move around with the
mouse, always keeping the same relative position with respect to the
mouse."""
        if self.grabpoint is None:
            self.grabpoint = (x - self.x, y - self.y)
        (grabx, graby) = self.grabpoint
        self.x = x - grabx + dx
        self.left = self.x - self.rx
        self.right = self.x + self.rx
        self.y = y - graby + dy
        self.top = self.y + self.ry
        self.bot = self.y - self.ry

    def get_tabdict(self):
        dimn = str(self.dimension)
        placen = str(self.place)
        boardi = int(self.board)
        spot_img_rows = set()
        spot_img_cols = (
            "dimension",
            "place",
            "board",
            "branch",
            "tick_from",
            "tick_to",
            "img")
        for branch in self.imagery:
            for (tick_from, (img, tick_to)) in (
                    self.imagery[branch].iteritems()):
                spot_img_rows.add((
                    dimn,
                    placen,
                    boardi,
                    branch,
                    tick_from,
                    tick_to,
                    str(img)))
        spot_interactive_rows = set()
        spot_interactive_cols = (
            "dimension",
            "place",
            "board",
            "branch",
            "tick_from",
            "tick_to")
        for branch in self.interactivity:
            for (tick_from, tick_to) in self.interactivity[branch].iteritems():
                spot_interactive_rows.add((
                    dimn,
                    placen,
                    boardi,
                    branch,
                    tick_from,
                    tick_to))
        spot_coords_rows = set()
        spot_coords_cols = (
            "dimension",
            "place",
            "board",
            "branch",
            "tick_from",
            "tick_to",
            "x",
            "y")
        for branch in self.coord_dict:
            for (tick_from, (x, y, tick_to)) in (
                    self.coord_dict[branch].iteritems()):
                spot_coords_rows.add((
                    dimn,
                    placen,
                    boardi,
                    branch,
                    tick_from,
                    tick_to,
                    x,
                    y))
        return {
            "spot_img": [
                dictify_row(row, spot_img_cols) for row in iter(spot_img_rows)],
            "spot_interactive": [
                dictify_row(row, spot_interactive_cols) for row in iter(spot_interactive_rows)],
            "spot_coords": [
                dictify_row(row, spot_coords_cols) for row in iter(spot_coords_rows)]}

    def get_state_tup(self):
        return (
            str(self.board.dimension),
            int(self.board),
            str(self.place),
            str(self.img),
            self.hovered,
            self.pressed,
            self.grabbed,
            self.window_x,
            self.window_y,
            self.in_window)
