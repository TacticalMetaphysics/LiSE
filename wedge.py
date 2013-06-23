import math


fortyfive = math.pi / 4


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Wedge:
    def __init__(self, x, y, r):
        self.pt = Point(x, y)
        self.r = r

    def __getattr__(self, attrn):
        else:
            raise AttributeError(
                "Wedge instance has no attribute named {0}".format(attrn))
