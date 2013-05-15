# do I want to handle the timer here? that might be good

class GameState:
    """Class to hold the state of the game, specifically not including the
state of the interface.

    """
    def __init__(self, dimensions):
        self.dimensions = set(dimensions)
        self.age = None
                
    def __iter__(self):
        return iter(self.dimensions)

    def update(self, ts, st):
        # assuming for now that time only goes forward, at a rate of
        # one tick every st seconds
        newage = self.age
        while ts > st:
            ts -= st
            newage += 1
        starts = {}
        conts = {}
        ends = {}
        for dimension in self.dimensions:
            for item in dimension.itemdict.itervalues():
                if hasattr(item, 'schedule'):
                    (s, c, e) = item.schedule.starts_continues_ends(self.age, newage)
                    starts.update(s)
                    conts.update(c)
                    ends.update(e)
        for i in xrange(self.age, newage):
            s = iter(starts[i])
            c = iter(conts[i])
            e = iter(ends[i])
            for starter in s:
                starter.commence()
            for continuer in c:
                continuer.proceed()
            for ender in e:
                ender.conclude()
            self.age = i

    def add(self, dimension):
        self.dimensions.add(dimension)

    def discard(self, dimension):
        self.dimensions.discard(dimension)

    def remove(self, dimension):
        self.dimensions.remove(dimension)
