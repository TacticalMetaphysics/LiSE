import igraph
from util import (SaveableMetaclass, LocationException,
                  ContainmentException, Item, dictify_row)


__metaclass__ = SaveableMetaclass


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
    maintab = "journey"
    coldecls = {"journey":
                {"dimension": "text",
                 "thing": "text",
                 "curstep": "integer",
                 "progress": "float"},
                "journey_step":
                {"dimension": "text",
                 "thing": "text",
                 "idx": "integer",
                 "portal": "text"}}
    primarykeys = {"journey": ("dimension", "thing"),
                   "journey_step": ("dimension", "thing", "idx")}
    fkeydict = {"journey":
                {"dimension, thing": ("thing", "dimension, name")},
                "journey_step":
                {"dimension, thing": ("thing", "dimension, name"),
                 "dimension, portal": ("portal", "dimension, name")}}
    checks = {"journey": ["progress>=0.0", "progress<1.0"]}

    def __init__(self, dimension, thing, curstep, progress, steps, db=None):
        self.dimension = dimension
        self.thing = thing
        self.curstep = curstep
        self.progress = progress
        self.steps = steps
        if db is not None:
            if dimension not in db.journeydict:
                db.journeydict[dimension] = {}
            db.journeydict[dimension][thing] = self

    def unravel(self, db):
        self.dimension = db.dimensiondict[self.dimension]
        self.thing = db.thingdict[self.dimension.name][self.thing]
        for step in self.steps:
            step = db.portaldict[self.dimension.name][step]

    def pull_dimension(self, db, dimname):
        # Now just returns a lot of rowdicts. Each is sufficient to
        # make a journey and its journeystep.
        qryfmt = (
            "SELECT {0} FROM journey, journey_step WHERE "
            "journey.dimension=journey_step.dimension AND "
            "journey.thing=journey_step.thing AND "
            "journey.dimension=?")
        jocols = ["journey." + col for col in self.colnames["journey"]]
        scols = ["journey_step." + col
                 for col in self.valnames["journey_step"]]
        allcolstr = ", ".join(jocols + scols)
        allcols = (
            self.colnames["journey"] + self.valnames["journey_step"])
        qrystr = qryfmt.format(allcolstr)
        db.c.execute(qrystr, (dimname,))
        return [
            dictify_row(allcols, row) for row in db.c]

    def parse(self, rows):
        journeydict = {}
        for row in rows:
            if row["dimension"] not in journeydict:
                journeydict[row["dimension"]] = {}
            if row["thing"] not in journeydict[row["dimension"]]:
                journeydict[row["dimension"]][row["thing"]] = {
                    "steps": [],
                    "curstep": row["curstep"],
                    "progress": row["progress"]}
            journeyptr = journeydict[row["dimension"]][row["thing"]]
            while len(journeyptr["steps"]) < row["idx"]:
                journeyptr["steps"].append(None)
            journeyptr["steps"][row["idx"]] = row["portal"]
        return {"journey": journeydict}

    def pull_parse_dimension(self, db, dimname):
        return self.parse(self.pull_dimension(db, dimname))

    def steps(self):
        """Get the number of steps in the Journey.

        steps() => int

        Returns the number of Portals the traveller ever passed
        through or ever will on this Journey.

        """
        return len(self.steplist)

    def stepsleft(self):
        """Get the number of steps remaining until the end of the Journey.

        stepsleft() => int

        Returns the number of Portals left to be travelled through,
        including the one the traveller is in right now.

        """
        return len(self.steplist) - self.curstep

    def getstep(self, i):
        """Get the ith next Portal in the journey.

        getstep(i) => Portal

        getstep(0) returns the portal the traveller is presently
        travelling through. getstep(1) returns the one it wil travel
        through after that, etc. getstep(-1) returns the step before
        this one, getstep(-2) the one before that, etc.

        If i is out of range, returns None.

        """
        return self.steplist[i+self.curstep]

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
        self.progress += prop
        while self.progress >= 1.0:
            self.curstep += 1
            self.progress -= 1.0
        while self.progress < 0.0:
            self.curstep -= 1
            self.progress += 1.0
        if self.curstep > len(self.steplist):
            return None
        else:
            return self.getstep(0)

    def set_step(self, idx, port):
        while idx >= len(self.steplist):
            self.steplist.append(None)
        self.steplist[idx] = port

    def gen_event(self, step):
        """Make an Event representing every tick of travel through the given
portal.

        The Event will have a length, but no start. Make sure to give
        it one.

        """
        # Work out how many ticks this is going to take.  Of course,
        # just because a thing is scheduled to travel doesn't mean it
        # always will--which makes it convenient to have
        # events to resolve all the steps, ne?
        db = self.db
        speed = self.thing.speed_thru(step)
        ticks = 1.0 / speed
        start_test_arg = step.name
        start_test_s = "%s.%s.can_enter(%s)" % (
            self.dimension.name, self.thing.name, start_test_arg)
        effd = {
            "name": start_test_s,
            "func": "%s.%s.can_enter" % (self.dimension.name, self.thing.name),
            "arg": start_test_arg,
            "dict_hint": "dimension.thing"}
        tabd = {"effect": effd}
        # db.effectdict is going to contain all these Effects
        Effect(db, tabd)
        commence_arg = step.name
        commence_s = "%s.%s.enter(%s)" % (
            self.dimension.name, self.thing.name, commence_arg)
        effd = {
            "name": commence_s,
            "func": "%s.%s.enter" % (self.dimension.name, self.thing.name),
            "arg": commence_arg,
            "dict_hint": "dimension.thing"}
        tabd = {"effect": effd}
        Effect(db, tabd)
        proceed_arg = step.name
        proceed_s = "%s.%s.remain(%s)" % (
            self.dimension.name, self.thing.name, proceed_arg)
        effd = {
            "name": proceed_s,
            "func": "%s.%s.remain" % (self.dimension.name, self.thing.name),
            "arg": proceed_arg,
            "dict_hint": "dimension.thing"}
        tabd = {"effect": effd}
        Effect(db, tabd)
        conclude_arg = step.dest.name
        conclude_s = "%s.%s.enter(%s)" % (
            self.dimension.name, self.thing.name, conclude_arg)
        effd = {
            "name": conclude_s,
            "func": "%s.%s.enter" % (self.dimension.name, self.thing.name),
            "arg": conclude_arg,
            "dict_hint": "dimension.thing"}
        tabd = {"effect": effd}
        Effect(db, tabd)
        event_name = "%s:%s-thru-%s" % (
            self.dimension.name, self.thing.name, step.name),
        event_d = {
            "name": event_name,
            "type": "travel",
            "start": None,
            "length": ticks,
            "ongoing": False}
        start_test_d = {
            "event": event_name,
            "effect": start_test_s}
        commence_d = {
            "event": event_name,
            "effect": commence_s}
        proceed_d = {
            "event": event_name,
            "effect": proceed_s}
        conclude_d = {
            "event": event_name,
            "effect": conclude_s}
        tabd = {
            "event": event_d,
            "event_start_test_effect_link": [start_test_d],
            "event_commence_effect_link": [commence_d],
            "event_proceed_effect_link": [proceed_d],
            "event_conclude_effect_link": [conclude_d]}
        event = Event(db, tabd)
        self.db.eventdict[event_name] = event
        return event

    def schedule(self, start=0):
        """Make a Schedule filled with Events representing the steps in this
Journey.

        Optional argument start indicates the start time of the schedule.

        """
        stepevents = []
        for step in self.steplist:
            ev = self.gen_event(step)
            ev.start = start
            start += ev.length
        tabdict = {
            "schedule": {
                "name": self.__name__ + ".schedule",
                "age": 0},
            "scheduled_event": stepevents}
        s = Schedule(tabdict)
        return s


