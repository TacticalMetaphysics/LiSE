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

    def setup(self):
        db = self.db
        rowdict = self.tabdict["journey"]
        self.dimension = db.dimensiondict[rowdict["dimension"]]
        self.thing = db.thingdict[rowdict["dimension"]][rowdict["thing"]]
        self.curstep = rowdict["curstep"]
        self.progress = rowdict["progress"]
        self.steplist = self.tabdict["journeystep"]
        db.journeydict[self.dimension.name][self.thing.name] = self

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

    def setup(self):
        from_place = self.tabdict["portal"]["from_place"]
        to_place = self.tabdict["portal"]["to_place"]
        pd = self.db.placedict
        self.orig = pd[self.dimension.name][from_place]
        self.dest = pd[self.dimension.name][to_place]
        self.db.portaldict[self.dimension.name][self.name] = self
        podd = self.db.portalorigdestdict[self.dimension.name]
        pdod = self.db.portaldestorigdict[self.dimension.name]
        podd[self.orig.name] = self.dest
        pdod[self.dest.name] = self.orig

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
         "arg": "text",
         "dict_hint": "text"}}
    primarykeys = {
        "effect": ("name", "func", "arg")}

    def build(self):
        rowdict = self.tabdict["effect"]
        db = self.db
        funcn = rowdict["func"]
        if funcn in db.func:
            self.func = db.func[funcn]
        else:
            # I should really load all the funcs before I instantiate
            # any Effects, but I feel I should include this here
            # anyway in case it refers to things that've been created
            # and not yet saved
            dl = list(rowdict["dict_hint"].split("."))
            dl.reverse()
            ptr = None
            while dl != []:
                ptr = getattr(db, dl.pop())
            self.func = ptr
            db.func[funcn] = ptr
        self.arg = rowdict["arg"]
        self.name = rowdict["name"]
        db.effectdict[self.name] = self

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

    def pull(self, db, tabdict):
        qryfmt = (
            "SELECT {0} FROM effect_deck_link WHERE "
            "deck IN ({1})")
        cols = self.colnames["effect_deck_link"]
        decknames = [rowdict["name"] for rowdict in tabdict["effect_deck"]]
        qms = ["?"] * len(decknames)
        qrystr = qryfmt.format(", ".join(cols), ", ".join(qms))
        db.c.execute(qrystr, decknames)
        tabdict["effect_deck_link"] = [
            dictify_row(self.colnames["effect_deck_link"], row)
            for row in db.c]

        qryfmt = (
            "SELECT {0} FROM effect WHERE effect.name IN ({1})")
        cols = Effect.cols
        effnames = [rowdict["effect"]
                    for rowdict in tabdict["effect_deck_link"]]
        qms = ["?"] * len(effnames)
        qrystr = qryfmt.format(", ".join(effnames), ", ".join(qms))
        db.c.execute(qrystr, effnames)
        tabdict["effect"] = [
            dictify_row(Effect.cols, row) for row in db.c]
        return Effect.pull(db, tabdict)


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
         "type": "text",
         "start": "integer",
         "length": "integer",
         "ongoing": "boolean",
         "commence_test": "text",
         "abort_effects": "text",
         "proceed_test": "text",
         "interrupt_effects": "text",
         "conclude_test": "text",
         "end_effects": "text"}}
    primarykeys = {
        "event": ("name",)}
    foreignkeys = {
        "event":
        {"commence_tests": ("effect_deck", "name"),
         "abort_effects": ("effect_deck", "name"),
         "proceed_tests": ("effect_deck", "name"),
         "interrupt_effects": ("effect_deck", "name"),
         "conclude_tests": ("effect_deck", "name"),
         "complete_effects": ("effect_deck", "name")}}

    def build(self):
        rowdict = self.tabdict["event"]
        self.name = rowdict["name"]
        self.typ = rowdict["type"]
        self.db.eventdict[self.name] = self
        self.start = rowdict["start"]
        self.length = rowdict["length"]
        self.ongoing = rowdict["ongoing"]
        for deckatt in self.foreignkeys["event"].iterkeys():
            deck = self.db.effectdeckdict[rowdict[deckatt]]
            setattr(self, deckatt, deck)

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


