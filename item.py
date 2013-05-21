from util import (
    SaveableMetaclass,
    dictify_row,
    stringlike)
from event import (
    lookup_between,
    Event,
    SenselessEvent,
    ImpossibleEvent,
    IrrelevantEvent,
    ImpracticalEvent)
from effect import Effect, EffectDeck
import re


"""Items that exist in the simulated world. Their graphical
representations are not considered here."""


__metaclass__ = SaveableMetaclass


class LocationException(Exception):
    """Exception raised when a Thing tried to go someplace that made no
sense."""
    pass


class ContainmentException(Exception):
    """Exception raised when a Thing tried to go into another Thing, and
it made no sense."""
    pass


class Item:
    """Master class for all items that are in the game world. Doesn't do
much."""
    tables = [
        ("item",
         {"dimension": "text",
          "name": "text"},
         ("dimension", "name"),
         {},
         [])]


class Place(Item):
    """The 'top level' of the world model. Places contain Things and are
connected to other Places, forming a graph."""
    tables = [
        ("place",
         {"dimension": "text",
          "name": "text"},
         ("dimension", "name"),
         {},
         [])]

    def __init__(self, dimension, name, db):
        """Return a Place of the given name, in the given dimension. Register
it with the placedict and itemdict in the db."""
        self.dimension = dimension
        self.name = name
        self.contents = set()
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

    def unravel(self, db):
        """Get myself a real Dimension object if I don't have one."""
        if isinstance(self.dimension, str):
            self.dimension = db.dimensiondict[self.dimension]

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name

    def add(self, other):
        """Put a Thing in this Place, but don't check if it makes sense. Be
careful!"""
        self.contents.add(other)

    def remove(self, other):
        """Remove a Thing from this Place, but don't check if it makes
sense. Be careful!"""
        self.contents.remove(other)


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
         {"dimension": "text",
          "name": "text",
          "location": "text not null",
          "container": "text default null",
          "portal": "text default null",
          "journey_progress": "float default 0.0",
          "journey_step": "integer default 0",
          "age": "integer default 0"},
         ("dimension", "name"),
         {"dimension, container": ("thing", "dimension, name")},
         [])]

    def __init__(self, dimension, name, location, container,
                 portal=None, journey_step=0, journey_progress=0.0, age=0,
                 schedule=None, db=None):
        """Return a Thing in the given dimension, location, and container,
with the given name. Its contents will be empty to start; later on,
point some other Things' container attributes at this Thing to put
them in.

Register with the database's itemdict and thingdict too.

        """
        self.dimension = dimension
        self.name = name
        self.location = location
        self.container = container
        self.portal = portal
        self.journey_step = journey_step
        self.journey_progress = journey_progress
        self.age = age
        self.schedule = schedule
        self.contents = set()
        self.hsh = hash(hash(self.dimension) + hash(self.name))
        if db is not None:
            dimname = None
            if stringlike(self.dimension):
                dimname = self.dimension
            else:
                dimname = self.dimension.name
            if dimname not in db.itemdict:
                db.itemdict[dimname] = {}
            if dimname not in db.thingdict:
                db.thingdict[dimname] = {}
            db.itemdict[dimname][self.name] = self
            db.thingdict[dimname][self.name] = self

    def unravel(self, db):
        """If dimension, locatiaon, container, portal, or schedule are names
rather than instances or None, dereference them.

Also add self to location, and container if applicable.

        """
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.location):
            self.location = db.itemdict[self.dimension.name][self.location]
        if stringlike(self.container):
            self.container = db.itemdict[self.dimension.name][self.container]
        if stringlike(self.portal):
            self.portal = db.itemdict[self.dimension.name][self.portal]
        if stringlike(self.schedule):
            self.schedule = db.scheduledict[self.dimension.name][self.name]
            self.schedule.unravel(db)
        if (
                self.dimension.name in db.journeydict and
                self.name in db.journeydict[self.dimension.name]):
            self.journey = db.journeydict[self.dimension.name][self.name]
            self.journey.unravel(db)
            if self.schedule is None:
                self.schedule = self.journey.schedule(db)
                self.schedule.unravel(db)
        if self.container is not None:
            self.container.add(self)
        self.location.add(self)

    def __hash__(self):
        return self.hsh

    def __str__(self):
        return "(%s, %s)" % (self.dimension, self.name)

    def __iter__(self):
        return (self.dimension, self.name)

    def __repr__(self):
        if self.location is None:
            loc = "nowhere"
        else:
            loc = str(self.location)
        return self.name + "@" + loc

    def add(self, it):
        """Add an item to my contents without caring if it makes any sense to
do so.

This will not, for instance, remove the item from wherever it currently is.

"""
        self.contents.add(it)

    def remove(self, it):
        """Remove an item from my contents without putting it anywhere else.

The item might end up not being contained in anything, leaving it
inaccessible. Beware.

"""
        self.contents.remove(it)

    def can_enter(self, it):
        """Can I enter the given place, portal, or thing?"""
        return True

    def can_contain(self, it):
        """Can I contain that thing?"""
        return True

    def enter(self, it):
        """Check if I can go into the destination, and if so, do it
immediately. Else raise exception as appropriate."""
        if isinstance(it, Place):
            self.enter_place(it)
        elif isinstance(it, Portal):
            self.enter_portal(it)
        elif isinstance(it, Thing):
            self.enter_thing(it)
        else:
            raise Exception("%s tried to enter %s, which is not enterable" %
                            (self.name, repr(it)))

    def enter_place(self, it):
        """Enter a location, with a few sanity checks"""
        if self.can_enter(it) and it.can_contain(self):
            if self.container is None or self.container.location == it:
                self.location = it
                self.db.placecontentsdict[self.name] = it
            else:
                raise LocationException("%s tried to enter Place %s before "
                                        "its container %s did" %
                                        (self.name, it.name,
                                         self.container.name))
        else:
            raise LocationException("%s cannot enter Place %s" %
                                    (self.name, it.name))

    def enter_portal(self, it):
        """Enter a portal, after a few sanity checks"""
        if self.can_enter(it) and it.can_contain(self):
            self.container.remove(self)
            it.add(self)
        else:
            raise ContainmentException("%s cannot enter Portal %s" %
                                       (self.name, it.name))

    def enter_thing(self, it):
        """Enter another thing, after a few sanity checks"""
        if self.can_enter(it) and it.can_contain(self):
            self.container.remove(self)
            it.add(self)
        else:
            raise ContainmentException("%s cannot enter Thing %s" %
                                       (self.name, it.name))

    def speed_thru(self, port):
        """Given a portal, return an integer for the number of ticks it would
take me to pass through it."""

        return 60


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
         {"dimension": "text",
          "thing": "text",
          "idx": "integer",
          "portal": "text"},
         ("dimension", "thing", "idx"),
         {"dimension, thing": ("thing", "dimension, name"),
          "dimension, portal": ("portal", "dimension, name")},
         [])]

    def __init__(self, dimension, thing, steps, db=None):
        """Return a journey in the given dimension, wherein the given thing
takes the given steps.

If db is provided, register in its journeydict.

        """
        self.dimension = dimension
        self.thing = thing
        self.steps = steps
        if db is not None:
            dimname = None
            thingname = None
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

    def unravel(self, db):
        """Dereference dimension, thing, and all steps."""
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.thing):
            self.thing = db.itemdict[self.dimension.name][self.thing]
        i = 0
        while i < len(self.steps):
            if stringlike(self.steps[i]):
                self.steps[i] = db.portaldict[self.dimension.name][self.steps[i]]
            i += 1

    def steps(self):
        """Get the number of steps in the Journey.

        Returns the number of Portals the traveller ever passed
        through or ever will on this Journey.

        """
        return len(self.steps)

    def stepsleft(self):
        """Get the number of steps remaining until the end of the Journey.

        Returns the number of Portals left to be travelled through,
        including the one the traveller is in right now.

        """
        return len(self.steps) - self.thing.journey_step

    def getstep(self, i):
        """Get the ith next Portal in the journey.

        getstep(i) => Portal

        getstep(0) returns the portal the traveller is presently
        travelling through. getstep(1) returns the one it wil travel
        through after that, etc. getstep(-1) returns the step before
        this one, getstep(-2) the one before that, etc.

        If i is out of range, returns None.

        """
        return self.steps[i+self.thing.journey_step]

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

    def move(self, prop):

        """Move the specified amount through the current portal.

        move(prop) => Portal

        Increments the current progress, and then adjusts the next and
        previous portals as needed.  Returns the Portal the traveller
        is now travelling through. prop may be negative.

        If the traveller moves past the end (or start) of the path,
        returns None.

        """
        self.thin.journey_progress += prop
        while self.thin.journey_progress >= 1.0:
            self.thing.journey_step += 1
            self.thin.journey_progress -= 1.0
        while self.thin.journey_progress < 0.0:
            self.thing.journey_step -= 1
            self.thin.journey_progress += 1.0
        if self.thing.journey_step > len(self.steplist):
            return None
        else:
            return self.getstep(0)

    def set_step(self, idx, port):
        """Put given portal into the steplist at given index, padding steplist
with None as needed."""
        while idx >= len(self.steplist):
            self.steplist.append(None)
        self.steplist[idx] = port

    def gen_event(self, step, db):
        """Make an Event representing every tick of travel through the given
portal.

The Event will not have a start or a length.

        """
        # Work out how many ticks this is going to take.  Of course,
        # just because a thing is scheduled to travel doesn't mean it
        # always will--which makes it convenient to have
        # events to resolve all the steps, ne?
        if stringlike(step):
            commence_arg = step
            proceed_arg = step
            conclude_arg = re.match(
                "portal\[.*?->(.*?)\]", step).groups()[0]
        elif isinstance(step, dict):
            commence_arg = step["portal"]
            proceed_arg = step["portal"]
            conclude_arg = re.match(
                "portal\[.*?->(.*?)\]", step["portal"]).groups()[0]
        else:
            commence_arg = step.name
            proceed_arg = step.name
            conclude_arg = step.dest.name
        if stringlike(self.dimension):
            dimname = self.dimension
        elif isinstance(self.dimension, dict):
            dimname = self.dimension["name"]
        else:
            dimname = self.dimension.name
        if stringlike(self.thing):
            thingname = self.thing
        elif isinstance(self.thing, dict):
            thingname = self.thing["name"]
        else:
            thingname = self.thing.name
        event_name = "%s:%s-thru-%s" % (
            dimname, thingname, commence_arg)
        if event_name in db.eventdict:
            return db.eventdict[event_name]

        commence_s = "{0}.{1}.enter({2})".format(
            dimname, thingname, commence_arg)
        if commence_s in db.effectdeckdict:
            commence_deck = db.effectdeckdict[commence_s]
        else:
            effd = {
                "name": commence_s,
                "func": "%s.%s.enter" % (dimname, thingname),
                "arg": commence_arg,
                "dict_hint": "dimension.thing",
                "db": db}
            if effd["name"] in db.effectdict:
                commence = db.effectdict[effd["name"]]
                assert(commence.func == effd["func"])
                assert(commence.arg == effd["arg"])
            else:
                commence = Effect(**effd)
            commence_deck = EffectDeck(commence_s, [commence], db)
        proceed_s = "%s.%s.remain(%s)" % (
            dimname, thingname, proceed_arg)
        if proceed_s in db.effectdeckdict:
            proceed_deck = db.effectdeckdict[proceed_s]
        else:
            effd = {
                "name": proceed_s,
                "func": "%s.%s.remain" % (dimname, thingname),
                "arg": proceed_arg,
                "dict_hint": "dimension.thing",
                "db": db}
            if effd["name"] in db.effectdict:
                proceed = db.effectdict[effd["name"]]
                assert(proceed.func == effd["func"])
                assert(proceed.arg == effd["arg"])
            else:
                proceed = Effect(**effd)
            proceed_deck = EffectDeck(proceed_s, [proceed], db)
        conclude_s = "%s.%s.enter(%s)" % (
            dimname, thingname, conclude_arg)
        if conclude_s in db.effectdeckdict:
            conclude_deck = db.effectdeckdict[conclude_s]
        else:
            effd = {
                "name": conclude_s,
                "func": "%s.%s.enter" % (dimname, thingname),
                "arg": conclude_arg,
                "dict_hint": "dimension.thing",
                "db": db}
            if effd["name"] in db.effectdict:
                conclude = db.effectdict[effd["name"]]
            else:
                conclude = Effect(**effd)
            conclude_deck = EffectDeck(conclude_s, [conclude], db)
        event_d = {
            "name": event_name,
            "text": "Movement",
            "ongoing": False,
            "commence_effects": commence_deck,
            "proceed_effects": proceed_deck,
            "conclude_effects": conclude_deck,
            "db": db}
        event = Event(**event_d)
        return event

    def schedule(self, db, start=0):
        """Make a Schedule filled with Events representing the steps in this
Journey.

        Optional argument start indicates the start time of the schedule.

        """
        stepevents = []
        last_end = start
        for step in self.steps:
            ev = self.gen_event(step, db)
            ev.start = last_end
            ev.length = self.thing.speed_thru(step)
            stepevents.append(ev)
            last_end = ev.start + ev.length
        s = Schedule(self.dimension, self.thing, db)
        for ev in stepevents:
            s.add(ev)
        return s