class Portal(Item):
    # Portals would be called 'exits' if that didn't make it
    # perilously easy to exit the program by mistake. They link
    # one place to another. They are one-way; if you want two-way
    # travel, make another one in the other direction. Each portal
    # has a 'weight' that probably represents how far you have to
    # go to get to the other side; this can be zero. Portals are
    # likely to impose restrictions on what can go through them
    # and when. They might require some ritual to be performed
    # prior to becoming passable, e.g. opening a door before
    # walking through it. They might be diegetic, in which case
    # they point to a Thing that the player can interact with, but
    # the portal itself is not a Thing and does not require one.
    #
    # These are implemented as methods, although they
    # will quite often be constant values, because it's not much
    # more work and I expect that it'd cause headaches to be
    # unable to tell whether I'm dealing with a number or not.
    maintab = "portal"
    coldecls = {"portal":
                {"dimension": "text",
                 "name": "text",
                 "from_place": "text",
                 "to_place": "text"}}
    primarykeys = {"portal": ("dimension", "name")}
    foreignkeys = {"portal":
                   {"dimension, name": ("item", "dimension, name"),
                    "dimension, from_place": ("place", "dimension, name"),
                    "dimension, to_place": ("place", "dimension, name")}}

    def __init__(self, dimension, name, from_place, to_place, db=None):
        self.dimension = dimension
        self.name = name
        self.orig = from_place
        self.dest = to_place
        if db is not None:
            pd = db.portaldict
            podd = db.portalorigdestdict
            pdod = db.portaldestorigdict
            for d in [pd, podd, pdod]:
                if dimension not in d:
                    d[dimension] = {}
            if from_place not in podd:
                podd[from_place] = {}
            if to_place not in pdod:
                pdod[to_place] = {}
            pd[dimension][name] = self
            podd[dimension][from_place][to_place] = self
            pdod[dimension][to_place][from_place] = self

    def unravel(self, db):
        self.dimension = db.dimensiondict[self.dimension]
        self.orig = db.placedict[self.dimension.name][self.orig]
        self.dest = db.placedict[self.dimension.name][self.dest]

    def pull_dimension(self, db, dimname):
        qryfmt = "SELECT {0} FROM portal WHERE dimension=?"
        qrystr = qryfmt.format(self.colnamestr["portal"])
        db.c.execute(qrystr, (dimname,))
        return [
            dictify_row(self.cols, row) for row in db.c]

    def parse(self, rows):
        return {"portal": rows}

    def pull_parse_dimension(self, db, dimname):
        return self.parse(self.pull_dimension(db, dimname))

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


