import math


fortyfive = math.pi / 4


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Wedge:
    def __init__(self, x, y, r, theta, degrees=True):
        self.pt = Point(x, y)
        self.r = r
        if degrees:
            self.theta = math.radians(theta)
        else:
            self.theta = theta

    def __getattr__(self, attrn):
        if attrn == "y":
            return self.pt.y
        elif attrn == "m":
            return math.tan(self.theta)
        elif attrn == "x":
            return self.pt.x
        elif attrn == "b":
            # y = mx + b
            # b = mx - y
            return self.m * self.x - self.y
        elif attrn == "left_tail_end":
            return self.get_left_tail_end()
        elif attrn == "right_tail_end":
            return self.get_right_tail_end()
        elif attrn == "points":
            return (self.left_tail_end, self.pt, self.right_tail_end)
        elif attrn == "edge":
            return (
                self.left_tail_end.x,
                self.left_tail_end.y,
                self.x,
                self.y,
                self.right_tail_end.x,
                self.right_tail_end.y)
        else:
            raise AttributeError(
                "Wedge instance has no attribute named {0}".format(attrn))

    def get_left_tail_end(self):
        # Being the point which, if I draw a line through it and my
        # own origin, I get an angle of intersection of 45 degrees, or
        # pi/2.
        #
        # First get the theta of some line that's forty five degrees
        # clockwise of me
        clockweiss = self.theta - fortyfive
        # Now put it in the opposite direction
        weissclock = math.pi - clockweiss
        # Pretend that the tail is always drawn from the origin. Add
        # self.x and self.y as offset at the end.
        ytmp = math.sin(weissclock) * self.r
        xtmp = math.cos(weissclock) * self.r
        return Point(xtmp + self.x, ytmp + self.y)

    def get_right_tail_end(self):
        clockweiss = self.theta + fortyfive
        weissclock = math.pi - clockweiss
        ytmp = math.sin(weissclock) * self.r
        xtmp = math.cos(weissclock) * self.r
        return Point(xtmp + self.x, ytmp + self.y)
