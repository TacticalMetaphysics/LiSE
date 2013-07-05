"""Containers for EffectDecks that have beginnings, middles, and ends.

Events, in LiSE, resemble events in programming generally insofar as
you register listeners in the form of EffectDecks, and the listeners
get called when the event is fired. Events here actually have *three*
EffectDecks registered, one each for the moment the event starts, the
moment it ends, and the various ticks in between.

Events get passed to the effect decks, which may or may not use them
for anything in particular.

"""
from util import SaveableMetaclass, dictify_row, stringlike
from effect import (
    read_effect_decks,
    PortalEntryEffectDeck,
    PortalProgressEffectDeck,
    PortalExitEffectDeck)
import logging


logger = logging.getLogger(__name__)


class SenselessEvent(Exception):
    """Exception raised when trying to fire events that can't happen
anywhere ever."""
    pass


class ImpossibleEvent(Exception):
    """Exception raised when trying to fire events that can't happen given
the present circumstances."""
    pass


class IrrelevantEvent(Exception):
    """Exception raised when trying to fire events that could happen if
they hadn't already, or if some other event hadn't already done the
same thing."""
    pass


class ImpracticalEvent(Exception):
    """Exception raised when trying to fire events that could happen, but
are bad ideas. They may be allowed to pass anyway if the characters
involved *insist*."""
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
         {"name": "text not null",
          "text": "text not null",
          "ongoing": "boolean not null",
          "commence_effects": "text",
          "proceed_effects": "text",
          "conclude_effects": "text"},
         ("name",),
         {"commence_effects": ("effect_deck", "name"),
          "proceed_effects": ("effect_deck", "name"),
          "conclude_effects": ("effect_deck", "name")},
         [])]

    def __init__(self, db, name, text, ongoing, commence_effects,
                 proceed_effects, conclude_effects):
        """Return an Event with the given name, text, and ongoing-status, and
the three given effect decks. Register with db.eventdict.

        """
        self.name = name
        self._text = text
        self.ongoing = ongoing
        self._commence_effects = str(commence_effects)
        self._proceed_effects = str(proceed_effects)
        self._conclude_effects = str(conclude_effects)
        db.add_event(self)
        self.db = db

    def __getattr__(self, attrn):
        if attrn == "text":
            if self._text[0] == "@":
                return self.db.get_text[self._text[1:]]
            else:
                return self._text
        elif attrn == "commence_effects":
            if self._commence_effects == 'None':
                return None
            else:
                return self.db.effectdeckdict[self._commence_effects]
        elif attrn == "proceed_effects":
            if self._proceed_effects == 'None':
                return None
            else:
                return self.db.effectdeckdict[self._proceed_effects]
        elif attrn == "conclude_effects":
            if self._conclude_effects == 'None':
                return None
            else:
                return self.db.effectdeckdict[self._conclude_effects]
        else:
            raise AttributeError("Event has no such attribute")

    def __repr__(self):
        if hasattr(self, 'start') and hasattr(self, 'length'):
            return "{0}[{1}->{2}]".format(
                self.name,
                self.start,
                self.start + self.length)

    def get_tabdict(self):
        return {
            "name": self.name,
            "text": self.text,
            "ongoing": self.ongoing,
            "commence_effects": self.commence_effects.name,
            "proceed_effects": self.proceed_effects.name,
            "conclude_effects": self.conclude_effects.name}

    def unravel(self):
        """Dereference the effect decks.

If the event text begins with @, it's a pointer; look up the real
value in the db.

        """
        for deck in (self.commence_effects, self.proceed_effects,
                     self.conclude_effects):
            if deck is not None:
                deck.unravel()

    def cmpcheck(self, other):
        """Check if this event is comparable to the other. Raise TypeError if
not."""
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

    def __hash__(self):
        if hasattr(self, 'start') and hasattr(self, 'length'):
            return hash((self.start, self.length, self.name))
        else:
            return hash(self.name)

    def commence(self):
        """Perform all commence effects, and set self.ongoing to True."""
        if self.commence_effects is not None:
            self.commence_effects.do(self)
        self.ongoing = True

    def proceed(self):
        """Perform all proceed effects."""
        if self.proceed_effects is not None:
            self.proceed_effects.do(self)

    def conclude(self):
        """Perform all conclude effects, and set self.ongoing to False."""
        if self.conclude_effects is not None:
            self.conclude_effects.do(self)
        self.ongoing = False

    def display_str(self):
        """Get the text to be shown in this event's calendar cell, and return
it."""
        # Sooner or later gonna get it so you can put arbitrary
        # strings in some other table and this refers to that
        return self.name

    def get_tabdict(self):
        return {
            "event": {
                "name": self.name,
                "ongoing": self.ongoing,
                "commence_effects": self._commence_effects,
                "proceed_effects": self._proceed_effects,
                "conclude_effects": self._conclude_effects}}


