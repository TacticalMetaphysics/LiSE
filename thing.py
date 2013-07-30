from util import (
    SaveableMetaclass,
    LocationException,
    BranchTicksIter)
from logging import getLogger


__metaclass__ = SaveableMetaclass


logger = getLogger(__name__)


class JourneyException(Exception):
    pass


class Thing:
    """The sort of item that has a particular location at any given time.

Every Thing has a Journey and a Schedule, but either may be empty.

Things can contain other Things and be contained by other Things. This
is independent of where they are "located," which is always a
Place. But any things that contain one another should share locations,
too.

    """
    tables = [
        ("thing_location",
         {"dimension": "text not null default 'Physical'",
          "thing": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "location": "text not null"},
         ("dimension", "thing", "branch", "tick_from"),
         {"dimension, thing": ("thing", "dimension, name"),
          "dimension, location": ("place", "dimension, name")},
         [])]
    basic_speed = 0.1

    def __init__(self, dimension, name):
        self.name = name
        self.dimension = dimension
        self.db = self.dimension.db
        self.locations = {}
        self.indefinite_locations = {}

    def __getattr__(self, attrn):
        if attrn == 'location':
            return self.get_location()
        elif attrn == 'speed':
            return self.get_speed()
        elif attrn == 'distance':
            return self.get_distance()
        elif attrn == 'progress':
            return self.get_progress()
        else:
            raise AttributeError(
                "Thing instance {0} has no attribute {1}".format(
                str(self), attrn))

    def __setattr__(self, attrn, val):
        if attrn == 'location':
            self.set_location(val)
        else:
            super(Thing, self).__setattr__(attrn, val)

    def __str__(self):
        return self.name

    def __int__(self):
        return self.dimension.things.index(self)

    def assert_can_enter(self, it):
        """If I can't enter the given location, raise a LocationException.

Assume that the given location has no objections."""
        pass

    def assert_can_leave_location(self):
        """If I can't leave the location I'm currently in, raise a
LocationException."""
        pass

    def assert_can_contain(self, it):
        """If I can't contain the given item, raise a ContainmentException."""
        pass

    def get_location(self, branch=None, tick=None):
        """Return my current location by default, or where I was at the given
tick in the given branch."""
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.locations:
            return None
        for (tick_from, (loc, tick_to)) in self.locations[branch].iteritems():
            if tick_from <= tick and (tick_to is None or tick <= tick_to):
                return loc
        return None

    def set_location(self, loc, branch=None, tick_from=None, tick_to=None):
        """Declare that I'm in the given Place, Portal, or Thing.

With no tick_to argument, I'll stay in this location
indefinitely--that is, until I have anything else to do. With tick_to,
I'll stay in this location until then, even if I DO have something
else to do.

        """
        if branch is None:
            branch = self.db.branch
        if tick_from is None:
            tick_from = self.db.tick
        if branch not in self.locations:
            self.locations[branch] = {}
        self.locations[branch][tick_from] = (loc, tick_to)
        # A previous set_location might have set a previous tick_to to
        # None. In that case, this call to set_location will set the
        # end of that previous location.
        if branch in self.indefinite_locations:
            indef_tick_from = self.indefinite_locations[branch]
            indef_loc = self.locations[branch][indef_tick_from][0]
            self.locations[branch][indef_tick_from] = (
                indef_loc, tick_from - 1)
            del self.indefinite_locations[branch]
        if tick_to is None:
            self.indefinite_locations[branch] = tick_from

    def add_path(self, path, branch=None, tick=None):
        # the path is in reversed order.
        # pop stuff off it to find where to go.
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        prevstep = path.pop()
        prevtick = tick
        step = None
        while path != []:
            step = path.pop()
            port = self.dimension.portals_by_orign_destn[str(prevstep)][str(step)]
            tick_out = self.get_ticks_thru(port) + prevtick + 1
            self.set_location(port, branch, prevtick, tick_out)
            prevstep = step
            prevtick = tick_out
        if step is not None:
            self.set_location(step, branch, prevtick)

    def add_journey(self, journey, branch=None, tick=None):
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        prevtick = tick
        journey_end = journey[-1].dest
        for port in journey:
            tick_out = self.get_ticks_thru(port) + prevtick
            self.set_location(port, branch, prevtick, tick_out)
            prevtick = tick_out + 1
        self.set_location(journey_end, branch, prevtick)

    def get_speed(self, branch=None, tick=None):
        lo = self.get_location(branch, tick)
        ticks = self.get_ticks_thru(lo)
        return float(len(lo)) / float(ticks)

    def get_ticks_thru(self, po):
        """How many ticks would it take to get through that portal?"""
        # basic_speed should really be looked up in a character, this
        # is really a placeholder
        return len(po) / self.basic_speed

    def get_distance(self, branch=None, tick=None):
        """Return a float representing the number of spans across the portal
I've gone.

Presupposes that I'm in a portal.

        """
        return NotImplemented

    def get_progress(self, branch=None, tick=None):
        """Return a float representing the proportion of the portal I have
passed through.

Presupposes that I'm in a portal.

        """
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.locations:
            raise LocationException("I am nowhere in that branch")
        for (tick_from, (loc, tick_to)) in self.locations[branch].iteritems():
            if tick_to is None:
                continue
            if tick_from <= tick and tick <= tick_to:
                assert(hasattr(loc, 'orig') and hasattr(loc, 'dest'))
                return float(tick - tick_from) / float(tick_to - tick_from)
        raise LocationException("I am nowhere at that time")

    def free_time(self, n, branch=None, tick=None):
        """Return the first tick after the one given, and after which there
are n ticks of free time."""
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.locations:
            # Well, not existing is certainly ONE way not to have commitments
            return tick
        laterthan = tick
        for (tick_from, (loc, tick_to)) in self.locations[branch].iteritems():
            # This is only a *travel* event if it puts me in a portal
            if not (hasattr(loc, 'orig') and hasattr(loc, 'dest')):
                continue
            if (tick_from - n <= laterthan and laterthan <= tick_to):
                laterthan = tick_to
        return laterthan + 1

    def schedule_travel_thru(self, port, branch=None, tick=None):
        """Plan to travel through the given portal.

If I'm free, I'll go right away, or at the tick specified (and in the
branch specified) as applicable. Otherwise it'll wait til I'm good and
ready.

        """
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        # how long would it take?
        nticks = self.get_ticks_thru(port)
        # find a time
        starttime = self.free_time(nticks, branch, tick)
        self.set_location(port, branch, starttime, starttime + nticks)

    def schedule_journey(self, dest, branch=None, tick=None):
        """Plan a series of travels, through a series of portals, resulting in
my being located at the place given."""
        # TODO: Notify each Place that I go through
        #
        # if I'm already in a portal, wait til I'm out of it before
        # going on this new journey
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.locations:
            raise LocationException(
                "I don't exist in the given branch, so I can't go anywhere.")
        for (tick_from, (loc, tick_to)) in self.locations[branch].iteritems():
            if tick_from <= tick and (tick_to is None or tick <= tick_to):
                orig = loc
                if hasattr(orig, 'dest'):
                    starttick = tick_to
                else:
                    starttick = tick
                    self.locations[branch][tick_from] = (loc, tick)
                    if tick_to is None:
                        del self.indefinite_locations[branch]
                p = self.dimension.get_shortest_path(orig, dest, branch, tick)
                lasti = orig.i
                lasttick = starttick + 1
                while p != []:
                    nexti = p.pop()
                    if nexti == orig.i or nexti == dest.i:
                        continue
                    port = self.dimension.graph[lasti, nexti]["portal"]
                    ticks = self.get_ticks_thru(port)
                    self.set_location(port, branch, lasttick, lasttick + ticks)
                    lasttick += ticks + 1
                    lasti = nexti
                self.set_location(dest, branch, lasttick, None)
        raise JourneyException("Couldn't schedule the journey")

    def get_tabdict(self):
        return {
            "thing_location": [
                {
                    "dimension": str(self.dimension),
                    "thing": str(self),
                    "branch": branch,
                    "tick_from": tick_from,
                    "tick_to": tick_to,
                    "location": str(location)}
                for (branch, tick_from, tick_to, location) in
                BranchTicksIter(self.locations)]}