class Schedule:
    """Many events, all assocated with the same item in the same dimension,
and given start times and lengths.

Events in a given schedule are assumed never to overlap. This is not
true of events in different schedules.

    """
    tables = [
        ("scheduled_event",
         {"dimension": "text",
          "item": "text",
          "start": "integer",
          "event": "text not null",
          "length": "integer"},
         ("dimension", "item"),
         {"dimension, item": ("item", "dimension, name"),
          "event": ("event", "name")},
         [])]

    def __init__(self, dimension, item, db=None):
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
        if db is not None:
            dimname = None
            itemname = None
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
            if dimname not in db.startevdict:
                db.startevdict[dimname] = {}
            db.startevdict[dimname][itemname] = self.events_starting
            if dimname not in db.contevdict:
                db.contevdict[dimname] = {}
            db.contevdict[dimname][itemname] = self.events_ongoing
            if dimname not in db.endevdict:
                db.endevdict[dimname] = {}
            db.endevdict[dimname][itemname] = self.events_ending

    def __iter__(self):
        """Return iterator over my events in order of their start times."""
        return self.events.itervalues()

    def unravel(self, db):
        """Dereference dimension and item."""
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.item):
            self.item = db.itemdict[self.dimension.name][self.item]

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


    def discard(self, ev):
        """Remove an event from all my dictionaries in which it is a
member."""
        ev_end = ev.start + ev.length
        self.events_starting[ev.start].discard(ev)
        self.events_ending[ev_end].discard(ev)
        for i in xrange(ev.start+1, ev_end-1):
            self.events_ongoing[i].discard(ev)
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


