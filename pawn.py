from util import SaveableMetaclass, dictify_row


__metaclass__ = SaveableMetaclass


class Pawn:
    """A token to represent something that moves about between Places.

    Pawn(thing, place, x, y) => pawn

    thing is the game-logic item that the Pawn represents.
    It should be of class Thing.

    place is the name of a Place that is already represented by a Spot
    in the same Board. pawn will appear here to begin with. Note that
    the Spot need not be visible. You can supply the Place name for an
    invisible spot to make it appear that a Pawn is floating in that
    nebulous dimension between Places.

    """
    tablenames = ["pawn"]
    coldecls = {"pawn":
                {"dimension": "text",
                 "thing": "text",
                 "img": "text",
                 "visible": "boolean",
                 "interactive": "boolean"}}
    primarykeys = {"pawn": ("dimension", "thing")}
    fkeydict = {"pawn":
                {"img": ("img", "name"),
                 "dimension, thing": ("thing", "dimension, name")}}

    def __init__(self, dimension, thing, img, visible, interactive, db=None):
        self.dimension = dimension
        self.thing = thing
        self.img = img
        self.visible = visible
        self.interactive = interactive
        if db is not None:
            dimname = None
            thingname = None
            if isinstance(self.dimension, str):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if isinstance(self.thing, str):
                thingname = self.thing
            else:
                thingname = self.thing.name
            if dimname not in db.pawndict:
                db.pawndict[dimname] = {}
            db.pawndict[dimname][thingname] = self

    def __eq__(self, other):
        return (
            isinstance(other, Pawn) and
            self.dimension == other.dimension and
            self.thingname == other.thingname)

    def __hash__(self):
        return self.hsh

    def unravel(self, db):
        if isinstance(self.dimension, str):
            self.dimension = db.dimensiondict[self.dimension]
        if isinstance(self.thing, str):
            self.thing = db.thingdict[self.dimension.name][self.thing]
        if isinstance(self.img, str):
            self.img = db.imgdict[self.img]

    def getcoords(self):
        # Assume I've been provided a spotdict. Use it to get the
        # spot's x and y, as well as that of the spot for the next
        # step on my thing's journey. If my thing doesn't have a
        # journey, return the coords of the spot. If it does, return a
        # point between the start and end spots in proportion to the
        # journey's progress. If there is no end spot, behave as if
        # there's no journey.
        #
        # I can't assume that img is an actual image because the
        # loader instantiates things before assigning them data that's
        # not strings or numbers. Calculate self.rx to save some
        # division.
        if not hasattr(self, 'rx'):
            self.rx = self.img.width / 2
        if not hasattr(self, 'ry'):
            self.ry = self.img.height / 2
        if hasattr(self.thing, 'journey') and\
           self.thing.journey.stepsleft() > 0:
            j = self.thing.journey
            port = j.getstep(0)
            start = port.orig.spot
            end = port.dest.spot
            hdist = end.x - start.x
            vdist = end.y - start.y
            p = j.progress
            x = start.x + hdist * p
            y = start.y + vdist * p
            return (x, y)
        else:
            ls = self.thing.location.spot
            return (ls.x, ls.y)

    def getcenter(self):
        (x, y) = self.getcoords()
        return (x, y + self.ry)

    def getleft(self):
        return self.getcoords()[0] - self.rx

    def getright(self):
        return self.getcoords()[0] + self.rx

    def gettop(self):
        return self.getcoords()[1] + self.img.height

    def getbot(self):
        return self.getcoords()[1]

    def is_visible(self):
        return self.visible

    def is_interactive(self):
        return self.interactive

    def onclick(self, button, modifiers):
        pass


pawncolstr = ", ".join(Pawn.colnames["pawn"])

pawn_dimension_qryfmt = (
    "SELECT {0} FROM pawn WHERE dimension IN ({1})".format(pawncolstr, "{0}"))


def read_pawns_in_dimensions(db, names):
    qryfmt = pawn_dimension_qryfmt
    qrystr = qryfmt.format(["?"] * len(names))
    db.c.execute(qrystr, names)
    r = {}
    for name in names:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Pawn.colnames["pawn"])
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["thing"]] = Pawn(**rowdict)
    return r


def unravel_pawns(db, pawnd):
    for pawn in pawnd.itervalues():
        pawn.unravel(db)
    return pawnd


def unravel_pawns_in_dimensions(db, pawnd):
    for pawns in pawnd.itervalues():
        unravel_pawns(db, pawns)
    return pawnd


def load_pawns_in_dimensions(db, names):
    return unravel_pawns_in_dimensions(db, read_pawns_in_dimensions(db, names))
