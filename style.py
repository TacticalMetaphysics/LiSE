from util import SaveableMetaclass, dictify_row


__metaclass__ = SaveableMetaclass


class Color:
    """Color(red=0, green=0, blue=0, alpha=255) => color

    This is just a container class for the (red, green, blue, alpha)
tuples that Pyglet uses to identify colors.

    """
    tablenames = ["color"]
    coldecls = {"color":
                {'name': 'text',
                 'red': 'integer not null ',
                 'green': 'integer not null ',
                 'blue': 'integer not null ',
                 'alpha': 'integer default 255 '}}
    primarykeys = {"color": ("name",)}
    checks = {"color":
              ["red between 0 and 255",
              "green between 0 and 255",
              "blue between 0 and 255",
              "alpha between 0 and 255"]}

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

    def __eq__(self, other):
        return (
            isinstance(other, Color) and
            self.name == other.name)

    def __hash__(self):
        return hash(self.name)

    def __iter__(self):
        return iter(self.tup)

    def __str__(self):
        return "(" + ", ".join(self.tup) + ")"


class Style:
    tablenames = ["style"]
    coldecls = {"style":
                {"name": "text",
                 "fontface": "text not null",
                 "fontsize": "integer not null",
                 "spacing": "integer default 6",
                 "bg_inactive": "text not null",
                 "bg_active": "text not null",
                 "fg_inactive": "text not null",
                 "fg_active": "text not null"}}
    primarykeys = {"style": ("name",)}
    foreignkeys = {"style":
                   {"bg_inactive": ("color", "name"),
                    "bg_active": ("color", "name"),
                    "fg_inactive": ("color", "name"),
                    "fg_active": ("color", "name")}}

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

    def __eq__(self, other):
        return (
            isinstance(other, Style) and
            self.name == other.name)

    def __hash__(self):
        return self.hsh


def pull(self, db, keydicts):
    colornames = [keydict["name"] for keydict in keydicts]
    qryfmt = "SELECT {0} FROM color WHERE name IN ({1})"
    qms = ["?"] * len(colornames)
    qrystr = qryfmt.format(
        ", ".join(self.colnames["color"]),
        ", ".join(qms))
    db.c.execute(qrystr, colornames)
    return parse([
        dictify_row(self.colnames["color"], row)
        for row in db.c])


def parse(self, rows):
    r = {}
    for row in rows:
        r[row["name"]] = row
    return r
