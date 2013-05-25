#from util import getLoggerIfLogging, DEBUG
# do I want to handle the timer here? that might be good
#log = getLoggerIfLogging(__name__)

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
        for i in xrange(self.age, newage):
            if i in self.db.startevdict:
                starts = iter(self.db.startevdict[i])
            else:
                starts = tuple()
            if i in self.db.contevdict:
                conts = iter(self.db.contevdict[i])
            else:
                conts = tuple()
            if i in self.db.endevdict:
                ends = iter(self.db.endevdict[i])
            else:
                ends = tuple()
            # if log.isEnabledFor(DEBUG):
            #     x = {
            #         "ts": ts,
            #         "st": st,
            #         "i": i,
            #         "old_age": self.age,
            #         "new_age": newage}
            for ev in starts:
                ev.commence()
            for ev in conts:
                ev.proceed()
            for ev in ends:
                ev.conclude()
        self.age = newage

