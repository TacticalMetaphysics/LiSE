from util import (
    SaveableMetaclass,
    tickly_get)
from logging import getLogger


__metaclass__ = SaveableMetaclass


logger = getLogger(__name__)


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
         []),
        ("thing_speed",
         {"dimension": "text not null default 'Physical'",
          "thing": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null",
          "tick_to": "integer not null",
          "ticks_per_span": "integer not null"},
         ("dimension", "thing", "branch", "tick_from"),
         {"dimension, thing": ("thing", "dimension, name")},
         [])]
    basic_speed = 0


    def __init__(self, dimension, name):
        self.name = name
        self.dimension = dimension
        self.db = self.dimension.db
        self.speeds = {}
        self.locations = {}
        self.indefinite_locations = {}
        self.indefinite_speeds = {}

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
            raise AttributeError("Thing instance {0} has no attribute {1}".format(
                str(self), attrn))

    def __setattr__(self, attrn, val):
        if attrn == 'location':
            self.set_location(val)
        elif attrn == 'speed':
            self.set_speed(val)
        else:
            super(Thing, self).__setattr__(self, attrn, val)

    def __str__(self):
        return self.name

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
        return tickly_get(self.db, self.locations, branch, tick)

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
            self.locations[branch][indef_tick_from] = (indef_loc, tick_from - 1)
            del self.indefinite_locations[branch]
        if tick_to is None:
            self.indefinite_locations[branch] = tick_from

    def get_speed(self, branch=None, tick=None):
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.speeds:
            return 0.0
        for (tick_from, (speed, tick_to)) in self.speeds[branch].iteritems():
            if tick_from <= tick <= tick_to:
                return speed
        return 0.0

    def set_speed(self, ticks_per_span, branch=None, tick_from=None, tick_to=None):
        """Declare that, during the given timespan, I will move at the given speed.

This is binding--if circumstances change how fast I can move, I must
set my speed again with this method.

Speed is measured in ticks-per-span, where a tick is an arbitrary unit
of time and a span is an arbitrary unit of distance.

        """
        if branch is None:
            branch = self.db.branch
        if tick_from is None:
            tick = self.db.tick
        if branch not in self.speeds:
            self.speeds[branch] = {}
        self.speeds[tick_from] = (ticks_per_span, tick_to)
        # clean up after a previous set_speed
        if branch in self.indefinite_speeds:
            indef_tick_from = self.indefinite_speeds[branch]
            indef_loc = self.locations[branch][indef_tick_from][0]
            self.locations[branch][indef_tick_from] = (indef_loc, tick_from - 1)
            del self.indefinite_speeds[branch]
        if tick_to is None:
            self.indefinite_speeds[branch] = tick_from

    def get_ticks_thru(self, po):
        """How many ticks would it take to get through that portal?"""
        # basic_speed should really be looked up in a character, this
        # is really a placeholder
        return len(po) * self.basic_speed

    def get_distance(self, branch=None, tick=None):
        """Return a float representing the number of spans across the portal
I've gone.

Presupposes that I'm in a portal.

        """
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        if branch not in self.locations:
            return 0.0
        lasttick = max([
            tick_from for tick_from in self.locations[branch].iterkeys()
            if tick_from <= tick])
        if nexttick is None:
            return 0.0
        speed = self.get_speed(branch, tick)
        travel_ticks_past = float(tick - lasttick)
        return 1.0 / (speed / travel_ticks_past)

    def get_progress(self, branch=None, tick=None):
        """Return a float representing the proportion of the portal I have
passed through.

Presupposes that I'm in a portal.

        """
        return self.get_distance(branch, tick) / len(self.get_location(branch, tick))

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
        self.set_location(port, branch, tick, tick + nticks)
