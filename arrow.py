from util import stringlike
from math import hypot


class Arrow:
    margin = 20
    w = 10
    def __init__(self, gw, portal):
        self.gw = gw
        self._portal = str(portal)
        self.vertices = ((None,None),(None,None),(None,None))
        self.oldstate = None
        self.order = gw.edge_order
        gw.edge_order += 1
        self.selectable = True
        self.overlap_hints = {}
        self.y_at_hints = {}
        self.tweaks = 0
        dimname = self.gw.board._dimension
        self.db.arrowdict[dimname][self._portal] = self

    def __str__(self):
        return str(self.portal)

    def __len__(self):
        return hypot(self.run, self.rise)

    def __getattr__(self, attrn):
        if attrn == "dimension":
            return self.gw.board.dimension
        elif attrn == "_dimension":
            return self.gw.board._dimension
        elif attrn == "db":
            return self.gw.db
        elif attrn == "portal":
            return self.db.itemdict[
                self._dimension][self._portal]
        elif attrn == 'orig':
            return self.portal.orig.spot
        elif attrn == 'ox':
            return self.orig.x
        elif attrn == 'oy':
            return self.orig.y
        elif attrn == 'dest':
            return self.portal.dest.spot
        elif attrn == 'dx':
            return self.dest.x
        elif attrn == 'dy':
            return self.dest.y
        elif attrn == 'rise':
            return self.dest.y - self.orig.y
        elif attrn == 'run':
            return self.dest.x - self.orig.x
        elif attrn in ('m', 'slope'):
            ox = self.orig.x
            oy = self.orig.y
            dx = self.dest.x
            dy = self.dest.y
            if oy == dy:
                return 0
            elif ox == dx:
                return None
            else:
                return self.rise / self.run
        elif attrn == 'window_left':
            if self.orig.window_x < self.dest.window_x:
                return self.orig.window_x - self.margin
            else:
                return self.dest.window_x - self.margin
        elif attrn == 'window_right':
            if self.orig.window_x < self.dest.window_x:
                return self.dest.window_x + self.margin
            else:
                return self.orig.window_x + self.margin
        elif attrn == 'window_bot':
            if self.orig.window_y < self.dest.window_y:
                return self.orig.window_y - self.margin
            else:
                return self.dest.window_y - self.margin
        elif attrn == 'window_top':
            if self.orig.window_y < self.dest.window_y:
                return self.dest.window_y + self.margin
            else:
                return self.orig.window_y + self.margin
        elif attrn == 'b':
            # Returns a pair representing a fraction
            # y = mx + b
            # y - b = mx
            # -b = mx - y
            # b = -mx + y
            # b = y - mx
            if self.m is None:
                return None
            denominator = self.run
            x_numerator = self.rise * self.ox
            y_numerator = denominator * self.oy
            return ((y_numerator - x_numerator), denominator)
        elif attrn == 'highlit':
            return self in self.gw.selected
        else:
            raise AttributeError(
                "Edge instance has no attribute {0}".format(attrn))

    def y_at(self, x):
        if self.m is None:
            return None
        else:
            b = self.b
            mx = (self.rise * x, self.run)
            y = (mx[0] + b[0], self.run)
            return y

    def x_at(self, y):
        # y = mx + b
        # y - b = mx
        # (y - b)/m = x
        if self.m is None:
            return self.ox
        else:
            b = self.b
            numerator = y - b[1]
            denominator = b[0]
            return (numerator, denominator)

    def touching(self, x, y):
        """Do I overlap the point (x, y)?

'Width' is actually more like 'height'--it's a vertical margin of
error. This is good enough approximation for determining if I've been
clicked.

        """
        # trivially reject stuff outside my bounding box
        if (
                x < self.window_left or
                x > self.window_right or
                y < self.window_bot or
                y > self.window_top):
            return False
        if self.m > 300:
            perfect_x = self.x_at(y)
            frac_x = (x * perfect_x[1] - perfect_x[0], perfect_x[1])
            return abs(frac_x[0]) < abs(self.w * frac_x[1])
        perfect_y = self.y_at(x)
        if perfect_y is None:
            return True
        else:
            frac_y = (y * perfect_y[1] - perfect_y[0], perfect_y[1])
            return abs(frac_y[0]) < abs(self.w * frac_y[1])

    def get_state_tup(self):
        return ((self.tweaks, self.highlit) +
             self.orig.get_state_tup() +
             self.dest.get_state_tup())

    def reciprocate(self):
        # Return the edge of the portal that connects the same two
        # places in the opposite direction, supposing it exists
        try:
            port = self.portal.reciprocal
            return port.edge
        except KeyError:
            return None
        except AttributeError:
            port.edge = Edge(self.gw, port)

    def delete(self):
        for pair in self.vertices:
            for vertle in pair:
                try:
                    vertle.delete()
                except AttributeError:
                    pass
        self.portal.delete()
        del self.db.edgedict[self._dimension][self._portal]