class Effect:
    """Curry a function name and a string argument.

    This is actually still good for function calls that don't have any
    effect. It's named this way because it's linked from the event
    table, which does in fact use these to describe effects.

    """
    maintab = "effect"
    coldict = {
        "effect":
        {"name": "text",
         "func": "text",
         "arg": "text"}}
    primarykeys = {
        "effect": ("name", "func", "arg")}

    def __init__(self, name, func, arg, db=None):
        self.name = name
        self.func = func
        self.arg = arg
        if db is not None:
            db.effectdict[name] = self

    def unravel(self, db):
        self.func = db.func[self.func]

    def parse(self, row):
        return {"effect": row}

    def do(self):
        return self.func(self.arg)


class EffectDeck:
    maintab = "effect_deck"
    coldict = {
        "effect_deck":
        {"name": "text"},
        "effect_deck_link":
        {"deck": "text",
         "effect": "text"}}
    primarykeys = {
        "effect_deck": ("name",),
        "effect_deck_link": ("deck", "effect")}
    foreignkeys = {
        "effect_deck_link":
        {"deck": ("effect_deck", "name"),
         "effect": ("effect", "name")}}

    def __init__(self, name, effects, db=None):
        self.name = name
        self.effects = effects
        if db is not None:
            db.effectdeckdict[name] = self

    def unravel(self, db):
        for effect in self.effects:
            effect = db.effectdict[effect]


