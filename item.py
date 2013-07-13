"""Items that exist in the simulated world. Their graphical
representations are not considered here."""

from util import (
    SaveableMetaclass,
    dictify_row,
    stringlike,
    LocationException,
    ContainmentException,
    PortalException)
from event import (
    read_events,
    lookup_between,
    read_events,
    Event,
    SenselessEvent,
    ImpossibleEvent,
    IrrelevantEvent,
    ImpracticalEvent,
    PortalTravelEvent)
from edge import Edge
from effect import Effect, EffectDeck
import re
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
        self._dimension = dimension
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
            return [it for it in self.db.itemdict[str(self.dimension)].itervalues()
                    if it.location == self]
        elif attrn == 'dimension':
            return self.db.dimensiondict[self._dimension]
        else:
            raise AttributeError("Item has no attribute by that name")

    def add(self, that):
        if stringlike(that.dimension):
            dimn = that.dimension
        else:
            dimn = that.dimension.name
        self.db.locdict[dimn][that.name] = self

    def assert_can_contain(self, other):
        pass

    def delete(self):
        del self.db.itemdict[self._dimension][self.name]
        self.erase()


class Place(Item):
    """The 'top level' of the world model. Places contain Things and are
connected to other Places, forming a graph."""
    tables = [
        ("place",
         {"dimension": "text not null DEFAULT 'Physical'",
          "name": "text not null"},
         ("dimension", "name"),
         {},
         [])]

    def __init__(self, db, dimension, name):
        """Return a Place of the given name, in the given dimension. Register
it with the placedict and itemdict in the db."""
        Item.__init__(self, db, dimension, name)
        if self._dimension not in db.placedict:
            db.placedict[self._dimension] = {}
        if self._dimension not in db.contentsdict:
            db.contentsdict[self._dimension] = {}
        if self.name not in db.contentsdict[self._dimension]:
            db.contentsdict[self._dimension][self.name] = set()
        db.placedict[self._dimension][self.name] = self

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __getattr__(self, attrn):
        if attrn == 'spot':
            return self.db.spotdict[self._dimension][self.name]
        else:
            return Item.__getattr__(self, attrn)

    def unravel(self):
        pass

    def can_contain(self, other):
        """Does it make sense for that to be here?"""
        return True

    def delete(self):
        del self.db.placedict[self._dimension][self.name]
        Item.delete(self)


class Portal(Item):
    tables = [
        ("portal",
         {"dimension": "text not null DEFAULT 'Physical'",
          "from_place": "text not null",
          "to_place": "text not null"},
         ("dimension", "from_place", "to_place"),
         # This schema relies on a trigger to create an appropriate
         # item record.
         {"dimension, from_place": ("place", "dimension, name"),
          "dimension, to_place": ("place", "dimension, name")},
         [])]

    def __init__(self, db, dimension, from_place, to_place):
        self._orig = from_place
        self._dest = to_place
        name = "Portal({0}->{1})".format(
            str(from_place), str(to_place))
        Item.__init__(self, db, dimension, name)
        podd = db.portalorigdestdict
        pdod = db.portaldestorigdict
        for d in (db.itemdict, podd, pdod):
            if self._dimension not in d:
                d[self._dimension] = {}
        if self._orig not in podd[self._dimension]:
            podd[self._dimension][self._orig] = {}
        if self._dest not in pdod[self._dimension]:
            pdod[self._dimension][self._dest] = {}
        podd[self._dimension][self._orig][self._dest] = self
        pdod[self._dimension][self._dest][self._orig] = self

    def __str__(self):
        return self.name

    def __getattr__(self, attrn):
        if attrn == "spot":
            return self.dest.spot
        elif attrn == "orig":
            return self.db.placedict[self._dimension][self._orig]
        elif attrn == "dest":
            return self.db.placedict[self._dimension][self._dest]
        elif attrn == "edge":
            return self.db.edgedict[self._dimension][str(self)]
        elif attrn == "dimension":
            return self.db.dimensiondict[self._dimension]
        elif attrn == "reciprocal":
            return self.db.portaldestorigdict[
                self._dimension][self._orig][self._dest]
        else:
            raise AttributeError("Portal has no such attribute")

    def __repr__(self):
        return 'Portal({0}->{1})'.format(str(self.orig), str(self.dest))

    def unravel(self):
        pass

    def get_tabdict(self):
        return {
            "portal": {
                "dimension": str(self.dimension),
                "from_place": str(self.orig),
                "to_place": str(self.dest)}}

    def admits(self, traveler):
        """Return True if I want to let the given thing enter me, False
otherwise."""
        return True

    def touches(self, place):
        return self.orig is place or self.dest is place

    def find_neighboring_portals(self):
        return self.orig.portals + self.dest.portals

    def notify_moving(self, thing, amount):
        """Handler for when a thing moves through me by some amount of my
length. Does nothing by default."""
        pass

    def delete(self):
        del self.db.portalorigdestdict[self._dimension][self._orig][self._dest]
        del self.db.portaldestorigdict[self._dimension][self._dest][self._orig]
        del self.db.itemdict[self._dimension][self.name]
        self.erase()


