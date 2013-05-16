from event import get_all_starting_ongoing_ending as gasoe
# do I want to handle the timer here? that might be good

class GameState:
    """Class to hold the state of the game, specifically not including the
state of the interface.

    """
    def __init__(self, db):
        self.db = db
        self.age = db.get_age()
        self.since = 0
                
    def __iter__(self):
        return iter(self.dimensions)

    def update(self, ts, st):
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
