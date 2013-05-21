from event import get_all_starting_ongoing_ending as gasoe
import logging
# do I want to handle the timer here? that might be good


"""Controller for the whole thing, more or less."""


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

    def update(self, ts, st):
        """Update an appropriate number of ticks given that ts time has
passed, and ticks are supposed to pass every st seconds. Both are
floats."""
        # assuming for now that time only goes forward, at a rate of
        # one tick every st seconds
        log = logging.getLogger("state.update")
        extra = {
            "ts": ts,
            "st": st}
        self.since += ts
        newage = self.age
        while self.since > st:
            self.since -= st
            newage += 1
        extra["old_age"] = self.age
        extra["new_age"] = newage
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
        if log.isEnabledFor(logging.DEBUG):
            startstrs = [str(ev) for ev in starts.itervalues()]
            contstrs = [str(ev) for ev in conts.itervalues()]
            endstrs = [str(ev) for ev in ends.itervalues()]
            extra["starts"] = ", ".join(startstrs)
            extra["conts"] = ", ".join(contstrs)
            extra["ends"] = ", ".join(endstrs)
            log.debug("Updating game state.", extra=extra)
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