class Thing(Item):
    """The sort of item that has a particular location at any given time.

Every Thing has a Journey and a Schedule, but either may be empty.

Things can contain other Things and be contained by other Things. This
is independent of where they are "located," which is always a
Place. But any things that contain one another should share locations,
too.

    """
    tables = [
        ("thing",
         {"dimension": "text not null DEFAULT 'Physical'",
          "name": "text not null",
          "location": "text not null",
          "journey_progress": "float not null DEFAULT 0.0",
          "journey_step": "integer not null DEFAULT 0",
          "age": "integer not null DEFAULT 0"},
         ("dimension", "name"),
         {"dimension, location": ("item", "dimension, name")},
         [])]

    def __init__(self, db, dimension, name, location,
                 journey_step=0, journey_progress=0.0, age=0,
                 schedule=None):
        """Return a Thing in the given dimension and location,
with the given name. Its contents will be empty to start; later on,
point some other Things' location attributes at this Thing to put
them in.

Register with the database's itemdict and thingdict too.

        """
        Item.__init__(self, db, dimension, name)
        self.start_location = location
        self.journey_step = journey_step
        self.journey_progress = journey_progress
        self.age = age
        if self._dimension not in db.itemdict:
            db.itemdict[self._dimension] = {}
        if self._dimension not in db.thingdict:
            db.thingdict[self._dimension] = {}
        if self._dimension not in db.locdict:
            db.locdict[self._dimension] = {}
        if self._dimension not in db.scheduledict:
            db.scheduledict[self._dimension] = {}
        db.thingdict[self._dimension][self.name] = self
        db.locdict[self._dimension][self.name] = location
        if schedule is None:
            if self.name not in self.db.scheduledict[self._dimension]:
                self.db.scheduledict[self._dimension][self.name] = Schedule(db, dimension, name)
        else:
            self.db.scheduledict[self._dimension][self.name] = schedule
            

    def __getattr__(self, attrn):
        if attrn == 'location':
            dimn = str(self.dimension)
            return self.db.locdict[dimn][self.name]
        elif attrn == 'schedule':
            return self.db.scheduledict[str(self.dimension)][self.name]
        else:
            return Item.__getattr__(self, attrn)

    def __str__(self):
        return self.name

    def __repr__(self):
        if self.location is None:
            loc = "nowhere"
        else:
            loc = str(self.location)
        return self.name + "@" + loc

    def unravel(self):
        """Dereference stringlike attributes.

Also add self to location, if applicable.

        """
        db = self.db
        locn = str(self.start_location)
        location = db.itemdict[self._dimension][locn]
        db.locdict[self.dimension.name][self.name] = location
        self.location.add(self)
        self.schedule.unravel()
        if (
                self.dimension.name in db.journeydict and
                self.name in db.journeydict[self.dimension.name]):
            self.journey = db.journeydict[self.dimension.name][self.name]
            self.journey.dimension = self.dimension
            self.journey.thing = self
            self.journey.schedule()

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

    def enter(self, it):
        """Check if I can go into the destination, and if so, do it
immediately. Else raise exception as appropriate."""
        self.assert_can_enter(it)
        it.assert_can_contain(self)
        it.add(self)

    def pass_through(self, there, elsewhere):
        """Try to enter there, and immediately go elsewhere. Raise
ShortstopException if it doesn't work."""

    def move_thru_portal(self, amount):
        """Move this amount through the portal I'm in"""
        if not isinstance(self.location, Portal):
            raise PortalException(
                """The location of {0} is {1},
which is not a portal.""".format(repr(self), repr(self.location)))
        self.location.notify_moving(self, amount)
        self.journey_progress += amount

    def speed_thru(self, port):
        return 1.0/60.0

    def delete(self):
        del self.db.thingdict[self._dimension][self.name]
        Item.delete(self)


