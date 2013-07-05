import logging
# do I want to handle the timer here? that might be good
logger = logging.getLogger(__name__)


"""Looper over all the various update functions."""


class GameState:
    """Class to hold the state of the game, specifically not including the
state of the interface.

    """
    logfmt = """%(ts)s Updating game state from tick %(old_age)s to tick
%(new_age)s."""

    def __init__(self, db):
        """Return a GameState controlling everything in the given database."""
        self.db = db
        self.age = db.get_age()
        self.since = 0
        self.db.state = self

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
            for ev in starts:
                logger.debug("Starting event %s at tick %d", repr(ev), self.age)
                ev.commence()
            for ev in conts:
                ev.proceed()
            for ev in ends:
                logger.debug("Ending event %s at tick %d", repr(ev), self.age)
                ev.conclude()
        self.age = newage