class Event:
    """A class for things that can happen. Normally represented as
cards.

Events are kept in EventDecks, which are in turn contained by
Characters. When something happens involving one or more characters,
the relevant EventDecks from the participating Characters will be put
together into an AttemptDeck. One card will be drawn from this, called
the attempt card. It will identify what kind of EventDeck should be
taken from the participants and compiled in the same manner into an
OutcomeDeck. From this, the outcome card will be drawn.

The effects of an event are determined by both the attempt card and
the outcome card. An attempt card might specify that only favorable
outcomes should be put into the OutcomeDeck; the attempt card might
therefore count itself for a success card. But further, success cards
may have their own effects irrespective of what particular successful
outcome occurs. This may be used, for instance, to model that kind of
success that strains a person terribly and causes them injury.

    """
    maintab = "event"
    coldecls = {
        "event":
        {"name": "text",
         "ongoing": "boolean",
         "commence_tests": "text",
         "proceed_tests": "text",
         "conclude_tests": "text"}}
    primarykeys = {
        "event": ("name",)}
    foreignkeys = {
        "event":
        {"commence_tests": ("effect_deck", "name"),
         "proceed_tests": ("effect_deck", "name"),
         "conclude_tests": ("effect_deck", "name")}}

    def __init__(self, name, ongoing, commence_tests,
                 proceed_tests, conclude_tests, db=None):
        self.name = name
        self.ongoing = ongoing
        self.commence_tests = commence_tests
        self.proceed_tests = proceed_tests
        self.conclude_tests = conclude_tests
        if db is not None:
            db.eventdict[name] = self

    def unravel(self, db):
        for deck in [self.commence_tests, self.proceed_tests,
                     self.conclude_tests]:
            for effect in deck:
                effect = db.effectdict[effect]

    def parse(self, row):
        return {"event": row}

    def cmpcheck(self, other):
        if not hasattr(self, 'start') or not hasattr(other, 'start'):
            raise Exception("Events are only comparable when they have "
                            "start times.")
        elif not isinstance(other, Event):
            raise TypeError("Events may only be compared to other Events.")

    def __eq__(self, other):
        self.cmpcheck(other)
        return self.start == other.start

    def __gt__(self, other):
        self.cmpcheck(other)
        return self.start > other.start

    def __lt__(self, other):
        self.cmpcheck(other)
        return self.start < other.start

    def __ge__(self, other):
        self.cmpcheck(other)
        return self.start >= other.start

    def __le__(self, other):
        self.cmpcheck(other)
        return self.start <= other.start

    def scheduled_copy(self, start, length):
        # Return a copy of myself with the given start & end
        new = Event(self.db, self.tabdict)
        new.start = start
        new.length = length
        new.end = start + length
        return new

    def begun(self):
        r = True
        for starttest in self.starttests:
            if not starttest():
                r = False
        return r

    def commence(self):
        if self.begun():
            self.ongoing = True
        else:
            for effect in self.abort_effects:
                effect[0](effect[1])
        return self.status

    def proceed(self):
        if self.interrupted():
            for effect in self.interrupt_effects:
                effect[0](effect[1])
            self.ongoing = False
        return self.status

    def conclude(self):
        self.ongoing = False
        for effect in self.complete_effects:
            effect[0](effect[1])
        return self.status