class Portal(Item):
    """A one-directional connection between two places, whereby a Thing
may travel."""
    tables = [
        ("portal",
         {"dimension": "text",
          "name": "text",
          "from_place": "text",
          "to_place": "text"},
         ("dimension", "name"),
         {"dimension, name": ("item", "dimension, name"),
          "dimension, from_place": ("place", "dimension, name"),
          "dimension, to_place": ("place", "dimension, name")},
         [])]

    def __init__(self, dimension, name, from_place, to_place, db=None):
        """Return a portal in the given dimension, with the given name,
leading from the one given place to the other.

With db, register it in db's itemdict and portaldict.

        """
        self.dimension = dimension
        self.name = name
        self.orig = from_place
        self.dest = to_place
        if db is not None:
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
            podd = db.portalorigdestdict
            pdod = db.portaldestorigdict
            for d in [db.itemdict, db.portaldict, podd, pdod]:
                if dimname not in d:
                    d[dimname] = {}
            if from_place_name not in podd[dimname]:
                podd[dimname][from_place_name] = {}
            if to_place_name not in pdod[dimname]:
                pdod[dimname][to_place_name] = {}
            db.itemdict[dimname][self.name] = self
            db.portaldict[dimname][self.name] = self
            podd[dimname][from_place_name][to_place_name] = self
            pdod[dimname][to_place_name][from_place_name] = self

    def unravel(self, db):
        """Dereference dimension, origin, and destination."""
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.orig):
            self.orig = db.itemdict[self.dimension.name][self.orig]
        if stringlike(self.dest):
            self.dest = db.itemdict[self.dimension.name][self.dest]

    def __hash__(self):
        """Return hash of dimension and name, since they are constrained to be
unique by the database."""
        return self.hsh

    def get_weight(self):
        """Return 'weight' for the purposes of pathfinding. May have nothing
to do with how easily anything can pass through me."""
        return self.weight

    def get_avatar(self):
        """Return my 'avatar,' being a Thing that's meant to represent me in
some place or other. Maybe it's a door or something."""
        return self.avatar

    def is_passable_now(self):
        """Return whether anything can travel through me at the moment. This
returns False if I'm eg. full, or closed for maintenance, or otherwise
unusable but not in such a way that I should be considered a
non-portal."""
        return True

    def admits(self, traveler):
        """Return True if I want to let the given thing enter me, False otherwise."""
        return True

    def is_now_passable_by(self, traveler):
        """Return True if I am passable now by anyone and also by the given
traveler."""
        return self.isPassableNow() and self.admits(traveler)

    def get_dest(self):
        """Return my destination."""
        return self.dest

    def get_orig(self):
        """Return my origin."""
        return self.orig

    def get_ends(self):
        """Return pair of origin and destination."""
        return [self.orig, self.dest]

    def touches(self, place):
        """Return whether the given place is one of my two endpoints."""
        return self.orig is place or self.dest is place

    def find_neighboring_portals(self):
        """Return portals from my origin and from my destination, including
myself."""
        return self.orig.portals + self.dest.portals


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