thing_qvals = ["thing." + valn for valn in Thing.valns]


class Journey:
    """Series of steps taken by a Thing to get to a Place.

    Journey is the class for keeping track of a path that a traveller
    wants to take across one of the game maps. It is stateful: it
    tracks where the traveller is, and how far it's gotten along the
    edge through which it's travelling. Each step of the journey is a
    portal in the steps supplied on creation. The list should consist
    of Portals in the precise order that they are to be travelled
    through.

    Each Journey has a progress attribute. It is a float, at least 0.0
    and less than 1.0. When the traveller moves some distance along
    the current Portal, call move(prop), where prop is a float, of the
    same kind as progress, representing the proportion of the length
    of the Portal that the traveller has travelled. progress will be
    updated, and if it meets or exceeds 1.0, the current Portal will
    become the previous Portal, and the next Portal will become the
    current Portal. progress will then be decremented by 1.0.

    You probably shouldn't move the traveller through more than 1.0 of
    a Portal at a time, but Journey handles that case anyhow.

    """
    tables = [
        ("journey_step",
         {"dimension": "text not null default 'Physical'",
          "thing": "text not null",
          "idx": "integer not null",
          "from_place": "text not null",
          "to_place": "text not null"},
         ("dimension", "thing", "idx"),
         {"dimension, thing": ("thing", "dimension, name"),
          "dimension, from_place, to_place":
          ("portal", "dimension, from_place, to_place")},
         [])]

    def __init__(self, db, dimension, thing, steps):
        self._dimension = dimension
        self._thing = thing
        self.steps = []
        for st in steps:
            if isinstance(st, tuple):
                self.steps.append(st)
            else:
                origname = str(st.orig)
                destname = str(st.dest)
                self.steps.append((origname, destname))
        self.scheduled = {}
        if self._dimension not in db.journeydict:
            db.journeydict[self._dimension] = {}
        db.journeydict[self._dimension][self._thing] = self
        self.db = db

    def __getattr__(self, attrn):
        if attrn == 'dimension':
            return self.db.dimensiondict[self._dimension]
        elif attrn == 'thing':
            return self.db.thingdict[self._thing]
        else:
            raise AttributeError('Journey has no such attribute')

    def __getitem__(self, i):
        (orign, destn) = self.steps[i]
        try:
            return self.db.portalorigdestdict[self._dimension][orign][destn]
        except KeyError:
            return None

    def __setitem__(self, idx, port):
        """Put given portal into the step list at given index, padding steplist
with None as needed."""
        while idx >= len(self.steps):
            self.steps.append(None)
        if hasattr(port, 'orig') and hasattr(port, 'dest'):
            orign = str(port.orig)
            destn = str(port.dest)
        else:
            (orign, destn) = port
        self.steps[idx] = (orign, destn)

    def __len__(self):
        """Get the number of steps in the Journey.

        Returns the number of Portals the traveller ever passed
        through or ever will on this Journey.

        """
        return len(self.steps)


    def unravel(self):
        pass

    def steps_left(self):
        """Get the number of steps remaining until the end of the Journey.

        Returns the number of Portals left to be travelled through,
        including the one the traveller is in right now.

        """
        return len(self.steps) - self.thing.journey_step

    def speed_at_step(self, i):
        """Get the thing's speed at step i.

Speed is the proportion of the portal that the thing passes through
per unit of game time. It is expressed as a float, greater than zero,
no greater than one.

Speed should be expected to vary a lot depending on the properties and
current status of the thing and the portal. Thus it is delegated to a
method of the thing that operates on the portal.

"""
        return self.thing.speed_thru(self.getstep(i))

    def move_thing(self, prop):
        """If the thing is presently in a portal, move it across the given
proportion of the portal's length. If it is not, put it into the
current portal, and then move it along."""
        if isinstance(self.thing.location, Portal):
            return self.thing.move_thru_portal(prop)
        elif self.thing.journey_step >= len(self):
            raise ImpossibleEvent("Tried to move something past the natural end of its journey")
        else:
            port = self.portal_at(self.thing.journey_step)
            logger.debug(
                "Thing %s is about to leave place %s for portal %s.",
                self.thing,
                self.thing.location,
                str(port))
            self.thing.enter(port)
            self.thing.move_thru_portal(prop)
            return True

    def step(self):
        """Teleport the thing to the destination of the portal it's in, and
increment the journey_step.

Return a pair containing the place passed through and the portal it's
now in. If the place is the destination of the journey, the new portal
will be None.

        """
        oldport = self.thing.location
        newplace = self.thing.location.dest
        self.thing.journey_step += 1
        self.thing.journey_progress = 0.0
        self.thing.enter(newplace)
        logger.debug(
            "Thing %s has moved out of portal %s into place %s.",
            self.thing,
            oldport,
            newplace)
        return (oldport, newplace)

    def portal_at(self, i):
        """Return the portal at the given step, rather than the pair of place names."""
        return self[i]

    def schedule_step(self, i, start):
        """Add an event representing the step at the given index to the
thing's schedule, starting at the given tick."""
        port = self.portal_at(i)
        ev = PortalTravelEvent(self.db, self.thing, port, False)
        ev.start = start
        ev.length = int(1/self.thing.speed_thru(port))
        self.scheduled[i] = ev
        if self.thing.schedule is None:
            self.thing.schedule = Schedule(self.db, self.dimension, self.thing)
        self.thing.schedule.add(ev)
        return ev

    def schedule(self, delay=0):
        """Schedule all events in the journey, if they haven't been scheduled yet.

They'll always be scheduled after the present tick. Immediately after,
by default, but you can change that by supplying delay.

        """
        present = self.db.get_age()
        time_cursor = present + delay
        i = 0
        while i < len(self):
            if i not in self.scheduled:
                ev = self.schedule_step(i, time_cursor)
                time_cursor += ev.length + 1
            i += 1
        return self.thing.schedule

    def delete(self):
        del self.db.journeydict[self._dimension][self._thing]
        self.erase()


