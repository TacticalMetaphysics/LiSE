from util import (
    SaveableMetaclass,
    dictify_row,
    stringlike)
from event import (
    Event,
    SenselessEvent,
    ImpossibleEvent,
    IrrelevantEvent,
    ImpracticalEvent)
from effect import Effect, EffectDeck
import re


__metaclass__ = SaveableMetaclass


class LocationException(Exception):
    pass


class ContainmentException(Exception):
    pass


class Item:
    tables = [
        ("item",
         {"dimension": "text",
          "name": "text"},
         ("dimension", "name"),
         {},
         [])]


class Place(Item):
    tables = [
        ("place",
         {"dimension": "text",
          "name": "text"},
         ("dimension", "name"),
         {},
         [])]

    def __init__(self, dimension, name, db):
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
        if isinstance(self.dimension, str):
            self.dimension = db.dimensiondict[self.dimension]

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name

    def add(self, other):
        self.contents.add(other)

    def remove(self, other):
        self.contents.remove(other)


class Thing(Item):
    tables = [
        ("thing",
         {"dimension": "text",
          "name": "text",
          "location": "text not null",
          "container": "text default null",
          "portal": "text default null",
          "progress": "float default 0.0",
          "age": "integer default 0"},
         ("dimension", "name"),
         {"dimension, container": ("thing", "dimension, name")},
         [])]

    def __init__(self, dimension, name, location, container,
                 portal=None, journey_step=0, progress=0.0, age=0,
                 schedule=None, db=None):
        self.dimension = dimension
        self.name = name
        self.location = location
        self.container = container
        self.portal = portal
        self.journey_step = journey_step
        self.journey_progress = progress
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
                self.schedule = self.journey.schedule()
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
        return True

    def can_contain(self, it):
        return True

    def enter(self, it):
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
        if self.can_enter(it) and it.can_contain(self):
            self.container.remove(self)
            it.add(self)
        else:
            raise ContainmentException("%s cannot enter Portal %s" %
                                       (self.name, it.name))

    def enter_thing(self, it):
        if self.can_enter(it) and it.can_contain(self):
            self.container.remove(self)
            it.add(self)
        else:
            raise ContainmentException("%s cannot enter Thing %s" %
                                       (self.name, it.name))

    def speed_thru(self, port):
        """Given a portal, return a float representing how fast I can pass
through it.

Speed is equal to the reciprocal of the number of ticks of the
game-clock it takes to pass through the portal.

        """
        return 1/60.


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
        if stringlike(self.dimension):
            self.dimension = db.dimensiondict[self.dimension]
        if stringlike(self.thing):
            self.thing = db.itemdict[self.dimension.name][self.thing]
        for step in self.steps:
            if stringlike(step):
                step = db.itemdict[self.dimension.name][step]

    def steps(self):
        """Get the number of steps in the Journey.

        steps() => int

        Returns the number of Portals the traveller ever passed
        through or ever will on this Journey.

        """
        return len(self.steps)

    def stepsleft(self):
        """Get the number of steps remaining until the end of the Journey.

        Returns the number of Portals left to be travelled through,
        including the one the traveller is in right now.

        """
        return len(self.steps) - self.thing.curstep

    def getstep(self, i):
        """Get the ith next Portal in the journey.

        getstep(i) => Portal

        getstep(0) returns the portal the traveller is presently
        travelling through. getstep(1) returns the one it wil travel
        through after that, etc. getstep(-1) returns the step before
        this one, getstep(-2) the one before that, etc.

        If i is out of range, returns None.

        """
        return self.steps[i+self.curstep]

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
        self.thing.progress += prop
        while self.thing.progress >= 1.0:
            self.thing.curstep += 1
            self.thing.progress -= 1.0
        while self.thing.progress < 0.0:
            self.thing.curstep -= 1
            self.thing.progress += 1.0
        if self.thing.curstep > len(self.steplist):
            return None
        else:
            return self.getstep(0)

    def set_step(self, idx, port):
        while idx >= len(self.steplist):
            self.steplist.append(None)
        self.steplist[idx] = port

    def gen_event(self, step, db=None):
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
        commence_s = "{0}.{1}.enter({2})".format(
            dimname, thingname, commence_arg)
        effd = {
            "name": commence_s,
            "func": "%s.%s.enter" % (dimname, thingname),
            "arg": commence_arg,
            "dict_hint": "dimension.thing",
            "db": db}
        commence = Effect(**effd)
        commence_deck = EffectDeck(commence_s, [commence], db)
        proceed_s = "%s.%s.remain(%s)" % (
            dimname, thingname, proceed_arg)
        effd = {
            "name": proceed_s,
            "func": "%s.%s.remain" % (dimname, thingname),
            "arg": proceed_arg,
            "dict_hint": "dimension.thing",
            "db": db}
        proceed = Effect(**effd)
        proceed_deck = EffectDeck(proceed_s, [proceed], db)
        conclude_s = "%s.%s.enter(%s)" % (
            dimname, thingname, conclude_arg)
        effd = {
            "name": conclude_s,
            "func": "%s.%s.enter" % (dimname, thingname),
            "arg": conclude_arg,
            "dict_hint": "dimension.thing",
            "db": db}
        conclude = Effect(**effd)
        conclude_deck = EffectDeck(conclude_s, [conclude], db)
        event_name = "%s:%s-thru-%s" % (
            dimname, thingname, commence_arg),
        event_d = {
            "name": event_name,
            "ongoing": False,
            "commence_effects": commence_deck,
            "proceed_effects": proceed_deck,
            "conclude_effects": conclude_deck,
            "db": db}
        event = Event(**event_d)
        return event

    def schedule(self, start=0):
        """Make a Schedule filled with Events representing the steps in this
Journey.

        Optional argument start indicates the start time of the schedule.

        """
        stepevents = []
        for step in self.steps:
            ev = self.gen_event(step)
            ev.start = start
            ev.length = self.thing.speed_thru(step)
        s = Schedule(self.dimension, self.thing)
        for ev in stepevents:
            s.add(ev)
        return s