def unravel_things(db, tdb):
    """Unravel thing objects in a dictionary keyed by names (but not
dimensions)."""
    for thing in tdb.itervalues():
        thing.unravel(db)
    return tdb


def unravel_things_in_dimensions(db, tddb):
    """Unravel thing objects in a 2D dictionary keyed by dimension name,
then thing name."""
    for things in tddb.itervalues():
        unravel_things(db, things)
    return tddb


def load_things_in_dimensions(db, dimnames):
    """Load all things in the named dimensions. Return a 2D dictionary of
things keyed by dimension name, then thing name."""
    return unravel_things_in_dimensions(
        db, read_things_in_dimensions(db, dimnames))


schedule_dimension_qryfmt = (
    "SELECT {0} FROM scheduled_event WHERE dimension IN "
    "({1})".format(
        ", ".join(Schedule.colnames["scheduled_event"]), "{0}"))


def read_schedules_in_dimensions(db, dimnames):
    """Read and instantiate, but do not unravel, all schedules in the
given dimensions.

Return a 2D dictionary of schedules keyed by dimension name, then item name.

    """
    qryfmt = schedule_dimension_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(dimnames)))
    db.c.execute(qrystr, dimnames)
    r = {}
    for dimname in dimnames:
        r[dimname] = {}
    for row in db.c:
        rowdict = dictify_row(row, Item.colnames["scheduled_event"])
        if rowdict["item"] not in r[rowdict["dimension"]]:
            r[rowdict["dimension"]][rowdict["item"]] = {
                "db": db,
                "dimension": rowdict["dimension"],
                "item": rowdict["item"],
                "events": {}}
        rptr = r[rowdict["dimension"]][rowdict["item"]]
        rptr["events"][rowdict["start"]] = {
            "event": rptr["event"],
            "start": rptr["start"],
            "length": rptr["length"]}
    for level0 in r.iteritems():
        (dimn, its) = level0
        for it in its.iteritems():
            (itn, sched) = it
            r[dimn][itn] = Schedule(**sched)
    return r


