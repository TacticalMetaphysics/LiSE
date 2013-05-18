from util import SaveableMetaclass, dictify_row
from effect import load_effect_decks


class SenselessEvent(Exception):
    pass


class ImpossibleEvent(Exception):
    pass


class IrrelevantEvent(Exception):
    pass


class ImpracticalEvent(Exception):
    pass


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
    tables = [
        ("event",
         {"name": "text",
          "text": "text",
          "ongoing": "boolean",
          "commence_effects": "text",
          "proceed_effects": "text",
          "conclude_effects": "text"},
         ("name",),
         {"commence_effects": ("effect_deck", "name"),
          "proceed_effects": ("effect_deck", "name"),
          "conclude_effects": ("effect_deck", "name")},
         [])]

    def __init__(self, name, text, ongoing, commence_effects,
                 proceed_effects, conclude_effects, db=None):
        self.name = name
        self.text = text
        self.ongoing = ongoing
        self.commence_effects = commence_effects
        self.proceed_effects = proceed_effects
        self.conclude_effects = conclude_effects
        if db is not None:
            db.eventdict[name] = self

    def unravel(self, db):
        if self.text[0] == "@":
            self.text = db.get_text(self.text[1:])
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

    def commence(self):
        self.commence_effects.do()
        self.ongoing = True

    def proceed(self):
        self.proceed_effects.do()

    def conclude(self):
        self.conclude_effects.do()
        self.ongoing = False

    def display_str(self):
        # Sooner or later gonna get it so you can put arbitrary
        # strings in some other table and this refers to that
        return self.name


class EventDeck:
    tables = [
        ("event_deck_link",
         {"deck": "text",
          "idx": "integer",
          "event": "text"},
         ("deck", "idx"),
         {"event": ("event", "name")},
         [])]

    def __init__(self, name, event_list, db=None):
        self.name = name
        self.events = event_list
        if db is not None:
            db.eventdeckdict[self.name] = self


evdl_qcol = ["event_deck_link." + coln for coln in EventDeck.colns]
ev_qval = ["event." + valn for valn in Event.valns]
red_qcol = evdl_qcol + ev_qval
red_col = EventDeck.colns + Event.valns
read_event_decks_qryfmt = (
    "SELECT {0} FROM event_deck_link, event "
    "WHERE event_deck_link.event=event.name "
    "AND event_deck_link.deck IN ({1})".format(
        ", ".join(red_qcol), "{0}"))


def load_event_decks(db, names):
    qryfmt = read_event_decks_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, names)
    r = {}
    effect_deck_names = set()
    for name in names:
        r[name] = []
    for row in db.c:
        rowdict = dictify_row(row, red_col)
        decklist = r[rowdict["name"]]
        while len(decklist) < rowdict["idx"]:
            decklist.append(None)
        rowdict["db"] = db
        effect_deck_names.add(rowdict["commence_effects"])
        effect_deck_names.add(rowdict["proceed_effects"])
        effect_deck_names.add(rowdict["conclude_effects"])
        decklist[rowdict["idx"]] = Event(**rowdict)
    for item in r.iteritems():
        (name, l) = item
        r[name] = EventDeck(name, l, db)
    load_effect_decks(db, list(effect_deck_names))
    for val in r.itervalues():
        val.unravel(db)
    return r


def lookup_between(startdict, start, end):
    r = {}
    tohash = []
    for i in xrange(start, end):
        if i in startdict:
            r[i] = startdict[i]
            tohash.append(i)
            tohash.extend(iter(startdict[i]))
    r["hash"] = hash(tuple(tohash))
    return r


def get_all_starting_between(db, start, end):
    r = {}
    for item in db.startevdict.itervalues():
        r.update(lookup_between(item, start, end))
    return r


def get_all_ongoing_between(db, start, end):
    r = {}
    for item in db.contevdict.itervalues():
        r.update(lookup_between(item, start, end))
    return r


def get_all_ending_between(db, start, end):
    r = {}
    for item in db.endevdict.itervalues():
        r.update(lookup_between(item, start, end))
    return r


def get_all_starting_ongoing_ending(db, start, end):
    return (get_all_starting_between(db, start, end),
            get_all_ongoing_between(db, start, end),
            get_all_ending_between(db, start, end))