journey_qvals = ["journey_step." + valn for valn in Journey.valns]


class Schedule:
    """Many events, all assocated with the same item in the same dimension,
and given start times and lengths.

Events in a given schedule are assumed never to overlap. This is not
true of events in different schedules.

    """
    tables = [
        ("scheduled_event",
         {"dimension": "text not null default 'Physical'",
          "item": "text not null",
          "event": "text not null",
          "start": "integer not null",
          "length": "integer not null default 1"},
         ("dimension", "item"),
         {"dimension, item": ("item", "dimension, name"),
          "event": ("event", "name")},
         [])]

    def __init__(self, db, dimension, item):
        """Return an empty event for the given item in the given
dimension. With db, register in db's scheduledict, startevdict,
contevdict, and endevdict."""
        self._dimension = dimension
        self._item = item
        self.events = {}
        self.events_starting = dict()
        self.events_ending = dict()
        self.events_ongoing = dict()
        self.cached_commencements = {}
        self.cached_processions = {}
        self.cached_conclusions = {}
        if self._dimension not in db.scheduledict:
            db.scheduledict[self._dimension] = {}
        db.scheduledict[self._dimension][self._item] = self
        self.db = db

    def __getattr__(self, attrn):
        if attrn == 'dimension':
            return self.db.dimensiondict[self._dimension]
        elif attrn == 'item':
            return self.db.itemdict[self._dimension][self._item]
        else:
            raise AttributeError("Schedule has no such attribute")

    def get_tabdict(self):
        return {
            "scheduled_event": [
                {
                    "dimension": self.dimension.name,
                    "item": self.item.name,
                    "start": ev.start,
                    "event": ev.name,
                    "length": ev.length}
                for ev in self.events_starting.itervalues()]}

    def __iter__(self):
        """Return iterator over my events in order of their start times."""
        return self.events.itervalues()

    def __len__(self):
        return max(self.events_ongoing.viewkeys())
    
    def __contains__(self, ev):
        if not (
            hasattr(ev, 'start') and hasattr(ev, 'length')):
            return False
        ev_end = ev.start + ev.length
        if not (
            ev.start in self.events_starting and
            ev_end in self.events_ending):
            return False
        # Assume that self.add did its job right and I don't have to check all 
        # the inbetween periods.
        return (
            ev in self.events_starting[ev.start] and
            ev in self.events_ending[ev_end])

    def unravel(self):
        db = self.db
        """Dereference dimension and item."""
        for ev in self.events.itervalues():
            ev.unravel()

    def trash_cache(self, start):
        """Trash all cached results for commencements_between,
processions_between, and conclusions_between."""
        for cache in [
                self.cached_commencements,
                self.cached_processions,
                self.cached_conclusions]:
            try:
                del cache[start]
            except KeyError:
                pass

    def add(self, ev):
        """Add an event to all dictionaries in me. Assume it has a start and a
length already."""
        self.events[ev.name] = ev
        ev_end = ev.start + ev.length
        if ev.start not in self.events_starting:
            self.events_starting[ev.start] = set()
        if ev_end not in self.events_ending:
            self.events_ending[ev_end] = set()
        for i in xrange(ev.start+1, ev_end-1):
            if i not in self.events_ongoing:
                self.events_ongoing[i] = set()
            self.events_ongoing[i].add(ev)
        self.events_starting[ev.start].add(ev)
        self.events_ending[ev_end].add(ev)
        self.trash_cache(ev.start)
        if self.db is not None:
            self.db.add_event(ev)

    def remove(self, ev):
        """Remove an event from all my dictionaries."""
        del self.events[ev.name]
        ev_end = ev.start + ev.length
        self.events_starting[ev.start].remove(ev)
        for i in xrange(ev.start+1, ev_end-1):
            self.events_ongoing[i].remove(ev)
        self.events_ending[ev_end].remove(ev)

    def discard(self, ev):
        """Remove an event from all my dictionaries in which it is a
member."""
        del self.events[ev.name]
        if not hasattr(ev, 'start') or not hasattr(ev, 'length'):
            return
        ev_end = ev.start + ev.length
        self.events_starting[ev.start].discard(ev)
        self.events_ending[ev_end].discard(ev)
        for i in xrange(ev.start+1, ev_end-1):
            self.events_ongoing[i].discard(ev)
        self.discard_global(ev)
        self.trash_cache(ev.start)

    def commencements_between(self, start, end):
        """Return a dict of all events that start in the given timeframe,
keyed by their start times."""
        if (
                start in self.cached_commencements and
                end in self.cached_commencements[start]):
            return self.cached_commencements[start][end]
        lookup = lookup_between(self.events_starting, start, end)
        if start not in self.cached_commencements:
            self.cached_commencements[start] = {}
        self.cached_commencements[start][end] = lookup
        return lookup

    def processions_between(self, start, end):
        """Return a dict of all events that occur in the given timeframe,
regardless of whether they start or end in it. Keyed by every tick in
which the event is ongoing, meaning most events will be present more
than once."""
        if (
                start in self.cached_processions and
                end in self.cached_processions[start]):
            return self.cached_processions[start][end]
        lookup = lookup_between(self.events_ongoing, start, end)
        if start not in self.cached_processions:
            self.cached_processions[start] = {}
        self.cached_processions[start][end] = lookup
        return lookup

    def conclusions_between(self, start, end):
        """Return a dict of all events that end in the given time frame, keyed
by their end times."""
        if (
                start in self.cached_conclusions and
                end in self.cached_conclusions[start]):
            return self.cached_conclusions[start][end]
        lookup = lookup_between(self.events_ending, start, end)
        if start not in self.cached_conclusions:
            self.cached_conclusions[start] = {}
        self.cached_conclusions[start][end] = lookup
        return lookup

    def events_between(self, start, end):
        """Return a tuple containing the results of commencements_between,
processions_between, and conclusions_between, for the given
timeframe."""
        return (self.commencements_between(start, end),
                self.processions_between(start, end),
                self.conclusions_between(start, end))

    def delete(self):
        del self.db.scheduledict[self._dimension][self.name]
        self.erase()

