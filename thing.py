from item import Item
from portal import Portal
from event import (
    ImpossibleEvent,
    PortalTravelEvent,
    lookup_between,
    read_events)
from util import (
    dictify_row,
    SaveableMetaclass,
    PortalException,
    place2idx)
from logging import getLogger


__metaclass__ = SaveableMetaclass


logger = getLogger(__name__)


class Thing(Item):
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
         {"dimension, thing": ("item", "dimension, name"),
          "dimension, location": ("item", "dimension, name")},
         []),
        ("portal_progress",
         {"dimension": "text not null default 'Physical'",
          "thing": "text not null",
          "branch": "integer not null default 0",
          "tick_from": "integer not null default 0",
          "tick_to": "integer default null",
          "progress": "float not null default 0.0"},
         ("dimension", "thing", "branch", "tick_from"),
         {"dimension, thing": ("thing_loc", "dimension, thing")},
         ["progress>=0.0", "progress<=1.0"])]
          
    def __init__(self, db, dimension, name, location,
                 portal_progress=0.0, age=0,
                 schedule=None):
        """Return a Thing in the given dimension and location,
with the given name. Its contents will be empty to start; later on,
point some other Things' location attributes at this Thing to put
them in.

Register with the database's itemdict and thingdict too.

        """
        Item.__init__(self, db, dimension, name)
        self.start_location = location
        self.portal_progress = portal_progress
        self.age = age
        if self._dimension not in db.itemdict:
            db.itemdict[self._dimension] = {}
        if self._dimension not in db.thingdict:
            db.thingdict[self._dimension] = {}
        if self._dimension not in db.locdict:
            db.locdict[self._dimension] = {}
        db.thingdict[self._dimension][self.name] = self
        db.locdict[self._dimension][self.name] = location

    def __getattr__(self, attrn):
        if attrn == 'location':
            return self.db.locdict[self._dimension][self.name]
        elif attrn == 'schedule':
            return self.db.get_schedule(self._dimension, self.name)
        elif attrn == 'pawn':
            return self.db.pawndict[self._dimension][self.name]
        elif attrn == 'journey':
            return self.db.get_journey(self._dimension, self.name)
        else:
            return Item.__getattr__(self, attrn)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name + "@" + str(self.location)

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

    def enter(self, it, branch=None, tick=None):
        """Check if I can go into the destination, and if so, do it
immediately. Else raise exception as appropriate."""
        self.assert_can_enter(it)
        it.assert_can_contain(self)
        w = self.db.get_world_state(branch, tick)
        w.move_thing(self._dimension, self.name, it)

    def move_thru_portal(self, amount, branch=None, tick=None):
        """Move this amount through the portal I'm in"""
        if not isinstance(self.location, Portal):
            raise PortalException(
                """The location of {0} is {1},
which is not a portal.""".format(repr(self), repr(self.location)))
        self.location.notify_moving(self, amount)
        w = self.db.get_world_state(branch, tick)
        w.thing_thru_portal(self._dimension, self.name, self.amount)

    def speed_thru(self, port):
        return 1.0/60.0

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
          "branch": "integer not null default 0",
          "from_tick": "integer not null default 0",
          "to_tick": "integer default null",
          "from_place": "text not null",
          "to_place": "text not null"},
         ("dimension", "thing", "idx", "branch", "from_tick"),
         {"dimension, thing": ("thing", "dimension, name"),
          "dimension, from_place, to_place":
          ("portal", "dimension, from_place, to_place")},
         [])]

    def __init__(self, db, dimension, thing, steps):
        self.db = db
        self._dimension = str(dimension)
        self._thing = str(thing)
        self.steps = []
        self.extend(steps)
        self.scheduled = {}
        if self._dimension not in db.journeydict:
            db.journeydict[self._dimension] = {}
        db.journeydict[self._dimension][self._thing] = self

    def __getattr__(self, attrn):
        if attrn == 'dimension':
            return self.db.get_dimension(self._dimension)
        elif attrn == 'thing':
            return self.db.thingdict[self._dimension][self._thing]
        elif attrn == 'graph':
            return self.dimension.graph
        else:
            raise AttributeError('Journey has no such attribute')

    def __getitem__(self, i):
        (origi, desti) = self.steps[i]
        if isinstance(origi, int):
            orign = self.graph.vs[origi]["name"]
        else:
            orign = origi
        if isinstance(desti, int):
            destn = self.graph.vs[desti]["name"]
        else:
            destn = desti
        return self.db.portalorigdestdict[self._dimension][orign][destn]

    def __setitem__(self, idx, port):
        """Put given portal into the step list at given index, padding steplist
with None as needed."""
        try:
            origi = self.place2idx(port[0])
            desti = self.place2idx(port[1])
        except:
            origi = self.place2idx(port.orig)
            desti = self.place2idx(port.dest)
        orign = self.db.placeidxdict[self._dimension][origi]
        destn = self.db.placeidxdict[self._dimension][desti]
        if (
                origi == desti or
                orign not in
                self.db.portalorigdestdict[self._dimension] or
                destn not in
                self.db.portaldestorigdict[self._dimension]):
            return
        while idx >= len(self.steps):
            self.steps.append(None)
        self.steps[idx] = (origi, desti)

    def __len__(self):
        """Get the number of steps in the Journey.

        Returns the number of Portals the traveller ever passed
        through or ever will on this Journey.

        """
        return len(self.steps)

    def place2idx(self, pl):
        return place2idx(self.db, self._dimension, pl)

    def unravel(self):
        pass

    def append(self, st):
        logger.debug("appending %s to %s's journey",
                     str(st), str(self.thing))
        try:
            begin = self.place2idx(st[0])
            end = self.place2idx(st[1])
        except TypeError:
            begin = self.place2idx(st.orig)
            end = self.place2idx(st.dest)
        begin_s = str(self.db.placeidxdict[self._dimension][begin])
        end_s = str(self.db.placeidxdict[self._dimension][end])
        if (
                begin_s not in
                self.db.portalorigdestdict[self._dimension] or
                end_s not in
                self.db.portalorigdestdict[self._dimension][begin_s]):
            raise PortalException("There is no portal from %d to %d",
                              begin, end)
        elif begin == end:
            raise PortalException(
                "Portals can't lead to the place they are from.")
        else:
            self.steps.append((begin, end))

    def extend(self, it):
        for step in it:
            self.append(step)

    def add_path(self, path):
        logger.debug("adding path to %s's journey", str(self.thing))
        i = len(self.steps)
        age = self.db.age
        try:
            prev = self.steps[-1][1]
        except IndexError:
            prev = path.pop()
        while path != []:
            place = path.pop()
            if place == prev:
                continue
            placen = str(self.db.placeidxdict[self._dimension][place])
            prevn = str(self.db.placeidxdict[self._dimension][prev])
            if (
                    prevn not in
                    self.db.portalorigdestdict[self._dimension] or
                    placen not in
                    self.db.portalorigdestdict[self._dimension][prevn]):
                raise PortalException("No portal between {0} and {1}".format(
                    prevn, placen))
            else:
                self.steps.append((prev, place))
                prev = place
        while i < len(self.steps):
            ev = self.schedule_step(i, age)
            age += len(ev) + 1
            i += 1

    def get_tabdict(self):
        i = 0
        iod = []
        for step in self.steps:
            iod.append({
                "dimension": self._dimension,
                "thing": self._thing,
                "idx": i,
                "from_place": step[0],
                "to_place": step[1]})
            i += 1
        return {
            "journey_step": iod}

    def portal_at(self, i):
        """Return the portal represented by the given step."""
        (origi, desti) = self.steps[i]
        if isinstance(origi, int):
            orign = str(self.db.placeidxdict[self._dimension][origi])
        else:
            orign = origi
        if isinstance(desti, int):
            destn = str(self.db.placeidxdict[self._dimension][desti])
        else:
            destn = desti

        return self.db.portalorigdestdict[self._dimension][orign][destn]

    def steps_left(self):
        """Get the number of steps remaining until the end of the Journey.

        Returns the number of Portals left to be travelled through,
        including the one the traveller is in right now.

        """
        return len(self.steps)

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
            raise ImpossibleEvent(
                "Tried to move {0} past the natural end "
                "of its journey".format(self.thing.name))
        else:
            (o, d) = self.steps[0]
            orig = str(self.db.placeidxdict[self._dimension][o])
            dest = str(self.db.placeidxdict[self._dimension][d])
            port = self.db.portalorigdestdict[self._dimension][orig][dest]
            self.thing.enter(port)
            self.thing.move_thru_portal(prop)
            return True

    def step(self):
        """Teleport the thing to the destination of the portal it's in, and
advance to the next step of the journey.

Return a pair containing the place passed through and the portal it's
now in. If the place is the destination of the journey, the new portal
will be None.

        """
        oldport = self.thing.location
        newplace = self.thing.location.dest
        self.thing.portal_progress = 0.0
        self.thing.enter(newplace)
        del self.steps[0]
        return (oldport, newplace)

    def schedule_step(self, i, branch=None, tick=None):
        """Add an event representing the step at the given index to the
thing's schedule, starting at the given tick."""
        if branch is None:
            branch = self.db.branch
        if tick is None:
            tick = self.db.tick
        logger.debug("scheduling step %d in %s's journey, "
                     "with start in branch %d at tick %d",
                     i, str(self.thing), branch, tick)
        port = self.portal_at(i)
        ev = PortalTravelEvent(self.db, self.thing, port, False)
        ev.tick_from = tick
        length = int(1/self.thing.speed_thru(port))
        ev.tick_to = tick_from + length
        self.scheduled[i] = ev
        logger.debug("...and end at tick %d", ev.tick_to)
        self.db.remember_scheduled_event(ev)
        return ev

    def schedule(self, delay=0):
        """Schedule all events in the journey, if they haven't been scheduled
yet.

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

    def append_portal_by_name(self, name):
        port = self.db.itemdict[self._dimension][name]
        self.steps.append((str(port.orig), str(port.dest)))

    def append_place_by_name(self, name):
        lastplace = self.steps[-1][1]
        self.steps.append((lastplace, name))

    def append_place_by_index(self, i):
        lastplace = self.steps[-1][1]
        self.steps.append((lastplace, i))


journey_qvals = ["journey_step." + valn for valn in Journey.valns]

SCHEDULE_DIMENSION_QRYFMT = (
    "SELECT {0} FROM scheduled_event WHERE dimension "
    "IN ({1})".format(", ".join(Schedule.colns), "{0}"))


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
            r[dimn][itn] = Schedule(db, dimn, itn)
        events.add(rowdict["event"])
    read_events(db, events)
    return r

schedule_qvals = (
    ["scheduled_event.item"] +
    ["scheduled_event." + valn for valn in Schedule.valns])


def lookup_loc(db, it):
    """Return the item that the given one is inside, possibly None."""
    dimname = str(it.dimension)
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
        stepl[rowdict["idx"]] = (f, t)
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