class EventDeck:
    maintab = "event_deck"
    coldecls = {
        "event_deck":
        {"name": "text",
         "type": "text"},
        "event_deck_link":
        {"event": "text",
         "deck": "text"}}
    primarykeys = {
        "event_deck": ("name",),
        "event_deck_link": ("event", "deck")}
    foreignkeys = {
        "event_deck_link":
        {"event": ("event", "name"),
         "deck": ("event_deck", "name")}}

    def pull(self, db, tabdict):
        eventnames = [rowdict["name"] for rowdict in tabdict["event_deck"]]
        qryfmt = "SELECT {0} FROM event_deck_link WHERE name IN ({1})"
        qrystr = qryfmt.format(", ".join(self.colnames["event_deck_link"]),
                               ", ".join(["?"] * len(eventnames)))
        db.c.execute(qrystr, eventnames)
        tabdict["event_deck_link"] = [
            dictify_row(self.colnames["event_deck_link"], row)
            for row in db.c]
        return tabdict

    def build(self):
        self.events = [self.db.eventdict[rowdict["event"]]
                       for rowdict in self.tabdict["event_deck_link"]]


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

    def pull_dimensions(self, db, dims):
        dim_qm = ["?"] * len(dims)
        dim_qm_s = ", ".join(dim_qm)
        tabdict = {}

        qryfmt = "SELECT {0} FROM schedule WHERE dimension IN ({1})"
        qrystr = qryfmt.format(self.colnamestr["schedule"], dim_qm_s)
        db.c.execute(qrystr, dims)
        tabdict["schedule"] = [
            dictify_row(self.cols, row) for row in db.c]

        qryfmt = "SELECT {0} FROM scheduled_event WHERE dimension IN ({1})"
        qrystr = qryfmt.format(self.colnamestr["scheduled_event"], dim_qm_s)
        db.c.execute(qrystr, dims)
        tabdict["scheduled_event"] = [
            dictify_row(self.colnames["scheduled_event"], row)
            for row in db.c]

        qryfmt = "SELECT {0} FROM event WHERE name IN ({1})"
        evnames = [rowdict["event"] for rowdict in tabdict["scheduled_event"]]
        evqm = ["?"] * len(evnames)
        evqm_s = ", ".join(evqm)
        qrystr = qryfmt.format(Event.colnamestr["event"], evqm_s)
        db.c.execute(qrystr, evnames)
        tabdict["event"] = [dictify_row(Event.cols, row) for row in db.c]

        return Event.pull(db, tabdict)

    def pull(self, db, tabdict):
        qryfmt = (
            "SELECT {0} FROM scheduled_event WHERE (dimension, item) IN ({1})")
        di = []
        qm = []
        for rowdict in tabdict["schedule"]:
            di.extend([rowdict["dimension"], rowdict["item"]])
            qm.append("(?, ?)")
        qrystr = qryfmt.format(", ".join(self.colnames["scheduled_event"]),
                               ", ".join(qm))
        db.c.execute(qrystr, di)
        tabdict["scheduled_event"] = [
            dictify_row(self.colnames["scheduled_event"], row)
            for row in db.c]
        return tabdict

    def setup(self):
        td = self.tabdict
        db = self.db
        self.name = td["schedule"]["name"]
        self.age = td["schedule"]["age"]
        self.startevs = {}
        self.endevs = {}
        todo = []
        sevlist = td["scheduled_event"]
        while sevlist != []:
            sevrow = sevlist.pop()
            sevname = sevrow["event"]
            start = sevrow["start"]
            length = sevrow["length"]
            ev = db.eventdict[sevname].scheduled_copy(start, length)
            todo.append(ev)
        todo.sort(reverse=True)
        while todo != []:
            doing = todo.pop()
            if doing.start not in self.startevs:
                self.startevs = set()
            if doing.end not in self.endevs:
                self.endevs = set()
            self.startevs[doing.start].add(doing)
            self.endevs[doing.end].add(doing)

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

    def setup(self):
        rowdict = self.tabdict["dimension"][0]
        db = self.db
        self.name = rowdict["name"]
        self.placedict = self.db.placedict[self.name]
        self.portaldict = self.db.portaldict[self.name]
        self.thingdict = self.db.thingdict[self.name]
        self.journeydict = self.db.journeydict[self.name]
        db.dimensiondict[self.name] = self

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
    coldecls = {"place":
                {"dimension": "text",
                 "name": "text"}}
    primarykeys = {"place": ("dimension", "name")}

    def pull_dimension(self, db, dimname):
        qryfmt = "SELECT {0} FROM place WHERE dimension=?"
        qrystr = qryfmt.format(self.colnamestr["place"], dimname)
        db.c.execute(qrystr, (dimname,))
        tabdict = {}
        tabdict["place"] = [
            dictify_row(self.cols, row)
            for row in db.c]

    def pull_dimensions(self, db, dims):
        qryfmt = "SELECT {0} FROM place WHERE dimension IN ({0})"
        dimqm = ["?"] * len(dims)
        qrystr = qryfmt.format(self.colnamestr["place"], ", ".join(dimqm))
        db.c.execute(qrystr, dims)
        tabdict = {}
        tabdict["place"] = [
            dictify_row(self.cols, row) for row in db.c]
        return tabdict

    def setup(self):
        Item.setup(self)
        rowdict = self.tabdict["place"][0]
        db = self.db
        dimname = rowdict["dimension"]
        self.name = rowdict["name"]
        self.dimension = db.dimensiondict[dimname]
        pcd = self.db.placecontentsdict
        podd = self.db.portalorigdestdict
        self.contents = pcd[dimname][self.name]
        self.portals = podd[dimname][self.name]
        self.db.placedict[dimname][self.name] = self

    def __eq__(self, other):
        if not isinstance(other, Place):
            return False
        else:
            # The name is the key in the database. Must be unique.
            return self.name == other.name