SCHEDULE_DIMENSION_QRYFMT = """SELECT {0} FROM scheduled_event WHERE dimension 
IN ({1})""".format(", ".join(Schedule.colns), "{0}")

def read_schedules_in_dimensions(db, dimnames):
    qryfmt = SCHEDULE_DIMENSION_QRYFMT
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    events = set()
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Schedule.colns)
        dimn = rowdict["dimension"]
        itn = rowdict["item"]
        if itn not in r[dimn]:
            r[dimn][itn] = Schedule(dimn, itn, db)
        events.add(rowdict["event"])
    read_events(db, events)
    return r

schedule_qvals = (
    ["scheduled_event.item"] +
    ["scheduled_event." + valn for valn in Schedule.valns])

def lookup_loc(db, it):
    """Return the item that the given one is inside, possibly None."""
    if stringlike(it.dimension):
        dimname = it.dimension
    else:
        dimname = it.dimension.name
    if dimname not in db.locdict or it.name not in db.locdict[dimname]:
        return None
    return db.locdict[dimname][it.name]


def make_loc_getter(db, it):
    """Return a function with no args that will always return the present
location of the item, possibly None."""
    return lambda: lookup_loc(db, it)


thing_dimension_qryfmt = (
    "SELECT {0} FROM thing WHERE dimension IN "
    "({1})".format(
        ", ".join(Thing.colns), "{0}"))