class Schedule:
    maintab = "schedule"
    coldecls = {
        "schedule":
        {"dimension": "text",
         "item": "text",
         "age": "integer"},
        "scheduled_event":
        {"dimension": "text",
         "item": "text",
         "event": "text",
         "start": "integer not null",
         "length": "integer not null"}}
    primarykeys = {
        "schedule": ("dimension", "item"),
        "scheduled_event": ("dimension", "item", "event")}
    foreignkeys = {
        "schedule":
        {"dimension, item": ("item", "dimension, name")},
        "scheduled_event":
        {"schedule": ("schedule", "name"),
         "event": ("event", "name")}}

    def __init__(self, dimension, item, age, events, db=None):
        self.dimension = dimension
        self.item = item
        self.age = age
        self.events = events
        if db is not None:
            if dimension not in db.scheduledict:
                db.scheduledict[dimension] = {}
            db.scheduledict[dimension][item] = self

    def unravel(self, db):
        self.dimension = db.dimensiondict[self.dimension]
        self.item = db.itemdict[self.dimension.name][self.item]
        for event in self.events:
            start = event["start"]
            length = event["length"]
            event = db.eventdict[event]
            event.start = start
            event.length = length

    def pull_dimension(self, db, dimname):
        qryfmt = (
            "SELECT {0} FROM "
            "schedule, scheduled_event, event, effect_deck_link, effect "
            "WHERE "
            "schedule.dimension=scheduled_event.dimension AND "
            "schedule.item=scheduled_event.item AND "
            "scheduled_event.event=event.name AND "
            "dimension=?")
        schedcol = ["schedule." + col for col in self.colnames["schedule"]]
        schevcol = [
            "scheduled_event." + col
            for col in self.valnames["scheduled_event"]]
        evcol = ["event." + col for col in Event.valnames["event"]]
        efcol = ["effect." + col for col in Effect.valnames["effect"]]
        allcol = (
            self.colnames["schedule"] +
            self.valnames["scheduled_event"] +
            Event.valnames["event"] +
            Effect.valnames["effect"])
        allcolstr = ", ".join(schedcol + schevcol + evcol + efcol)
        qrystr = qryfmt.format(allcolstr)
        db.c.execute(qrystr, (dimname,))
        return [
            dictify_row(allcol, row) for row in db.c]

    def parse(self, rowdicts):
        tabdict = {}
        for row in rowdicts:
            if row["dimension"] not in tabdict:
                tabdict[row["dimension"]] = {}
            if row["item"] not in tabdict[row["dimension"]]:
                tabdict[row["dimension"]][row["item"]] = {
                    "age": row["age"],
                    "events": []}
            ptr = tabdict[row["dimension"]][row["item"]]
            # TODO write a real event row parser
            ptr["events"].append(Event.parse(row))
        return {"schedule": tabdict}

    def pull_parse_dimension(self, db, dimname):
        return self.parse(self.pull_dimension(db, dimname))

    def __getitem__(self, n):
        return self.startevs[n]

    def advance(self, n):
        # advance time by n ticks
        prior_age = self.age
        new_age = prior_age + n
        starts = [self.startevs[i] for i in xrange(prior_age, new_age)]
        for start in starts:
            start.start()
        ends = [self.endevs[i] for i in xrange(prior_age, new_age)]
        for end in ends:
            end.end()
        self.age = new_age


class Item:
    maintab = "item"
    coldecls = {
        "item":
        {"dimension": "text",
         "name": "text"}}
    primarykeys = {
        "item": ("dimension", "name")}


class Dimension:
    maintab = "dimension"
    coldecls = {"dimension":
                {"name": "text"}}
    primarykeys = {"dimension": ("name",)}

    def __init__(self, name, places, portals, things, journeys, db=None):
        self.name = name
        self.places = places
        self.portals = portals
        self.things = things
        self.journeys = journeys
        if db is not None:
            db.dimensiondict[name] = self

    def pull_parse_named(self, db, dimname):
        tabdict = {"name": dimname}
        for clas in [Place, Thing, Portal, Journey]:
            tabdict.update(clas.pull_parse_dimension(db, dimname))
        return {"dimension": tabdict}

    def from_tabdict(self, db, tabdict):
        tdd = tabdict["dimension"]
        name = tdd["name"]
        db.dimensiondict[self.name] = self
        places = [
            Place(**row) for row in tdd["place"]]
        portals = [
            Portal(**row) for row in tdd["portal"]]
        things = [
            Thing(**row) for row in tdd["thing"]]
        journeys = [
            Journey(**row) for row in tdd["journey"]]
        dim = Dimension(name, places, portals, things, journeys)
        return dim

    def load_named(self, db, name):
        loaded = self.from_tabdict(db, self.pull_parse_named(db, name))
        for l in [loaded.places, loaded.portals,
                  loaded.things, loaded.journeys]:
            for m in l:
                m.unravel(db)
        return loaded

    def get_edge(self, portal):
        origi = self.places.index(portal.orig)
        desti = self.places.index(portal.dest)
        return (origi, desti)

    def get_edges(self):
        return [self.get_edge(port) for port in self.portals]

    def get_edge_atts(self):
        return {}

    def get_vertex_atts(self):
        return {}

    def get_igraph_graph(self):
        return igraph.Graph(edges=self.get_edges(), directed=True,
                            vertex_attrs=self.get_vertex_atts(),
                            edge_attrs=self.get_edge_atts())

    def get_igraph_layout(self, layout_type):
        return self.get_igraph_graph().layout(layout=layout_type)