def unravel_schedules(db, schd):
    """Unravel schedules in a dict keyed by their items' names. Return the
same dict."""
    for sched in schd.itervalues():
        sched.unravel(db)
    return schd


def unravel_schedules_in_dimensions(db, schdd):
    """Unravel schedules previously read in by read_schedules or
read_schedules_in_dimensions."""
    for scheds in schdd.itervalues():
        unravel_schedules(db, scheds)
    return schdd


def load_schedules_in_dimensions(db, dimnames):
    """Load every schedule in the given dimensions.

Return a 2D dict keyed by dimension name, then item name.

    """
    return unravel_schedules_in_dimensions(
        db, read_schedules_in_dimensions(db, dimnames))


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
    db.c.execute(qrystr, dimnames)
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
        stepl[rowdict["idx"]] = rowdict["portal"]
    for item in r.iteritems():
        (dimname, journeys) = item
        for journey in journeys.iteritems():
            (thingname, jo) = journey
            r[dimname][thingname] = Journey(**jo)
    return r


def unravel_journeys(db, jod):
    """Unravel journeys in a dict keyed by their names. Return same
dict."""
    for jo in jod.itervalues():
        jo.unravel(db)
    return jod


def unravel_journeys_in_dimensions(db, jodd):
    """Unravel journeys previously read in by read_journeys or
read_journeys_in_dimensions."""
    for jod in jodd.itervalues():
        unravel_journeys(db, jod)
    return jodd