def read_things_in_dimensions(db, dimnames):
    """Read and instantiate, but do not unravel, all things in the given
dimensions.

Return a 2D dictionary keyed by dimension name, then thing name.

    """
    qryfmt = thing_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Thing.colns)
        rowdict["db"] = db
        r[rowdict["dimension"]][rowdict["name"]] = Thing(**rowdict)
    return r


def load_things_in_dimensions(db, dimnames):
    """Load all things in the named dimensions. Return a 2D dictionary of
things keyed by dimension name, then thing name."""
    r = read_things_in_dimensions(db, dimnames)
    for dim in r.itervalues():
        for th in dim.itervalues():
            th.unravel()
    return r

SCHEDULE_DIMENSION_QRYFMT = """SELECT {0} FROM scheduled_event WHERE dimension 
IN ({1})""".format(", ".join(Schedule.colns), "{0}")

def read_schedules_in_dimensions(db, dimnames):
    qryfmt = SCHEDULE_DIMENSION_QRYFMT
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    events = set()
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Schedule.colns)
        dimn = rowdict["dimension"]
        itn = rowdict["item"]
        if itn not in r[dimn]:
            r[dimn][itn] = Schedule(dimn, itn, db)
        events.add(rowdict["event"])
    read_events(db, events)
    return r


def load_schedules_in_dimensions(db, dimnames):
    r = read_schedules_in_dimensions(db, dimnames)
    for dim in r.itervalues():
        for sched in dim.itervalues():
            sched.unravel()
    return r


journey_dimension_qryfmt = (
    "SELECT {0} FROM journey_step WHERE dimension IN "
    "({1})".format(
        ", ".join(Journey.colnames["journey_step"]), "{0}"))