class Schedule:
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
        self.dimension = dimension
        self.item = item
        self.events_starting = dict()
        self.events_ending = dict()
        self.ongoing = set()
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

    def unravel(self, db):
        if isinstance(self.dimension, str):
            self.dimension = db.dimensiondict[self.dimension]
        if isinstance(self.item, str):
            self.item = db.itemdict[self.dimension.name][self.item]

    def advance(self, n):
        # advance time by n ticks
        prior_age = self.age
        new_age = prior_age + n
        starts = []
        ends = []
        for i in xrange(prior_age, new_age):
            startevs = iter(self.events_starting[i])
            endevs = iter(self.events_ending[i])
            starts.extend(startevs)
            ends.extend(endevs)
        for ev in starts:
            try:
                ev.commence()
            except SenselessEvent:
                # Actually, the various event exceptions ought to
                # provide info on the kind of failure that I could
                # parse and show to the user as applicable.
                continue
            except ImpossibleEvent:
                continue
            except IrrelevantEvent:
                continue
            except ImpracticalEvent:
                pass
            self.ongoing.add(ev)
        for ev in ends:
            ev.conclude()
            self.ongoing.remove(ev)
        for ev in iter(self.ongoing):
            ev.proceed()
        self.age = new_age

    def add(self, ev):
        if not hasattr(ev, 'end'):
            ev.end = ev.start + ev.length
        if ev.start not in self.events_starting:
            self.events_starting[ev.start] = set()
        if ev.end not in self.events_ending:
            self.events_ending[ev.end] = set()
        self.events_starting[ev.start].add(ev)
        self.events_ending[ev.end].add[ev]

    def timeframe(self, start, end):
        """Return a set of events starting or ending within the given
timeframe.

Events are assumed never to overlap. This is for ease of use only. You
can make something do many things at once by turning it into a
container, and putting things inside, each with one of the schedules
you want the container to follow.

        """
        r = set()
        for i in xrange(start, end):
            try:
                r.add(self.events_starting[i])
            except KeyError:
                pass
            try:
                r.add(self.events_ending[i])
            except KeyError:
                pass
        return r


class Portal(Item):
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


thing_dimension_qryfmt = (
    "SELECT {0} FROM thing WHERE dimension IN "
    "({1})".format(
        ", ".join(Thing.colns), "{0}"))


def read_things_in_dimensions(db, dimnames):
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
    for thing in tdb.itervalues():
        thing.unravel(db)
    return tdb


def unravel_things_in_dimensions(db, tddb):
    for things in tddb.itervalues():
        unravel_things(db, things)
    return tddb


def load_things_in_dimensions(db, dimnames):
    return unravel_things_in_dimensions(
        db, read_things_in_dimensions(db, dimnames))


schedule_dimension_qryfmt = (
    "SELECT {0} FROM scheduled_event WHERE dimension IN "
    "({1})".format(
        ", ".join(Schedule.colnames["scheduled_event"]), "{0}"))


def read_schedules_in_dimensions(db, dimnames):
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
    for sched in schd.itervalues():
        sched.unravel(db)
    return schd


def unravel_schedules_in_dimensions(db, schdd):
    for scheds in schdd.itervalues():
        unravel_schedules(db, scheds)
    return schdd


def load_schedules_in_dimensions(db, dimnames):
    return unravel_schedules_in_dimensions(
        db, read_schedules_in_dimensions(db, dimnames))


journey_dimension_qryfmt = (
    "SELECT {0} FROM journey_step WHERE dimension IN "
    "({1})".format(
        ", ".join(Journey.colnames["journey_step"]), "{0}"))


def read_journeys_in_dimensions(db, dimnames):
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
    for jo in jod.itervalues():
        jo.unravel(db)
    return jod


def unravel_journeys_in_dimensions(db, jodd):
    for jod in jodd.itervalues():
        unravel_journeys(db, jod)
    return jodd


def load_journeys_in_dimensions(db, dimnames):
    return unravel_journeys_in_dimensions(
        db, read_journeys_in_dimensions(db, dimnames))


place_dimension_qryfmt = (
    "SELECT {0} FROM place WHERE dimension IN "
    "({1})".format(
        ", ".join(Place.colns), "{0}"))


def read_places_in_dimensions(db, dimnames):
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
    for pl in pls.itervalues():
        pl.unravel(db)
    return pls


def unravel_places_in_dimensions(db, pls):
    for pl in pls.itervalues():
        unravel_places(db, pl)
    return pls


def load_places_in_dimensions(db, dimnames):
    return unravel_places_in_dimensions(
        db, load_places_in_dimensions(db, dimnames))


portal_dimension_qryfmt = (
    "SELECT {0} FROM portal WHERE dimension IN "
    "({1})".format(
        ", ".join(Portal.colnames["portal"]), "{0}"))


def read_portals_in_dimensions(db, dimnames):
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
    for port in portd.itervalues():
        port.unravel(db)
    return portd


def unravel_portals_in_dimensions(db, portdd):
    for ports in portdd.itervalues():
        unravel_portals(db, ports)
    return portdd


def load_portals_in_dimensions(db, dimnames):
    return unravel_portals_in_dimensions(
        db, read_portals_in_dimensions(db, dimnames))