def load_journeys_in_dimensions(db, dimnames):
    """Load all journeys in the given dimensions.

Return them in a 2D dict keyed by dimension name, then thing name.

    """
    return unravel_journeys_in_dimensions(
        db, read_journeys_in_dimensions(db, dimnames))


place_dimension_qryfmt = (
    "SELECT {0} FROM place WHERE dimension IN "
    "({1})".format(
        ", ".join(Place.colns), "{0}"))


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
        r[rowdict["dimension"]][rowdict["name"]] = Place(**rowdict)
    return r


def unravel_places(db, pls):
    """Unravel places in a dict keyed by their names.

Return the same dict."""
    for pl in pls.itervalues():
        pl.unravel(db)
    return pls


def unravel_places_in_dimensions(db, pls):
    """Unravel places previously read in by read_places or
read_places_in_dimensions."""
    for pl in pls.itervalues():
        unravel_places(db, pl)
    return pls


def load_places_in_dimensions(db, dimnames):
    """Load all places in the given dimensions.

Return them in a 2D dict keyed by the dimension name, then the place
name.

    """
    return unravel_places_in_dimensions(
        db, load_places_in_dimensions(db, dimnames))


portal_dimension_qryfmt = (
    "SELECT {0} FROM portal WHERE dimension IN "
    "({1})".format(
        ", ".join(Portal.colnames["portal"]), "{0}"))


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
        r[rowdict["dimension"]][rowdict["name"]] = Portal(**rowdict)
    return r


def unravel_portals(db, portd):
    """Unravel portals in a dict keyed by names. Return the dict."""
    for port in portd.itervalues():
        port.unravel(db)
    return portd


def unravel_portals_in_dimensions(db, portdd):
    """Unravel portals in a 2D dict previously read in by read_portals or
read_portals_in_dimensions. Return the dict."""
    for ports in portdd.itervalues():
        unravel_portals(db, ports)
    return portdd


def load_portals_in_dimensions(db, dimnames):
    """Load all portals in the given dimensions.

Return them in a 2D dict keyed by dimension name, then portal name.

    """
    return unravel_portals_in_dimensions(
        db, read_portals_in_dimensions(db, dimnames))
