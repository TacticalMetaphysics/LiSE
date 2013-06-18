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
from effect import Effect, EffectDeck
import re


"""Items that exist in the simulated world. Their graphical
representations are not considered here."""


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

    def __init__(self, db):
        if stringlike(self.dimension):
            dimname = self.dimension
        else:
            dimname = self.dimension.name
        if dimname not in db.locdict:
            db.locdict[dimname] = {}
        if dimname not in db.itemdict:
            db.itemdict[dimname] = {}
        self.db = db
        self.updcontents()
        self.contents_fresh = True

    def __str__(self):
        return self.name

    def __contains__(self, that):
        if stringlike(that):
            thatname = that
        else:
            thatname = that.name
        return self.db.locdict[that.dimension][thatname] == self

    def __len__(self):
        i = 0
        for loc in self.db.locdict[self.dimension].itervalues():
            if loc == self:
                i += 1
        return i

    def __iter__(self):
        r = []
        for pair in self.db.locdict[self.dimension].iteritems():
            if pair[1] == self:
                r.append(self.itemdict[pair[0]])
        return iter(r)

    def __getattr__(self, attrn):
        if attrn == 'contents':
            if not self.contents_fresh:
                self.updcontents()
            return self.real_contents
        else:
            raise AttributeError(
                "Item instance has no such attribute: " +
                attrn)

    def updcontents(self):
        self.real_contents = set()
        for pair in self.db.locdict[self.dimension].iteritems():
            if pair[1] == self:
                self.real_contents.add(pair[0])
        self.contents_fresh = True

    def add(self, that):
        if stringlike(that.dimension):
            dimn = that.dimension
        else:
            dimn = that.dimension.name
        self.db.locdict[dimn][that.name] = self
        self.contents_fresh = False

    def assert_can_contain(self, other):
        pass


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
        self.dimension = dimension
        self.name = name
        if db is not None:
            dimname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if dimname not in db.itemdict:
                db.itemdict[dimname] = {}
            if dimname not in db.placedict:
                db.placedict[dimname] = {}
            db.itemdict[dimname][self.name] = self
            db.placedict[dimname][self.name] = self
        Item.__init__(self, db)

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)

    def __getattr__(self, attrn):
        if attrn == 'spot':
            if stringlike(self.dimension):
                dimn = self.dimension
            else:
                dimn = self.dimension.name
            return self.db.spotdict[dimn][self.name]
        else:
            raise AttributeError(
                "Place instance has no such attribute: " +
                attrn)

    def unravel(self):
        """Get myself a real Dimension object if I don't have one."""
        db = self.db
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if not hasattr(self, 'contents'):
            if self.dimension.name not in db.contentsdict:
                db.contentsdict[self.dimension.name] = {}
            if self.name not in db.contentsdict[self.dimension.name]:
                db.contentsdict[self.dimension.name][self.name] = set()

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name

    def can_contain(self, other):
        """Does it make sense for that to be here?"""
        return True


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
        self.dimension = dimension
        self.orig = from_place
        self.dest = to_place
        dimname = None
        from_place_name = None
        to_place_name = None
        if stringlike(self.dimension):
            dimname = self.dimension
        else:
            dimname = self.dimension.name
        if stringlike(self.orig):
            from_place_name = self.orig
        else:
            from_place_name = self.orig.name
        if stringlike(self.dest):
            to_place_name = self.dest
        else:
            to_place_name = self.dest.name
        self.name = "Portal({0}->{1})".format(
            from_place_name, to_place_name)
        podd = db.portalorigdestdict
        pdod = db.portaldestorigdict
        for d in (db.itemdict, podd, pdod):
            if dimname not in d:
                d[dimname] = {}
        if from_place_name not in podd[dimname]:
            podd[dimname][from_place_name] = {}
        if to_place_name not in pdod[dimname]:
            pdod[dimname][to_place_name] = {}
        db.itemdict[dimname][self.name] = self
        podd[dimname][from_place_name][to_place_name] = self
        pdod[dimname][to_place_name][from_place_name] = self
        Item.__init__(self, db)

    def __repr__(self):
        if stringlike(self.orig):
            origname = self.orig
        else:
            origname = self.orig.name
        if stringlike(self.dest):
            destname = self.dest
        else:
            destname = self.dest.name
        return 'Portal({0}->{1})'.format(origname, destname)

    def unravel(self):
        db = self.db
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.orig):
            self.orig = db.itemdict[self.dimension.name][self.orig]
        if stringlike(self.dest):
            self.dest = db.itemdict[self.dimension.name][self.dest]

    def __hash__(self):
        return self.hsh

    def get_weight(self):
        return self.weight

    def get_avatar(self):
        return self.avatar

    def is_passable_now(self):
        return True

    def admits(self, traveler):
        """Return True if I want to let the given thing enter me, False
otherwise."""
        return True

    def is_now_passable_by(self, traveler):
        return self.isPassableNow() and self.admits(traveler)

    def get_dest(self):
        return self.dest

    def get_orig(self):
        return self.orig

    def get_ends(self):
        return [self.orig, self.dest]

    def touches(self, place):
        return self.orig is place or self.dest is place

    def find_neighboring_portals(self):
        return self.orig.portals + self.dest.portals

    def notify_moving(self, thing, amount):
        """Handler for when a thing moves through me by some amount of my
length. Does nothing by default."""
        pass


