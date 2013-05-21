from event import get_all_starting_ongoing_ending as gasoe
# do I want to handle the timer here? that might be good


"""Controller for the whole thing, more or less."""


class GameState:
    """Class to hold the state of the game, specifically not including the
state of the interface.

    """
    def __init__(self, db):
        """Return a GameState controlling everything in the given database."""
        self.db = db
        self.age = db.get_age()
        self.since = 0

    def __iter__(self):
        """Return an iterator over the dimensions in the game."""
        return iter(self.dimensions)

    def update(self, ts, st):
        """Update an appropriate number of ticks given that ts time has
passed, and ticks are supposed to pass every st seconds. Both are
floats."""
        # assuming for now that time only goes forward, at a rate of
        # one tick every st seconds
        self.since += ts
        newage = self.age
        while self.since > st:
            self.since -= st
            newage += 1
        if newage == self.age:
            return
        starts = {}
        conts = {}
        ends = {}
        for dimension in self.db.dimensiondict.itervalues():
            for item in dimension.itemdict.itervalues():
                if hasattr(item, 'schedule'):
                    (s, c, e) = gasoe(self.db, self.age, newage)
                    starts.update(s)
                    conts.update(c)
                    ends.update(e)
        for i in xrange(self.age, newage):
            if i in starts:
                s = iter(starts[i])
                for starter in s:
                    starter.commence()
            if i in conts:
                c = iter(conts[i])
                for continuer in c:
                    continuer.proceed()
            if i in ends:
                e = iter(ends[i])
                for ender in e:
                    ender.conclude()
            self.age = i

    def add(self, dimension):
        self.dimensions.add(dimension)

    def discard(self, dimension):
        self.dimensions.discard(dimension)

    def remove(self, dimension):
        self.dimensions.remove(dimension)
