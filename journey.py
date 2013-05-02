from event import Event
from effect import Effect
from schedule import Schedule
from util import SaveableMetaclass, dictify_row


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
    tablenames = ["journey", "journey_step"]
    coldecls = {
}
    primarykeys = {
        "journey_step": ("dimension", "thing", "idx")}
    fkeydict = {
        "journey_step":
        {"dimension, thing": ("thing", "dimension, name"),
         "dimension, portal": ("portal", "dimension, name")}}

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
        self.thing = db.itemdict[self.dimension.name][self.thing]
        for step in self.steps:
            step = db.itemdict[self.dimension.name][step]

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

    def gen_event(self, step, db):
        """Make an Event representing every tick of travel through the given
portal.

The Event will not have a start or a length.

        """
        # Work out how many ticks this is going to take.  Of course,
        # just because a thing is scheduled to travel doesn't mean it
        # always will--which makes it convenient to have
        # events to resolve all the steps, ne?
        commence_arg = step.name
        commence_s = "{0}.{1}.enter({2})".format(
            self.dimension.name, self.thing.name, commence_arg)
        effd = {
            "name": commence_s,
            "func": "%s.%s.enter" % (self.dimension.name, self.thing.name),
            "arg": commence_arg,
            "dict_hint": "dimension.thing",
            "db": db}
        commence = Effect(**effd)
        proceed_arg = step.name
        proceed_s = "%s.%s.remain(%s)" % (
            self.dimension.name, self.thing.name, proceed_arg)
        effd = {
            "name": proceed_s,
            "func": "%s.%s.remain" % (self.dimension.name, self.thing.name),
            "arg": proceed_arg,
            "dict_hint": "dimension.thing",
            "db": db}
        proceed = Effect(**effd)
        conclude_arg = step.dest.name
        conclude_s = "%s.%s.enter(%s)" % (
            self.dimension.name, self.thing.name, conclude_arg)
        effd = {
            "name": conclude_s,
            "func": "%s.%s.enter" % (self.dimension.name, self.thing.name),
            "arg": conclude_arg,
            "dict_hint": "dimension.thing",
            "db": db}
        conclude = Effect(**effd)
        event_name = "%s:%s-thru-%s" % (
            self.dimension.name, self.thing.name, step.name),
        event_d = {
            "name": event_name,
            "ongoing": False,
            "commence_effect": commence,
            "proceed_effect": proceed,
            "conclude_effect": conclude,
            "db": db}
        event = Event(**event_d)
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


jocoln = ["journey." + col for col in Journey.colnames["journey"]]
stepvaln = ["journey_step." + val for val in Journey.valnames["journey_step"]]
journey_dimension_qryfmt = (
    "SELECT {0} FROM journey, journey_step WHERE "
    "journey.dimension=journey_step.dimension AND "
    "journey.thing=journey_step.thing AND "
    "journey.dimension IN ({1})".format(
        ", ".join(jocoln + stepvaln), "{0}"))


def pull_in_dimensions(db, dimnames):
    qryfmt = journey_dimension_qryfmt
    qrystr = qryfmt.format(["?"] * len(dimnames))
    allcols = (
        Journey.colnames["journey"] + Journey.valnames["journey_step"])
    db.c.execute(qrystr, dimnames)
    journeydict = {}
    for row in db.c:
        rowdict = dictify_row(row, allcols)
        if rowdict["thing"] not in journeydict:
            journeydict[rowdict["thing"]] = {
                "dimension": rowdict["dimension"],
                "thing": rowdict["thing"],
                "steps": []}
        ptr = journeydict[rowdict["thing"]]["steps"]
        while len(ptr) < rowdict["idx"]:
            ptr.append(None)
        journeydict[rowdict["thing"]][rowdict["idx"]] = {
            "curstep": rowdict["curstep"],
            "progress": rowdict["progress"]}
    return journeydict


def combine(journeydict, stepdict):
    for journey in journeydict.itervalues():
        if "steps" not in journey:
            journey["steps"] = []
        steps = stepdict[journey["dimension"]][journey["thing"]]
        i = 0
        while i < len(steps):
            journey["steps"].append(steps[i])
            i += 1