class Thing(Item):
    """The sort of item that has a particular location at any given time.

Every Thing has a Journey and a Schedule, but either may be empty.

Things can contain other Things and be contained by other Things. This
is independent of where they are "located," which is always a
Place. But any things that contain one another should share locations,
too.

Things can *also* occupy a Portal. This normally doesn't prevent them
from occupying the Place that the Portal is from! This is just a
convenience for when movement events don't go right; then the Thing
involved will get kicked out of the Portal, leaving it in its original
location.

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
        self.dimension = dimension
        self.name = name
        self.start_location = location
        self.journey_step = journey_step
        self.journey_progress = journey_progress
        self.age = age
        self.schedule = schedule
        self.hsh = hash(hash(self.dimension) + hash(self.name))
        if stringlike(self.dimension):
            dimname = self.dimension
        else:
            dimname = self.dimension.name
        if dimname not in db.itemdict:
            db.itemdict[dimname] = {}
        if dimname not in db.thingdict:
            db.thingdict[dimname] = {}
        if dimname not in db.locdict:
            db.locdict[dimname] = {}
        db.itemdict[dimname][self.name] = self
        db.thingdict[dimname][self.name] = self
        db.locdict[dimname][self.name] = location
        Item.__init__(self, db)

    def unravel(self):
        """Dereference stringlike attributes.