class PortalTravelEvent(Event):
    """Event representing a thing's travel through a single portal, from
one place to another."""
    name_format = "PortalTravelEvent {0}: {1}: {2}-{3}->{4}"
    text_format = "Travel from {0} to {1}"

    def __init__(self, db, thing, portal, ongoing):
        dimname = thing.dimension.name
        origname = str(portal.orig)
        destname = str(portal.dest)
        name = self.name_format.format(
            dimname, thing.name, origname, str(portal), destname)
        text = self.text_format.format(origname, destname)
        commence_effects = None
        proceed_effects = PortalProgressEffectDeck(db, thing)
        conclude_effects = PortalExitEffectDeck(db, thing)
        Event.__init__(
            self, db, name, text, ongoing,
            commence_effects, proceed_effects, conclude_effects)


class EventDeck:
    """A deck representing events that might get scheduled at some point."""
    tables = [
        ("event_deck_link",
         {"deck": "text not null",
          "idx": "integer not null",
          "event": "text not null"},
         ("deck", "idx"),
         {"event": ("event", "name")},
         [])]

    def __init__(self, db, name, event_list):
        """Return an EventDeck with the given name, containing the given
events. Register with db.eventdeckdict.

        """
        self.name = name
        self.events = event_list
        db.eventdeckdict[self.name] = self
        self.db = db

    def get_tabdict(self):
        rowdicts = []
        for i in xrange(0, len(self.events)):
            rowdicts.append({
                "deck": self.name,
                "idx": i,
                "event": self.events[i].name})
        return {"event_deck_link": rowdicts}

    def unravel(self):
        for i in xrange(0, len(self.events)):
            if stringlike(self.events[i]):
                self.events[i] = self.db.eventdict[self.events[i]]


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
    """Load the event decks by the given names, including all effects
therein.

Return a dictionary, keyed by the event deck name."""
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
        val.unravel()
    return r


def lookup_between(startdict, start, end):
    """Given a dictionary with integer keys, return a subdictionary with
those keys falling between these bounds."""
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
    """Look through all the events yet loaded by the database, and return
a dictionary of those that start in the given range."""
    r = {}
    for item in db.startevdict.itervalues():
        r.update(lookup_between(item, start, end))
    return r


def get_all_ongoing_between(db, start, end):
    """Look through all the events yet loaded by the database, and return
a dictionary of those that occur (but perhaps not start or end) in
the given range."""
    r = {}
    for item in db.contevdict.itervalues():
        r.update(lookup_between(item, start, end))
    return r


def get_all_ending_between(db, start, end):
    """Look through all the events yet loaded by the database, and return
a dictionary of those that end in the given range.

    """
    r = {}
    for item in db.endevdict.itervalues():
        r.update(lookup_between(item, start, end))
    return r


def get_all_starting_ongoing_ending(db, start, end):
    """Return a tuple of events from the db that (start, continue, end) in
the given range."""
    return (get_all_starting_between(db, start, end),
            get_all_ongoing_between(db, start, end),
            get_all_ending_between(db, start, end))

EVENTS_QRYFMT = """SELECT {0} FROM event WHERE name IN ({1})""".format(
    ", ".join(Event.colns), "{0}")

def read_events(db, names):
    """Read, instantiate, but don't unravel events by the given names."""
    qryfmt = EVENTS_QRYFMT
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, tuple(names))
    r = {}
    effect_decks = set()
    for row in db.c:
        rowdict = dictify_row(row, Event.colns)
        rowdict["db"] = db
        for deckname in (rowdict["commence_effects"],
            rowdict["proceed_effects"],
            rowdict["conclude_effects"]):
            effect_decks.add(deckname)
        r[rowdict["name"]] = Event(**rowdict)
    read_effect_decks(db, effect_decks)
    return r

def load_events(db, names):
    r = read_events(db, names)
    for ev in r.itervalues():
        ev.unravel()
    return r