def read_journeys_in_dimensions(db, dimnames):
    """Read and instantiate, but do not unravel, all journeys in the given
dimensions.

Return a 2D dict keyed by dimension name, then item name.

    """
    qryfmt = journey_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, tuple(dimnames))
    r = {}
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Journey.colnames["journey_step"])
        if rowdict["thing"] not in r[rowdict["dimension"]]:
            r[rowdict["dimension"]][rowdict["thing"]] = {
                "db": db,
                "dimension": rowdict["dimension"],
                "thing": rowdict["thing"],
                "steps": []}
        stepl = r[rowdict["dimension"]][rowdict["thing"]]["steps"]
        while len(stepl) <= rowdict["idx"]:
            stepl.append(None)
        f = rowdict["from_place"]
        t = rowdict["to_place"]
        stepl[rowdict["idx"]] = Portal(db, rowdict["dimension"], f, t)
    for item in r.iteritems():
        (dimname, journeys) = item
        for journey in journeys.iteritems():
            (thingname, jo) = journey
            r[dimname][thingname] = Journey(**jo)
    return r


def unravel_journeys(jod):
    """Unravel journeys in a dict keyed by their names. Return same
dict."""
    for jo in jod.itervalues():
        jo.unravel()
    return jod


def unravel_journeys_in_dimensions(jodd):
    """Unravel journeys previously read in by read_journeys or
read_journeys_in_dimensions."""
    for jod in jodd.itervalues():
        unravel_journeys(jod)
    return jodd


def load_journeys_in_dimensions(db, dimnames):
    """Load all journeys in the given dimensions.

Return them in a 2D dict keyed by dimension name, then thing name.

    """
    return unravel_journeys_in_dimensions(
        read_journeys_in_dimensions(db, dimnames))


place_dimension_qryfmt = (
    "SELECT {0} FROM place WHERE dimension IN "
    "({1})".format(
        ", ".join(Place.colns), "{0}"))


generic_place_re = re.compile("Place_([0-9])+")


def read_places_in_dimensions(db, dimnames):
    """Read and instantiate, but do not unravel, all places in the given
dimensions.

Return them in a 2D dict keyed by dimension name, then place name.

    """
    qryfmt = place_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for name in dimnames:
        r[name] = {}
    for row in db.c:
        rowdict = dictify_row(row, Place.colnames["place"])
        rowdict["db"] = db
        m = re.match(generic_place_re, rowdict["name"])
        if m is not None:
            num = int(m.groups()[0])
            if num > db.hi_place:
                db.hi_place = num
        r[rowdict["dimension"]][rowdict["name"]] = Place(**rowdict)
    return r


def unravel_places(pls):
    """Unravel places in a dict keyed by their names.

Return the same dict."""
    for pl in pls.itervalues():
        pl.unravel()
    return pls


def unravel_places_in_dimensions(pls):
    """Unravel places previously read in by read_places or
read_places_in_dimensions."""
    for pl in pls.itervalues():
        unravel_places(pl)
    return pls


def load_places_in_dimensions(db, dimnames):
    """Load all places in the given dimensions.

Return them in a 2D dict keyed by the dimension name, then the place
name.

    """
    return unravel_places_in_dimensions(
        load_places_in_dimensions(db, dimnames))


portal_colstr = ", ".join(Portal.colnames["portal"])
portal_dimension_qryfmt = (
    "SELECT {0} FROM portal WHERE dimension IN "
    "({1})".format(portal_colstr, "{0}"))


def read_portals_in_dimensions(db, dimnames):
    """Read and instantiate, but do not unravel, all portals in the given
dimensions.

Return them in a 2D dict keyed by dimension name, then portal name.

    """
    qryfmt = portal_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for dimname in dimnames:
        r[dimname] = {}
    for row in db.c:
        rowdict = dictify_row(row, Portal.colnames["portal"])
        rowdict["db"] = db
        orig = rowdict["from_place"]
        dest = rowdict["to_place"]
        dim = rowdict["dimension"]
        if orig not in r[dim]:
            r[dim][orig] = {}
        r[dim][orig][dest] = Portal(**rowdict)
    return r


def load_portals_in_dimensions(db, dimnames):
    r = read_portals_in_dimensions(db, dimnames)
    for origin in r.itervalues():
        for destination in origin.itervalues():
            for portal in destination.itervalues():
                portal.unravel()
    return r
