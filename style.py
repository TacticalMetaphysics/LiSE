from util import SaveableMetaclass, dictify_row, stringlike
import pyglet


__metaclass__ = SaveableMetaclass


class Color:
    """Color(red=0, green=0, blue=0, alpha=255) => color

    This is just a container class for the (red, green, blue, alpha)
tuples that Pyglet uses to identify colors.

    """
    tables = [
        ("color",
         {'name': 'text',
          'red': 'integer not null ',
          'green': 'integer not null ',
          'blue': 'integer not null ',
          'alpha': 'integer default 255 '},
         ("name",),
         {},
         ["red between 0 and 255",
          "green between 0 and 255",
          "blue between 0 and 255",
          "alpha between 0 and 255"])]

    def __init__(self, name, red, green, blue, alpha, db=None):
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
        return (
            isinstance(other, Color) and
            self.name == other.name)

    def __hash__(self):
        return hash(self.name)

    def __iter__(self):
        return iter(self.tup)

    def __repr__(self):
        return "(" + ", ".join(self.tup) + ")"


class Style:
    tables = [
        ("style",
         {"name": "text",
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
        for colorcol in self.color_cols:
            colorname = getattr(self, colorcol)
            if stringlike(colorname):
                color = db.colordict[colorname]
                setattr(self, colorcol, color)

    def __eq__(self, other):
        return (
            isinstance(other, Style) and
            self.name == other.name)

    def __hash__(self):
        return hash((self.name, self.fontface, self.fontsize, self.spacing,
                     self.bg_inactive, self.bg_active, self.fg_inactive,
                     self.fg_active))

read_colors_fmt = (
    "SELECT {0} FROM color WHERE name IN ({1})".format(Color.colnstr, "{0}"))


def read_colors(db, colornames):
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
