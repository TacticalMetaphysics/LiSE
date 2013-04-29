from util import SaveableMetaclass, dictify_row


__metaclass__ = SaveableMetaclass


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
    tablenames = ["event"]
    coldecls = {
        "event":
        {"name": "text",
         "ongoing": "boolean",
         "commence_effects": "text",
         "proceed_effects": "text",
         "conclude_effects": "text"}}
    primarykeys = {
        "event": ("name",)}
    foreignkeys = {
        "event":
        {"commence_effects": ("effect_deck", "name"),
         "proceed_effects": ("effect_deck", "name"),
         "conclude_effects": ("effect_deck", "name")}}

    def pull(self, db, keydicts):
        names = [keydict["name"] for keydict in keydicts]
        return self.pull_named(db, names)

    def pull_named(self, db, names):
        qryfmt = "SELECT {0} FROM event WHERE name IN ({0})"
        qrystr = qryfmt.format(
            self.colnames["event"],
            ", ".join(["?"] * len(names)))
        db.c.execute(qrystr, names)
        return self.parse([
            dictify_row(self.colnames["event"], row)
            for row in db.c])

    def parse(self, rows):
        r = {}
        for row in rows:
            r[row["name"]] = row
        return r

    def combine(self, evdict, efdict):
        for ev in evdict.itervalues():
            ev["commence_effect"] = efdict[ev["commence_effect"]]
            ev["proceed_effect"] = efdict[ev["proceed_effect"]]
            ev["conclude_effect"] = efdict[ev["conclude_effect"]]
        return evdict

    def __init__(self, name, ongoing, commence_effect,
                 proceed_effect, conclude_effect, db=None):
        self.name = name
        self.ongoing = ongoing
        self.commence_effect = commence_effect
        self.proceed_effect = proceed_effect
        self.conclude_effect = conclude_effect
        if db is not None:
            db.eventdict[name] = self

    def unravel(self, db):
        for deck in [self.commence_tests, self.proceed_tests,
                     self.conclude_tests]:
            for effect in deck:
                effect = db.effectdict[effect]

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
    tablenames = ["event_deck", "event_deck_link"]
    coldecls = {
        "event_deck": {
            "name": "text"},
        "event_deck_link": {
            "deck": "text",
            "idx": "integer",
            "event": "text"}}
    primarykeys = {
        "event_deck": ("name",),
        "event_deck_link": ("deck", "idx")}
    foreignkeys = {
        "event_deck_link": {
            "deck": ("event_deck", "name"),
            "event": ("event", "name")}}

    def __init__(self, name, event_list, db=None):
        self.name = name
        self.events = event_list
        if db is not None:
            db.eventdeckdict[self.name] = self