class Thing(Item):
    coldecls = {"thing":
                {"dimension": "text",
                 "name": "text",
                 "location": "text"},
                "containment":
                {"dimension": "text",
                 "contained": "text",
                 "container": "text"},
                "thing_kind":
                {"name": "text"},
                "thing_kind_link":
                {"dimension": "text",
                 "thing": "text",
                 "kind": "text"}}
    primarykeys = {"thing": ("dimension", "name"),
                   "location": ("dimension", "thing"),
                   "containment": ("dimension", "contained"),
                   "thing_kind": ("name",),
                   "thing_kind_link": ("thing", "kind")}
    foreignkeys = {"thing":
                   {"dimension": ("dimension", "name")},
                   "containment":
                   {"dimension": ("dimension", "name"),
                    "dimension, contained": ("thing", "dimension, name"),
                    "dimension, container": ("thing", "dimension, name")},
                   "thing_kind_link":
                   {"dimension": ("dimension", "name"),
                    "thing": ("thing", "name"),
                    "kind": ("thing_kind", "name")}}
    checks = {"containment": ["contained<>container"]}

    def pull_dimensions(self, db, dims):
        qryfmt = "SELECT {0} FROM thing WHERE dimension IN ({1})"
        tabdict = {}
        dims_qm = ["?"] * len(dims)
        dims_qm_str = ", ".join(dims_qm)
        qrystr = qryfmt.join(self.colnamestr["thing"], dims_qm_str)
        db.c.execute(qrystr, dims)
        tabdict["thing"] = [
            dictify_row(self.cols, row) for row in db.c]

        qryfmt = (
            "SELECT {0} FROM containment WHERE dimension IN ({1})")
        qrystr = qryfmt.format(self.colnamestr["containment"], dims_qm_str)
        db.c.execute(qrystr, dims)
        tabdict["containment"] = [
            dictify_row(self.colnames["containment"], row)
            for row in db.c]

        qryfmt = (
            "SELECT {0} FROM thing_kind_link WHERE dimension IN ({1})")
        qrystr = qryfmt.format(self.colnamestr["thing_kind_link"], dims_qm_str)
        db.c.execute(qrystr, dims)
        tabdict["thing_kind_link"] = [
            dictify_row(self.colnames["thing_kind_link"], row)
            for row in db.c]

        return tabdict

    def pull_dimension(self, db, dimname):
        qryfmt = "SELECT {0} FROM thing WHERE dimension=?"
        qrystr = qryfmt.format(self.colnamestr["thing"], dimname)
        db.c.execute(qrystr, (dimname,))
        tabdict = {}
        tabdict["thing"] = [
            dictify_row(self.cols, row)
            for row in db.c]

        qryfmt = (
            "SELECT {0} FROM containment WHERE dimension=?")
        qrystr = qryfmt.format(self.colnamestr["containment"], dimname)
        db.c.execute(qrystr, (dimname,))
        tabdict["containment"] = [
            dictify_row(self.colnames["containment"], row)
            for row in db.c]

        qryfmt = (
            "SELECT {0} FROM thing_kind_link WHERE dimension=?")
        qrystr = qryfmt.format(self.colnamestr["thing_kind_link"], dimname)
        db.c.execute(qrystr, (dimname,))
        tabdict["thing_kind_link"] = [
            dictify_row(self.colnames["thing_kind_link"], row)
            for row in db.c]

        return tabdict

    def pull(self, db, tabdict):
        qryfmt = (
            "SELECT {0} FROM containment WHERE "
            "(dimension, contained) IN ({1})")
        dn = []
        qm = []
        for rowdict in tabdict["thing"]:
            dn.extend([rowdict["dimension"], rowdict["name"]])
            qm.append("(?, ?)")
        qmstr = ", ".join(qm)
        qrystr = qryfmt.format(self.rowqms["containment"], qmstr)
        db.c.execute(qrystr, dn)
        tabdict["containment"] = [
            dictify_row(self.colnames["containment"], row)
            for row in db.c]

        qryfmt = (
            "SELECT {0} FROM thing_kind_link WHERE "
            "(dimension, thing) IN ({1})")
        qrystr = qryfmt.format(self.rowqms["thing_kind_link"], qmstr)
        db.c.execute(qrystr, dn)
        tabdict["thing_kind_link"] = [
            dictify_row(self.colnames["thing_kind_link"], row)
            for row in db.c]

        return tabdict

    def setup(self):
        Item.setup(self)
        rowdict = self.tabdict["thing"][0]
        locname = rowdict["location"]
        dimname = self.dimension.name
        db = self.db
        self.location = db.placedict[dimname][locname]
        db.thingdict[dimname][self.name] = self
        if self.name in db.contentsdict[dimname]:
            self.contents = db.contentsdict[dimname][self.name]
            for contained in self.contents:
                db.containerdict[dimname][contained.name] = self
        else:
            self.contents = []
            db.contentsdict[dimname][self.name] = self.contents
        if self.name in db.containerdict[dimname]:
            self.container = db.containerdict[dimname]
        else:
            self.container = None

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
