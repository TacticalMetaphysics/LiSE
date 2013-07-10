from util import stringlike
from math import hypot

order = 1

class Edge:
    def __init__(self, gw, portal):
        global order
        self.gw = gw
        self._portal = str(portal)
        self.vertices = ((None,None),(None,None),(None,None))
        self.oldstate = None
        self.order = order
        self.selectable = True
        self.overlap_hints = {}
        self.y_at_hints = {}
        order += 1
        self.tweaks = 0
        dimname = self.gw.board._dimension
        self.db.edgedict[dimname][self._portal] = self

    def __str__(self):
        return str(self.portal)

    def __len__(self):
        return hypot(self.run, self.rise)

    def __getattr__(self, attrn):
        if attrn == "dimension":
            return self.gw.board.dimension
        elif attrn == "db":
            return self.gw.db
        elif attrn == "portal":
            return self.db.itemdict[
                self.gw.board._dimension][self._portal]
        elif attrn == 'orig':
            return self.portal.orig.spot
        elif attrn == 'dest':
            return self.portal.dest.spot
        elif attrn == 'rise':
            return float(self.dest.y - self.orig.y)
        elif attrn == 'run':
            return float(self.dest.x - self.orig.x)
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
        elif attrn == 'w':
            return self.gw.arrow_girth
        elif attrn == 'window_left':
            if self.orig.x < self.dest.x:
                return self.orig.window_x
            else:
                return self.dest.window_x
        elif attrn == 'window_right':
            if self.orig.x < self.dest.x:
                return self.dest.window_x
            else:
                return self.orig.window_x
        elif attrn == 'window_bot':
            if self.orig.y < self.dest.y:
                return self.orig.window_y
            else:
                return self.dest.window_y
        elif attrn == 'window_top':
            if self.orig.y < self.dest.y:
                return self.dest.window_y
            else:
                return self.orig.window_y
        elif attrn == 'b':
            if self.m is None:
                return None
            # If I had a y intercept of 0, how high would I be at my
            # origin's x?
            b0 = self.m * self.orig.window_x
            # But I'm actually here, so have the difference
            return self.orig.window_y - b0
        elif attrn == 'highlit':
            return self in self.gw.selected
        else:
            raise AttributeError(
                "Edge instance has no attribute {0}".format(attrn))

    def y_at(self, x):
        if self.m is None:
            return None
        if x not in self.y_at_hints:
            self.y_at_hints[x] = self.m * x + self.b
        return self.y_at_hints[x]

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
        if x not in self.overlap_hints:
            self.overlap_hints[x] = {}
        if y not in self.overlap_hints[x]:
            perfect_y = self.y_at(x)
            if perfect_y is None:
                self.overlap_hints[x][y] = True
            else:
                self.overlap_hints[x][y] = abs(y - perfect_y) < self.w
        return self.overlap_hints[x][y]

    def get_state_tup(self):
        r = ((self.tweaks,) +
             self.orig.get_state_tup() +
             self.dest.get_state_tup())
        if r != self.oldstate:
            self.trash_cache()
        return r

    def trash_cache(self):
        if self.overlap_hints != {}:
            self.overlap_hints = {}
        if self.y_at_hints != {}:
            self.y_at_hints = {}
