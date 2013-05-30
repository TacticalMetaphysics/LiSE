from util import SaveableMetaclass, dictify_row, stringlike
import pyglet


"""Simple data structures to hold style information for text and
things that contain text."""


__metaclass__ = SaveableMetaclass


class Color:
    """Red, green, blue, and alpha values.

    This is just a container class for the (red, green, blue, alpha)
tuples that Pyglet uses to identify colors. The tup attribute will get
you that.

    """
    tables = [
        ("color",
         {'name': 'text not null',
          'red': 'integer not null ',
          'green': 'integer not null ',
          'blue': 'integer not null ',
          'alpha': 'integer not null default 255 '},
         ("name",),
         {},
         ["red between 0 and 255",
          "green between 0 and 255",
          "blue between 0 and 255",
          "alpha between 0 and 255"])]

    def __init__(self, db, name, red, green, blue, alpha):
        """Return a color with the given name, and the given values for red,
green, blue, and alpha. Register in db.colordict.

        """
        self.name = name
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha
        self.tup = (self.red, self.green, self.blue, self.alpha)
        self.pattern = pyglet.image.SolidColorImagePattern(self.tup)
        if db is not None:
            db.colordict[self.name] = self

    def __str__(self):
        return self.name

    def __eq__(self, other):
        """Just check if they're both colors and their names are the same."""
        return (
            isinstance(other, Color) and
            self.name == other.name)

    def __hash__(self):
        """Hash of my name."""
        return hash(self.name)

    def __iter__(self):
        """Iterator over my tuple."""
        return iter(self.tup)

    def __repr__(self):
        """Looks just like the tuple."""
        return "(" + ", ".join(self.tup) + ")"


class Style:
    """A collection of cogent information for rendering text and things
that contain text."""
    tables = [
        ("style",
         {"name": "text not null",
          "fontface": "text not null",
          "fontsize": "integer not null",
          "spacing": "integer default 6",
          "bg_inactive": "text not null",
          "bg_active": "text not null",
          "fg_inactive": "text not null",
          "fg_active": "text not null"},
         ("name",),
         {"bg_inactive": ("color", "name"),
          "bg_active": ("color", "name"),
          "fg_inactive": ("color", "name"),
          "fg_active": ("color", "name")},
         [])]
    color_cols = ["bg_inactive", "bg_active", "fg_inactive", "fg_active"]

    def __init__(self, name, fontface, fontsize, spacing,
                 bg_inactive, bg_active, fg_inactive, fg_active,
                 db=None):
        """Return a style by the given name, with the given face, font size,
spacing, and four colors: active and inactive variants for each of the
foreground and the background.

With db, register in its styledict.

        """
        self.name = name
        self.fontface = fontface
        self.fontsize = fontsize
        self.spacing = spacing
        self.bg_inactive = bg_inactive
        self.bg_active = bg_active
        self.fg_inactive = fg_inactive
        self.fg_active = fg_active
        if db is not None:
            db.styledict[self.name] = self

    def __str__(self):
        return self.name

    def unravel(self, db):
        """Dereference all the colors"""
        for colorcol in self.color_cols:
            colorname = getattr(self, colorcol)
            if stringlike(colorname):
                color = db.colordict[colorname]
                setattr(self, colorcol, color)

    def __eq__(self, other):
        """Check we're both Style instances and we have the same name"""
        return (
            isinstance(other, Style) and
            self.name == other.name)

    def __hash__(self):
        """Hash a tuple with all the colors, name, fontface, fontsize,
spacing"""
        return hash((self.name, self.fontface, self.fontsize, self.spacing,
                     self.bg_inactive, self.bg_active, self.fg_inactive,
                     self.fg_active))

read_colors_fmt = (
    "SELECT {0} FROM color WHERE name IN ({1})".format(Color.colnstr, "{0}"))


def read_colors(db, colornames):
    """Read and instantiate colors of the given names. Don't unravel just
yet. Returns dict keyed with color names."""
    qryfmt = read_colors_fmt
    qrystr = qryfmt.format(", ".join(["?"] * len(colornames)))
    db.c.execute(qrystr, colornames)
    r = {}
    for row in db.c:
        rowdict = dictify_row(row, Color.colns)
        rowdict["db"] = db
        r[rowdict["name"]] = Color(**rowdict)
    return r


read_styles_fmt = (
    "SELECT {0} FROM style WHERE name IN ({1})".format(Style.colnstr, "{0}"))


def read_styles(db, stylenames):
    """Read styles by the given names and their colors, but don't unravel
just yet. Return a dict keyed by style name."""
    qryfmt = read_styles_fmt
    qrystr = qryfmt.format(", ".join(["?"] * len(stylenames)))
    db.c.execute(qrystr, stylenames)
    r = {}
    colornames = set()
    for row in db.c:
        rowdict = dictify_row(row, Style.colns)
        for colorcol in Style.color_cols:
            colornames.add(rowdict[colorcol])
        rowdict["db"] = db
        r[rowdict["name"]] = Style(**rowdict)
    read_colors(db, list(colornames))
    return r