Also add self to location, if applicable.

        """
        db = self.db
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.start_location):
            locn = self.start_location
            location = db.itemdict[self.dimension.name][locn]
        else:
            location = self.start_location
        db.locdict[self.dimension.name][self.name] = location
        self.location.add(self)
        if stringlike(self.schedule):
            self.schedule = db.scheduledict[self.dimension.name][self.name]
            self.schedule.unravel(db)
        if (
                self.dimension.name in db.journeydict and
                self.name in db.journeydict[self.dimension.name]):
            self.journey = db.journeydict[self.dimension.name][self.name]
            self.journey.dimension = self.dimension
            self.journey.thing = self
            if self.schedule is None:
                self.schedule = self.journey.schedule()

    def __getattr__(self, attrn):
        if attrn == 'location':
            dimn = str(self.dimension)
            return self.db.locdict[dimn][self.name]
        else:
            raise AttributeError(
                "Thing instance has no such attribute: " +
                attrn)

    def __hash__(self):
        return self.hsh

    def __str__(self):
        return self.name

    def __iter__(self):
        return (self.dimension, self.name)

    def __repr__(self):
        if self.location is None:
            loc = "nowhere"
        else:
            loc = str(self.location)
        return self.name + "@" + loc

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

    def move_thru_portal(self, amount):
        """Move this amount through the portal I'm in"""
        if not isinstance(self.location, Portal):
            raise PortalException(
                """The location of {0} is {1},
which is not a portal.""".format(repr(self), repr(self.location)))
        self.location.notify_moving(self, amount)
        self.journey_progress += amount

    def speed_thru(self, port):
        """Given a portal, return an integer for the number of ticks it would
take me to pass through it."""
        return 60


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
        self.dimension = dimension
        self.thing = thing
        self.steps = []
        for st in steps:
            if isinstance(st, tuple):
                self.steps.append(st)
            else:
                if stringlike(st.orig):
                    origname = st.orig
                else:
                    origname = st.orig.name
                if stringlike(st.dest):
                    destname = st.dest
                else:
                    destname = st.dest.name
                self.steps.append((origname, destname))
        if stringlike(self.dimension):
            dimname = self.dimension
        else:
            dimname = self.dimension.name
        if stringlike(self.thing):
            thingname = self.thing
        else:
            thingname = self.thing.name
        if dimname not in db.journeydict:
            db.journeydict[dimname] = {}
        db.journeydict[dimname][thingname] = self
        self.db = db

    def unravel(self):
        """Dereference all steps."""
        db = self.db
        i = 0
        while i < len(self.steps):
            if stringlike(self.steps[i]):
                self.steps[i] = (
                    db.portaldict[self.dimension.name][self.steps[i]])
            i += 1

    def __len__(self):
        """Get the number of steps in the Journey.

        Returns the number of Portals the traveller ever passed
        through or ever will on this Journey.

        """
        return len(self.steps)

    def steps_left(self):
        """Get the number of steps remaining until the end of the Journey.

        Returns the number of Portals left to be travelled through,
        including the one the traveller is in right now.

        """
        return len(self.steps) - self.thing.journey_step

    def __getitem__(self, i):
        """Get the ith next Portal in the journey.

        __getitem__(0) returns the portal the traveller is presently
        travelling through. __getitem__(1) returns the one it wil travel
        through after that, etc. __getitem__(-1) returns the step before
        this one, __getitem__(-2) the one before that, etc.

        """
        (orign, destn) = self.steps[i+self.thing.journey_step]
        if stringlike(self.thing.dimension):
            dimn = self.thing.dimension
        else:
            dimn = self.thing.dimension.name
        return self.db.portalorigdestdict[dimn][orign][destn]

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

    def move_thru_portal(self, prop):
        """Move the thing the specified amount through the current
portal. Return the updated progress.

*Don't* move the thing *out* of the portal. Raise a PortalException if
the thing isn't in a portal at all.

        """
        return self.thing.move_thru_portal(prop)

    def next(self):
        """Teleport the thing to the destination of the portal it's in, and
advance the journey.

Return a pair containing the new place and the new portal. If the
place is the destination of the journey, the new portal will be
None.

        """
        oldport = self.thing.location
        place = self.thing.enter(oldport.dest)
        self.thing.journey_step += 1
        self.thing.journey_progress = 0.0
        try:
            newport = self[0]
        except IndexError:
            newport = None
        return (place, newport)

    def __setitem__(self, idx, port):
        """Put given portal into the step list at given index, padding steplist
with None as needed."""
        while idx >= len(self.steps):
            self.steps.append(None)
        self.steps[idx] = port

    def schedule(self, delay=0):
        """Add events representing this journey to the very end of the thing's
schedule, if it has one.

Optional argument delay adds some ticks of inaction between the end of
the schedule and the beginning of the journey. If there's no schedule,
or an empty one, that's the amount of time from the start of the game
that the thing will wait before starting the journey.

Then return the schedule. Just for good measure.

        """
        db = self.db
        if not hasattr(self.thing, 'schedule') or self.thing.schedule is None:
            self.thing.schedule = Schedule(
                db, self.thing.dimension, self.thing)
        try:
            end = max(self.thing.schedule.events_ending.viewkeys())
        except ValueError:
            end = 1
        start = end + delay
        for port in self:
            newev = PortalTravelEvent(db, self.thing, port, False)
            evlen = self.thing.speed_thru(port)
            newev.start = start
            newev.length = evlen
            self.thing.schedule.add(newev)
            start += evlen + delay + 1
        self.thing.schedule.unravel()
        return self.thing.schedule


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
        self.dimension = dimension
        self.item = item
        self.events = {}
        self.events_starting = dict()
        self.events_ending = dict()
        self.events_ongoing = dict()
        self.cached_commencements = {}
        self.cached_processions = {}
        self.cached_conclusions = {}
        if stringlike(self.dimension):
            dimname = self.dimension
        else:
            dimname = self.dimension.name
        if stringlike(self.item):
            itemname = self.item
        else:
            itemname = self.item.name
        if dimname not in db.scheduledict:
            db.scheduledict[dimname] = {}
        db.scheduledict[dimname][itemname] = self
        self.db = db

    def tabdict(self):
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
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.item):
            self.item = db.itemdict[self.dimension.name][self.item]
        self.add_global = db.add_event
        self.remove_global = db.remove_event
        self.discard_global = db.discard_event
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
