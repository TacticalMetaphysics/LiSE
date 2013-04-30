from util import SaveableMetaclass, dictify_row
from event import Event
from effect import Effect


__metaclass__ = SaveableMetaclass


class Schedule:
    tablenames = ["schedule", "scheduled_event"]
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
        {"dimension, item": ("item", "dimension, name"),
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

    def parse(self, rowdicts):
        r = {}
        for row in rowdicts:
            if row["dimension"] not in r:
                r[row["dimension"]] = {}
            r[row["dimension"]][row["item"]] = row
        return r

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


def pull_in_dimension(db, dimname):
    qryfmt = (
        "SELECT {0} FROM schedule, scheduled_event, event, "
        "effect_deck_link, effect "
        "WHERE schedule.dimension=scheduled_event.dimension "
        "AND schedule.item=scheduled_event.item "
        "AND event.name=scheduled_event.event "
        "AND (event.commence_effects=effect_deck_link.deck "
        "OR event.proceed_effects=effect_deck_link.deck "
        "OR event.conclude_effects=effect_deck_link.deck) "
        "AND effect_deck_link.effect=effect.name "
        "AND schedule.dimension=?")
    allcols = (
        Schedule.colnames["schedule"] +
        Schedule.valnames["scheduled_event"] +
        Event.valnames["event"] +
        ["idx"] +
        Effect.valnames["effect"])
    colstrs = (
        ["schedule." + col
         for col in Schedule.colnames["schedule"]] +
        ["scheduled_event." + col
         for col in Schedule.valnames["scheduled_event"]] +
        ["event." + col
         for col in Event.valnames["event"]] +
        ["effect_deck_link.idx"] +
        ["effect." + col
         for col in Effect.valnames["effect"]])
    colstr = ", ".join(colstrs)
    qrystr = qryfmt.format(colstr)
    db.c.execute(qrystr, (dimname,))
    r = {}
    for row in db.c:
        rd = dictify_row(allcols, row)
        if rd["item"] not in r:
            r[rd["item"]] = {
                "age": rd["age"]}
        if rd["event"] not in r[rd["item"]]:
            r[rd["name"]][rd["event"]] = []
        ptr = r[rd["name"]][rd["event"]]
        while len(ptr) < rd["idx"]:
            ptr.append(None)
        ptr[rd["idx"]] = rd
    return r
