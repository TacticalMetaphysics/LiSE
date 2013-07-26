from util import (
    dictify_row,
    DictValues2DIterator,
    SaveableMetaclass)
from item import Item
from logging import getLogger


logger = getLogger(__name__)


class Portal(Item):
    __metaclass__ = SaveableMetaclass
    tables = [
        ("portal_existence",
         {"dimension": "text not null DEFAULT 'Physical'",
          "origin": "text not null",
          "destination": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null"},
         ("dimension", "from_place", "to_place", "branch", "tick_from"),
         # This schema relies on a trigger to create an appropriate
         # item record.
         [])]

    def __init__(self, dimension, orig, dest):
        self.dimension = dimension
        self.orig = orig
        self.dest = dest
        self.db = self.dimension.db
        self.existence = {}
        self.exist()
        

    def __str__(self):
        return "Portal({0}->{1})".format(str(self.orig), str(self.dest))

    def __int__(self):
        # assigned by self.dimension
        return self.i

    def __getattr__(self, attrn):
        else:
            raise AttributeError("Portal has no such attribute")

    def extant(self, branch=None, tick=None):
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.existence:
            return False
        for (tick_from, tick_to) in self.existence[branch].iteritems():
            if tick_from <= tick and (tick_to is None or tick <= tick_to):
                return True
        return False

    def exist(self, branch=None, tick_from=None, tick_to=None):
        if branch is None:
            branch = self.db.branch
        if tick_from is None:
            tick_from = self.db.tick
        if branch not in self.existence:
            self.existence[branch] = {}
        self.existence[branch][tick_from] = tick_to

    def admits(self, traveler):
        """Return True if I want to let the given thing enter me, False
otherwise."""
        return True

    def touches(self, place):
        return self.orig == place or self.dest == place

    def find_neighboring_portals(self):
        return self.orig.portals + self.dest.portals

    def notify_moving(self, thing, amount):
        """Handler for when a thing moves through me by some amount of my
length. Does nothing by default."""
        pass

    def get_tabdict(self):
        rows = []
        for branch in self.existence:
            for (tick_from, tick_to) in self.existence.branch:
                rows.append({
                    "dimension": str(self.dimension),
                    "origin": str(self.orig),
                    "destination": str(self.dest),
                    "branch": branch,
                    "tick_from": tick_from,
                    "tick_to": tick_to})
        return {
            "portal_existence": rows}
            
