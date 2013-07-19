"""Items that exist in the simulated world. Their graphical
representations are not considered here."""

from util import SaveableMetaclass
import logging


logger = logging.getLogger(__name__)


__metaclass__ = SaveableMetaclass


class Item:
    """Master class for all items that are in the game world. Doesn't do
much."""
    tables = [
        ("item",
         {"dimension": "text not null DEFAULT 'Physical'",
          "name": "text not null",
          "character": "text default null"},
         ("dimension", "name"),
         {},
         [])]

    def __init__(self, db, dimension, name):
        self.db = db
        self._dimension = str(dimension)
        self.name = name
        if self._dimension not in self.db.locdict:
            self.db.locdict[self._dimension] = {}
        if self._dimension not in self.db.itemdict:
            self.db.itemdict[self._dimension] = {}
        self.db.itemdict[self._dimension][str(self)] = self

    def __str__(self):
        return self.name

    def __contains__(self, that):
        return self.db.locdict[str(that.dimension)][str(that)] == self

    def __len__(self):
        i = 0
        for loc in self.db.locdict[self.dimension].itervalues():
            if loc == self:
                i += 1
        return i

    def __iter__(self):
        r = []
        for pair in self.db.locdict[str(self.dimension)].iteritems():
            if pair[1] == self:
                r.append(self.itemdict[pair[0]])
        return iter(r)

    def __getattr__(self, attrn):
        if attrn == 'contents':
            return [
                it for it in self.db.itemdict[str(self.dimension)].itervalues()
                if it.location == self]
        elif attrn == 'dimension':
            return self.db.get_dimension(self._dimension)
        else:
            raise AttributeError("Item has no attribute named " + attrn)

    def add(self, that):
        self.db.locdict[str(that.dimension)][that.name] = self

    def assert_can_contain(self, other):
        pass

    def get_tabdict(self):
        return {
            "item": {
                "dimension": self._dimension,
                "name": self.name}}

    def delete(self):
        del self.db.itemdict[self._dimension][self.name]
        self.erase()