class Place(Item):
    maintab = "place"
    coldecls = {"place":
                {"dimension": "text",
                 "name": "text"}}
    primarykeys = {"place": ("dimension", "name")}

    def __init__(self, dimension, name, db=None):
        self.dimension = dimension
        self.name = name
        if db is not None:
            if dimension not in db.placedict:
                db.placedict[dimension] = {}
            db.placedict[dimension][name] = self

    def unravel(self, db):
        self.dimension = db.dimensiondict[self.dimension]

    def pull_dimension(self, db, dimname):
        qryfmt = "SELECT {0} FROM place WHERE dimension=?"
        qrystr = qryfmt.format(self.colnamestr["place"])
        db.c.execute(qrystr, (dimname,))
        return [
            dictify_row(self.cols, row) for row in db.c]

    def parse(self, rows):
        return {"place": rows}

    def pull_parse_dimension(self, db, dimname):
        self.parse(self.pull_dimension(db, dimname))

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name


class Thing(Item):
    maintab = "thing"
    coldecls = {
        "thing":
        {"dimension": "text",
         "name": "text",
         "location": "text",
         "container": "text"},
        "thing_kind":
        {"name": "text"},
        "thing_kind_link":
        {"dimension": "text",
         "thing": "text",
         "kind": "text"}}
    primarykeys = {
        "thing": ("dimension", "name"),
        "location": ("dimension", "thing"),
        "thing_kind": ("name",),
        "thing_kind_link": ("thing", "kind")}
    foreignkeys = {
        "thing":
        {"dimension": ("dimension", "name"),
         "dimension, container": ("thing", "dimension, name")},
        "thing_kind_link":
        {"dimension": ("dimension", "name"),
         "thing": ("thing", "name"),
         "kind": ("thing_kind", "name")}}

    def __init__(self, dimension, name, location, container, kinds, db=None):
        self.dimension = dimension
        self.name = name
        self.location = location
        self.container = container
        self.kinds = kinds
        if db is not None:
            if dimension not in db.thingdict:
                db.thingdict[dimension] = {}
            db.thingdict[dimension][name] = self

    def unravel(self, db):
        self.dimension = db.dimensiondict[self.dimension]
        self.location = db.placedict[self.dimension.name][self.location]
        self.container = db.thingdict[self.dimension.name][self.container]
        self.contents = set()
        self.unravelled = True
        if self.container.unravelled:
            self.container.add(self)

    def pull_dimension(self, db, dimname):
        qryfmt = (
            "SELECT {0} FROM thing, thing_kind_link WHERE "
            "thing.dimension=thing_kind_link.dimension AND "
            "thing.name=thing_kind_link.thing AND "
            "dimension=?")
        thingcols = ["thing." + col for col in self.cols]
        tklcols = [
            "thing_kind_link." + col
            for col in self.valnames["thing_kind_link"]]
        allcols = self.cols + self.valnames["thing_kind_link"]
        colstr = ", ".join(thingcols) + ", ".join(tklcols)
        qrystr = qryfmt.format(colstr)
        db.c.execute(qrystr, (dimname,))
        return [
            dictify_row(allcols, row) for row in db.c]

    def parse(self, rows):
        tabdict = {}
        for row in rows:
            if row["dimension"] not in tabdict:
                tabdict[row["dimension"]] = {}
            if row["name"] not in tabdict[row["dimension"]]:
                tabdict[row["dimension"]][row["name"]] = {
                    "dimension": row["dimension"],
                    "name": row["name"],
                    "kinds": []}
            ptr = tabdict[row["dimension"]][row["name"]]
            ptr["kinds"].append(row["kinds"])
        return {"thing": tabdict}

    def pull_parse_dimension(self, db, dimname):
        return self.parse(self.pull_dimension(db, dimname))

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
