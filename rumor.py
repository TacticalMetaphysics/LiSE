"""The database backend, with dictionaries of loaded objects.

This is a caching database connector. There are dictionaries for all
objects that can be loaded from the database.

This module does not contain the code used to generate
SQL. That's in util.py, the class SaveableMetaclass.

"""

import sqlite3
import re
import igraph
from collections import OrderedDict
from board import load_boards
from style import read_colors, read_styles
from spot import Spot
from pawn import Pawn
from card import load_cards
from place import Place
from portal import Portal
from thing import Thing, Schedule, Journey
from dimension import Dimension, load_dimensions
from util import dictify_row, keyify_dict
from logging import getLogger


logger = getLogger(__name__)


def set_previous_end(d, tick, pair=False):
    if d != {} and tick not in d:
        p = max([tock for tock in d if tock < tick])
        if pair:
            d[p][1] = tick
        else:
            d[p] = tick

def set_previous_end_pair(d, tick):
    set_previous_end(d, tick, True)


class Fake3DictIter:
    def __init__(self, d1, d2, d3, mode):
        if mode == 'keys':
            self.iter1 = d1.iterkeys()
            self.iter2 = d2.iterkeys()
            self.iter3 = d3.iterkeys()
        elif mode == 'values':
            self.iter1 = d1.itervalues()
            self.iter2 = d2.itervalues()
            self.iter3 = d3.itervalues()
        elif mode == 'items':
            self.iter1 = d1.iteritems()
            self.iter2 = d2.iteritems()
            self.iter3 = d3.iteritems()
        else:
            raise ValueError("Invalid mode: " + mode)

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.iter1.next()
        except StopIteration:
            try:
                return self.iter2.next()
            except StopIteration:
                return self.iter3.next()


class Fake3Dict:
    def __init__(self, d1, d2, d3):
        self.d1 = d1
        self.d2 = d2
        self.d3 = d3

    def __iter__(self):
        return Fake3DictIter(self.d1, self.d2, self.d3, 'keys')

    def __getitem__(self, it):
        try:
            return self.d1[it]
        except KeyError:
            try:
                return self.d2[it]
            except KeyError:
                return self.d3[it]

    def __dict__(self):
        r = {}
        r.update(self.d1)
        r.update(self.d2)
        r.update(self.d3)
        return r

    def iterkeys(self):
        return iter(self)

    def itervalues(self):
        return Fake3DictIter(self.d1, self.d2, self.d3, 'values')

    def iteritems(self):
        return Fake3DictIter(self.d1, self.d2, self.d3, 'items')


class Tick:
    def __init__(self, db, branch, i):
        self.db = db
        self.branch = branch
        self.i = i
        self.commence = Ticklet(self)
        self.proceed = Ticklet(self)
        self.conclude = Ticklet(self)
        self.dimensiondict = Fake3Dict(
            self.commence.dimensiondict,
            self.proceed.dimensiondict,
            self.conclude.dimensiondict)
        self.character_skill = Fake3Dict(
            self.commence.character_skill,
            self.proceed.character_skill,
            self.conclude.character_skill)
        self.character_attrib = Fake3Dict(
            self.commence.character_attrib,
            self.proceed.character_attrib,
            self.conclude.character_attrib)
        self.deck_effect = Fake3Dict(
            self.commence.deck_effect,
            self.proceed.deck_effect,
            self.conclude.deck_effect)
        self.hand_card = Fake3Dict(
            self.commence.hand_card,
            self.proceed.hand_card,
            self.conclude.hand_card)
        # TODO: look at all the various window dicts and add all the
        # stuff that they indicate should happen now

        def __int__(self):
            return self.i

        def __getattr__(self, attrn):
            if attrn == 'event':
                return (
                    self.commence.event +
                    self.proceed.event +
                    self.conclude.event)
            else:
                raise AttributeError("Tick has no attribute " + attrn)

        def successor(self):
            pass
            

        def move_thing(self, dimension, thing, dest):
            # May throw KeyError, in which case you can't logically
            # END the location, because the thing isn't THERE.
            curloc = self.proceed.dimensiondict[dimension]["thing_loc"][thing]
            del self.proceed.dimensiondict[dimension]["thing_loc"][thing]
            self.conclude.add_thing_loc(dimension, thing, curloc)
            self.commence.add_thing_loc(dimension, thing, dest)

        def thing_thru_portal(self, dimension, thing, inc):
            curprog = self.proceed.dimensiondict[dimension]["thing_prog"][thing]
            self.conclude.set_thing_prog(dimension, thing, curprog)
            self.commence.set_thing_prog(dimension, thing, curprog + inc)
            del self.proceed.dimensiondict[dimension]["thing_prog"][thing]
            

def mkdimdict():
    return {
        "character_item": {},
        "path": {},
        "place_by_name": {},
        "place_by_i": [],
        "portal_by_orig_dest": {},
        "portal_by_dest_orig": {},
        "portal_by_i": [],
        "thing_loc": {},
        "thing_prog": {},
        "journey_step": {}}


class Ticklet:
    def __init__(self, tick)
        self.tick = tick
        self.db = tick.db
        self.dimensiondict = {}
        self.character_skill = {}
        self.character_attrib = {}
        self.deck_effect = {}
        self.event = set()
        self.hand_card = {}

    def __int__(self):
        return self.tick.i

    def add_character_item(self, dimension, character, item):
        d = self.dimensiondict
        if dimension not in d:
            d[dimension] = mkdimdict()
        if character not in d[dimension]["character_item"]:
            d[dimension]["character_item"][character] = set()
        d[dimension]["character_item"][character].add(item)

    def discard_character_item(self, dimension, character, item):
        try:
            self.dimensiondict[dimension]["character_item"][character].discard(item)
        except KeyError:
            pass

    def add_character_skill(self, character, skill, effd):
        d = self.character_skill
        if character not in d:
            d[character] = {}
        d[character][skill] = effd

    def discard_character_skill(self, character, skill):
        try:
            del self.character_skill[character][skill]
        except KeyError:
            pass

    def set_character_attribution(self, character, attribute, value):
        d = self.character_attrib
        if character not in d:
            d[character] = {}
        d[character][attribute] = value

    def discard_character_attribution(self, character, attribute):
        try:
            del self.character_attrribute[character][attribute]
        except KeyError:
            pass

    def add_event(self, name):
        self.event.add(name)

    def discard_event(self, name):
        self.event.discard(name)

    def remove_event(self, name):
        self.event.remove(name)

    def insert_into_effect_deck(self, deck, i, effect):
        self.deck_effect[deck].insert(i, effect)

    def set_effect_deck(self, deck, effects):
        self.deck_effect[deck] = effects

    def insert_into_hand(self, hand, i, card):
        self.hand_card[hand].insert(i, card)

    def set_hand(self, hand, cards):
        self.hand_card[hand] = cards

    def set_path(self, dimension, origi, desti, path):
        if dimension not in self.dimensiondict:
            self.dimensiondict[dimension] = mkdimdict()
        d = self.dimensiondict[dimension]["path_by_orig_dest"]
        e = self.dimensiondict[dimension]["path_by_dest_orig"]
        if origi not in d:
            d[origi] = {}
        if desti not in e:
            e[desti] = {}
        d[origi][desti] = path
        e[desti][origi] = path

    def set_place(self, dimension, name, i):
        if dimension not in self.dimensiondict:
            self.dimensiondict[dimension] = mkdimdict()
        d = self.dimensiondict[dimension]["place_by_name"]
        e = self.dimensiondict[dimension]["place_by_i"]
        d[name] = i
        while len(e) <= i:
            e.append(None)
        e[i] = name

    def set_portal(self, dimension, orign, destn, i):
        if dimension not in self.dimensiondict:
            self.dimensiondict[dimension] = mkdimdict()
        d = self.dimensiondict[dimension]["portal_by_orig_dest"]
        e = self.dimensiondict[dimension]["portal_by_dest_orig"]
        f = self.dimensiondict[dimension]["portal_by_i"] 
       if orign not in d
            d[orign] = {}
        d[orign][destn] = i
        if destn not in e:
            e[destn] = {}
        e[destn][orign] = i
        while len(f) <= i:
            f.append(None)
        f[i] = (orign, destn)

    def set_thing_loc(dimension, thing, loc):
        if dimension not in self.dimensiondict:
            self.dimensiondict[dimension] = mkdimdict()
        d = self.dimensiondict[dimension]["thing_loc"]
        d[thing] = loc

    def set_thing_prog(dimension, thing, prog):
        if dimension not in self.dimensiondict:
            self.dimensiondict[dimension] = mkdimdict()
        d = self.dimensiondict[dimension]["thing_prog"]
        d[thing] = prog

    def set_journey_step(dimension, thing, i, origi, desti):
        if dimension not in self.dimensiondict:
            self.dimensiondict[dimension] = mkdimdict()
        d = self.dimensiondict[dimension]["journey_step"]
        if thing not in d:
            d[thing] = []
        while len(d[thing]) <= i:
            d[thing].append(None)
        d[thing][i] = (origi, desti)


def noop(*args, **kwargs):
    """Do nothing."""
    pass

ONE_ARG_RE = re.compile("(.+)")
ITEM_ARG_RE = re.compile("([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)")
MAKE_SPOT_ARG_RE = re.compile(
    "([a-zA-Z0-9]+)\."
    "([a-zA-Z0-9]+),([0-9]+),([0-9]+),?([a-zA-Z0-9]*)")
MAKE_PORTAL_ARG_RE = re.compile(
    "([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)->"
    "([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)")
MAKE_THING_ARG_RE = re.compile(
    "([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)@([a-zA-Z0-9]+)")
THING_INTO_PORTAL_ARG_RE = re.compile("(.*)\.(.*)->Portal\((.*)->(.*)\)")


class RumorMill(object):
    """This is where you should get all your LiSE objects from, generally.

A RumorMill is a database connector that can load and generate LiSE
objects. When loaded or generated, the object will be kept in the
RumorMill, even if nowhere else.

There are some special facilities here for the convenience of
particular LiSE objects: Things look up their location here; Items
(including Things) look up their contents here; and Effects look up
their functions here. That means you need to register functions here
when you want Effects to be able to trigger them. To do that, put your
functions in a dictionary keyed with the strings LiSE should use to
refer to your functions, and pass that dictionary to the RumorMill
method xfunc(). You may also pass such a dictionary to the
constructor, just after the name of the database file.

You need to create a SQLite database file with the appropriate schema
before RumorMill will work. For that, run mkdb.py.

    """

    def __init__(self, dbfilen, xfuncs={},
                 front_board="default_board", front_branch=0 seed=0, tick=0,
                 hi_branch=0, hi_place=0, hi_portal=0):
        """Return a database wrapper around the SQLite database file by the
given name.

Optional argument xfuncs is a dictionary of functions, with strings
for keys. They should take only one argument, also a string. Effects
will be able to call those functions with arbitrary string
arguments.

        """
        self.conn = sqlite3.connect(dbfilen)
        self.cursor = self.conn.cursor()
        self.c = self.cursor
        self.boarddict = {}
        self.boardhanddict = {}
        self.calendardict = {}
        self.calcoldict = OrderedDict()
        self.carddict = {}
        self.colordict = {}
        self.dimensiondict = {}
        self.imgdict = {}
        self.menudict = {}
        self.menuitemdict = {}
        self.stringdict = {}
        self.styledict = {}
        self.tickdict = {}
        self.branch_start = {}
        self.branch_end = {}
        self.branch_parent = {}
        self.branch_children = {}
        self.spotdict = {}
        self.pawndict = {}
        self.arrowdict = {}
        self.eventdict = {}
        self.placedict = {}
        self.portaldict = {}
        self.thingdict = {}
        # "scheduled" dictionaries have a key that includes a branch
        # and a tick. Their values may be either another tick, or else
        # a pair containing some time-sensitive data as the 0th item
        # and a tick as the 1th item. The tick in the value is when a
        # fact stops being true. The tick in the key is when the fact
        # begins being true. The tick in the value may be None, in which
        # case the fact will stay true forever.
        self.event_scheduled = {}
        self.effect_deck_scheduled = {}
        self.char_att_scheduled = {}
        self.char_skill_scheduled = {}
        self.char_item_scheduled = {}
        self.location_scheduled = {}
        self.progress_scheduled = {}
        self.place_scheduled = {}
        self.portal_scheduled = {}
        self.thing_scheduled = {}
        self.hand_card_scheduled = {}
        

        placeholder = (noop, ITEM_ARG_RE)
        self.func = {
            'toggle_menu':
            (self.toggle_menu, ITEM_ARG_RE),
            'toggle_calendar':
            (self.toggle_calendar, ITEM_ARG_RE),
            'hide_menu':
            (self.hide_menu, ITEM_ARG_RE),
            'hide_calendar':
            (self.hide_calendar, ITEM_ARG_RE),
            'show_menu':
            (self.show_menu, ITEM_ARG_RE),
            'show_calendar':
            (self.show_calendar, ITEM_ARG_RE),
            'hide_menus_in_board':
            (self.hide_menus_in_board, ONE_ARG_RE),
            'hide_calendars_in_board':
            (self.hide_calendars_in_board, ONE_ARG_RE),
            'hide_other_menus_in_board':
            (self.hide_other_menus_in_board, ONE_ARG_RE),
            'hide_other_calendars_in_board':
            (self.hide_other_calendars_in_board, ONE_ARG_RE),
            'thing_into_portal':
            (self.thing_into_portal, THING_INTO_PORTAL_ARG_RE),
            'thing_along_portal':
            (self.thing_along_portal, ITEM_ARG_RE),
            'thing_out_of_portal':
            (self.thing_out_of_portal, ITEM_ARG_RE),
            'start_new_map': placeholder,
            'open_map': placeholder,
            'save_map': placeholder,
            'quit_map_editor': placeholder,
            'editor_select': placeholder,
            'editor_copy': placeholder,
            'editor_paste': placeholder,
            'editor_delete': placeholder,
            'create_place':
            (self.make_place, ITEM_ARG_RE),
            'create_generic_place':
            (self.make_generic_place, ONE_ARG_RE),
            'create_thing':
            (self.make_thing, ITEM_ARG_RE),
            'create_portal':
            (self.make_portal, MAKE_PORTAL_ARG_RE),
            'mi_create_place':
            (self.mi_create_place, ONE_ARG_RE),
            'mi_create_thing':
            (self.mi_create_thing, ONE_ARG_RE),
            'mi_create_portal':
            (self.mi_create_portal, ONE_ARG_RE)}
        self.func.update(xfuncs)
        self.game = {
            "front_board": front_board,
            "front_branch": front_branch,
            "seed": seed,
            "tick": tick,
            "hi_branch": hi_branch,
            "hi_place": hi_place,
            "hi_portal": hi_portal}

    def __getattr__(self, attrn):
        if attrn in ("board", "front_board"):
            return self.game["front_board"]
        elif attrn in ("branch", "front_branch"):
            return self.game["front_branch"]
        elif attrn == "seed":
            return self.game["seed"]
        elif attrn == "tick":
            return self.game["tick"]
        elif attrn == "hi_place":
            return self.game["hi_place"]
        elif attrn == "hi_portal":
            return self.game["hi_portal"]
        elif attrn == "world_state":
            return self.get_world_state()
        else:
            raise AttributeError(
                "RumorMill doesn't have the attribute " + attrn)

    def __setattr__(self, attrn, val):
        if attrn in ("front_board", "seed", "age", "hi_place", "hi_portal"):
            getattr(self, "game")[attrn] = val
        else:
            super(RumorMill, self).__setattr__(attrn, val)

    def __del__(self):
        """Try to write changes to disk before dying.

        """
        self.c.close()
        self.conn.commit()
        self.conn.close()

    def get_tick(self, branch, tick):
        if branch not in self.tickdict:
            self.tickdict[branch] = {}
        if tick not in self.tickdict[branch]:
            self.tickdict[branch][tick] = Tick(self, branch, tick)
        return self.tickdict[branch][tick]

    def get_ticks(self, dimension, branch, start, end):
        return [self.get_tick(
            str(dimension), int(branch), i)
                for i in xrange(int(start), int(end))]

    def alter_ticks_from_to(self, branch, tick_from, tick_to, function_name, function_args):
        starttick = self.get_tick(branch, tick_from).commence
        getattr(starttick, function_name)(*function_args)
        endtick = self.get_tick(branch, tick_to).conclude
        getattr(endtick, function_name)(*function_args)
        for i in xargs(tick_from+1, tick_to-1):
            conttick = self.get_tick(branch, i).proceed
            getattr(conttick, function_name)(*function_args)

    def alter_all_ticks_from(self, branch, tick_from, function_name, function_args):
        """Notably doesn't mark the conclusion!"""
        tick_to = max([ticki in self.tickdict[branch] if ticki > tick_from])
        starttick = self.get_tick(branch, tick_from).commence
        getattr(starttick, function_name)(*function_args)
        for i in xrange(tick_from+1, tick_to):
            conttick = self.get_tick(branch, i).proceed
            getattr(conttick, function_name)(*function_args)

    def alter_all_ticks(self, branch, function_name, function_args):
        """You'd better be damn sure."""
        tick_from = min(self.tickdict[branch])
        tick_to = max(self.tickdict[branch])
        starttick = self.tickdict[branch][tick_from].commence
        getattr(starttick, function_name)(*function_args)
        for i in xrange(tick_from+1, tick_to):
            conttick = self.get_tick(branch, i).proceed
            getattr(conttick, function_name)(*function_args)
        

    def alter_ticks(self, branch, tick_from, tick_to, function_name, function_args):
        if tick_to is None:
            if tick_from is None:
                self.alter_all_ticks(branch, function_name, function_args)
            else:
                self.alter_all_ticks_from(branch, tick_from, function_name, function_args)
        else:
            self.alter_ticks_from_to(branch, tick_from, tick_to, function_name, function_args)

    def record_character_item(self, character, dimension, item, branch, tick_from, tick_to):
        self.alter_ticks(branch, tick_from, tick_to,
                         'set_character_item', (character, dimension, item))

    def erase_character_item(self, character, dimension, item, branch, tick_from, tick_to):
        self.alter_ticks(branch, tick_from, tick_to,
                         'remove_character_item', (dimension, character, item))

    def get_character_items(self, character, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        d = w.dimensiondict
        r = {}
        for dimension in iter(d):
            if dimension not in r:
                r[dimension] = set()
            if character in d[dimension]["character_item"]:
                r[dimension].add(d[dimension]["character_item"][character])
        return r

    def get_character_skills(self, character, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.character_skill[character]

    def record_character_attribution(self, character, attribute, value,
                                     branch, tick_from, tick_to):
        self.alter_ticks(None, branch, tick_from, tick_to,
                          'set_character_attribution', (character, attribute, value))

    def erase_character_attribution(self, character, attribute, value, branch, tick_from, tick_to):
        self.alter_ticks(None, branch, tick_from, tick_to,
                         'remove_character_attribution', (character, attribute))

    def get_character_attributions(self, character, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.character_attrib[character]

    def record_scheduled_event(self, event_name, branch, tick_from, tick_to):
        self.alter_ticks(branch, tick_from, tick_to,
                         'add_event', (event_name,))

    def erase_scheduled_event(self, event_name, branch, tick_from, tick_to=None):
        if tick_to is None:
            tick_to = self.event_by_start[event_name][tick_from].tick_to
        del self.event_by_start[event_name][tick_from]
        self.alter_ticks(branch, tick_from, tick_to,
                         'remove_event', (event_name,))

    def get_events(self, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.events

    def get_events_commencing(self, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.commence.events

    def get_events_proceeding(self, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.proceed.events

    def get_events_concluding(self, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.conclude.events

    def record_effect_deck(self, effect_deck_name, effect_list,
                           branch, tick_from, tick_to):
        self.record_ticks(branch, tick_from, tick_to,
                          'set_effect_deck', (effect_deck_name, effect_list))

    def get_effects_in_deck(self, name, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.deck_effect[name]

    def record_hand_cards(self, hand_name, hand_cards,
                          branch, tick_from, tick_to):
        self.record_ticks(branch, tick_from, tick_to,
                          'set_hand_cards', (hand_name, hand_cards))

    def get_cards_in_hand(self, hand, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.hand_card[hand]

    def record_place(self, dimension, place, i,
                     branch, tick_from, tick_to):
        self.record_ticks(branch, tick_from, tick_to,
                          'add_place', (dimension, place, i))

    def get_contents(self, dimension, item, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        r = set()
        for (thing, loc) in w.dimensiondict[
                dimension]["location"].iteritems():
            if loc == item:
                r.add(thing)
        return r

    def record_path(self, dimension, origi, desti, path,
                    branch, tick_from, tick_to):
        self.record_ticks(branch, tick_from, tick_to,
                          'set_path', (dimension, origi, desti, path))

    def get_path(self, dimension, origi, desti, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.dimensiondict[dimension]["path"][origi][desti]

    def record_portal(self, dimension, orign, destn, i,
                      branch, tick_from, tick_to):
        self.record_ticks(branch, tick_from, tick_to,
                          'add_portal', (dimension, orign, destn, i))

    def record_location(self, dimension, thing, loc,
                        branch, tick_from, tick_to):
        self.record_ticks(branch, tick_from, tick_to,
                          'set_thing_loc', (dimension, thing, loc))

    def get_location(self, dimension, thing, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.dimensiondict[dimension]["thing_loc"][thing]

    def record_progress(self, dimension, thing, prog,
                        branch, tick_from, tick_to):
        self.record_ticks(branch, tick_from, tick_to,
                          'set_thing_prog', (dimension, thing, prog))

    def get_progress(self, dimension, thing, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.dimensiondict[dimension]["thing_prog"][thing]

    def record_step(self, dimension, thing, i, origi, desti,
                    branch, tick_from, tick_to):
        self.record_ticks(branch, tick_from, tick_to,
                          'set_journey_step', (dimension, thing, i, origi, desti))

    def get_step(self, dimension, thing, i, branch=None, tick=None):
        w = self.get_world_state(branch, tick)
        return w.dimensiondict[dimension]["thing_prog"][thing][i]

    def insert_rowdicts_table(self, rowdict, clas, tablename):
        """Insert the given rowdicts into the table of the given name, as
defined by the given class.

For more information, consult SaveableMetaclass in util.py.

        """
        if rowdict != []:
            clas.dbop['insert'](self, rowdict, tablename)

    def delete_keydicts_table(self, keydict, clas, tablename):
        """Delete the records identified by the keydicts from the given table,
as defined by the given class.

For more information, consult SaveableMetaclass in util.py.

        """
        if keydict != []:
            clas.dbop['delete'](self, keydict, tablename)

    def detect_keydicts_table(self, keydict, clas, tablename):
        """Return the rows in the given table, as defined by the given class,
matching the given keydicts.

For more information, consult SaveableMetaclass in util.py.

        """
        if keydict != []:
            return clas.dbop['detect'](self, keydict, tablename)
        else:
            return []

    def missing_keydicts_table(self, keydict, clas, tablename):
        """Return rows in the given table, as defined by the given class,
*not* matching any of the given keydicts.

For more information, consult SaveableMetaclass in util.py.

        """
        if keydict != []:
            return clas.dbop['missing'](self, keydict, tablename)
        else:
            return []

    def xfunc(self, func, name=None):
        """Add the given function to those accessible to effects.

Optional argument name is the one the effect needs to use to access
the function.

        """
        if name is None:
            self.func[func.__name__] = func
        else:
            self.func[name] = func

    def load_dimensions(self, dimname):
        """Load all dimensions with names in the given list.

Return a list of them.

"""
        return load_dimensions(self, dimname)

    def load_dimension(self, dimname):
        """Load and return the dimension with the given name."""
        return self.load_dimensions([dimname])[0]

    def load_boards(self, dimname):
        """Load the boards representing the named dimensions. Return them in a
list.

        """
        return load_boards(self, dimname)

    def load_board(self, dimname):
        """Load and return the board representing the named dimension."""
        return self.load_boards([dimname])[dimname]

    def load_colors(self, colornames):
        """Load the colors by the given names."""
        # being that colors are just fancy tuples fulla integers,
        # there's nothing to unravel. just read them.
        return read_colors(self, colornames)

    def load_color(self, colorname):
        """Load the color by the given name."""
        return self.load_colors((colorname,))

    def things_in_place(self, place):
        """Return a list of Thing objects that are located in the given Place
object.

The things' location property will be used. Note that things are
always considered to be in one place or another, even if they are also
in the portal between two places.

        """
        dim = place.dimension
        pname = place.name
        pcd = self.placecontentsdict
        if dim not in pcd or pname not in pcd[dim]:
            return []
        thingnames = self.placecontentsdict[dim][pname]
        return [self.itemdict[dim][name] for name in thingnames]

    def pawns_on_spot(self, spot):
        """Return a list of pawns on the given spot."""
        return [thing.pawn for thing in
                spot.place.contents
                if thing.name in self.pawndict[spot.dimension]]
    def make_board(self, name, width, height, view_left, view_bot, wallpaper,
                   effect=None, deck=None, event=None):
        bord = Board(self, name, width, height, view_left, view_bot, wallpaper)
        bord.unravel()
        bord.save()
        return bord

    def toggle_menu(self, menuitem, menu,
                    effect=None, deck=None, event=None):
        boardname = str(menuitem.board)
        menuname = str(menu)
        self.hide_other_menus_in_board(boardname, menuname)
        self.menudict[boardname][menuname].toggle_visibility()

    def toggle_calendar(self, menuitem, cal,
                        effect=None, deck=None, event=None):
        boardname = str(menuitem.board)
        calname = str(cal)
        self.hide_other_calendars_in_board(boardname, calname)
        self.calendardict[boardname][calname].toggle_visibility()

    def hide_menu(self, menuitem, menuname,
                  effect=None, deck=None, event=None):
        """A callback for MenuItem. Hide the menu of the given name, in the
same board as the caller."""
        boardname = str(menuitem.board)
        self.menudict[boardname][menuname].hide()

    def hide_calendar(self, menuitem, calname,
                      effect=None, deck=None, event=None):
        boardname = str(menuitem.board)
        self.calendardict[boardname][calname].hide()

    def show_menu(self, menuitem, menuname,
                  effect=None, deck=None, event=None):
        """A callback for MenuItem. Show the menu of the given name, in the
same board as the caller."""
        boardname = str(menuitem.board)
        self.menudict[boardname][menuname].show()

    def show_calendar(self, menuitem, calname,
                      effect=None, deck=None, event=None):
        boardname = str(menuitem.board)
        self.calendardict[boardname][calname].show()

    def hide_menus_in_board(self, board,
                            effect=None, deck=None, event=None):
        boardn = str(board)
        for menu in self.menudict[boardn].itervalues():
            if not menu.main_for_window:
                menu.hide()

    def hide_other_menus_in_board(self, board, menu,
                                  effect=None, deck=None, event=None):
        boardn = str(board)
        menun = str(menu)
        for menu in self.menudict[boardn].itervalues():
            if not menu.main_for_window and menu.name != menun:
                menu.hide()

    def hide_calendars_in_board(self, board,
                                effect=None, deck=None, event=None):
        boardn = str(board)
        for calendar in self.calendardict[boardn].itervalues():
            calendar.hide()

    def hide_other_calendars_in_board(self, board, calendar,
                                      effect=None, deck=None, event=None):
        boardn = str(board)
        itn = str(calendar)
        for calendar in self.calendardict[boardn].iteritems():
            (itname, cal) = calendar
            if itname != itn:
                cal.hide()

    def get_age(self):
        """Get the number of ticks since the start of the game. Persists
between sessions.

This is game-world time. It doesn't always go forwards.

        """
        return self.game["age"]

    def get_text(self, strname):
        """Get the string of the given name in the language set at startup."""
        return self.stringdict[strname][self.lang]

    def load_strings(self):
        """Load all the named strings and keep them in a dictionary.

Please use self.get_text() to lookup these strings later."""
        self.c.execute("SELECT * FROM strings;")
        for row in self.c:
            (stringn, lang, string) = row
            if stringn not in self.stringdict:
                self.stringdict[stringn] = {}
            self.stringdict[stringn][lang] = string

    def load_game(self, lang):
        """Load the metadata, the strings, and the main board for the game in
this database.

Spell the lang argument the same way it's spelled in the strings table.

        """
        self.c.execute("SELECT * FROM game;")
        self.game = dictify_row(
            self.c.fetchone(),
            ("front_board", "age", "seed", "hi_place", "hi_portal"))
        self.lang = lang
        self.load_strings()
        self.load_board(self.game["front_board"])

    def thing_into_portal(self, dimension_s, thing_s, orig_s, dest_s,
                          effect=None, deck=None, event=None, branch=None, tick=None):
        portal = self.get_portal_orig_dest(dimension_s, orig_s, dest_s)
        thing = self.thingdict[dimension_s][thing_s]
        thing.enter(portal)

    def thing_along_portal(
            self, dimname, branch, tick_from, thingname, effect=None, deck=None, event=None):
        global dropflag
        thing = self.thingdict[dimname][branch][tick_from][thingname]
        journey = thing.journey
        portal = journey[0]
        speed = thing.speed_thru(portal)
        journey.move_thing(speed)
        return (effect, thing, portal, speed, None)

    def thing_out_of_portal(
            self, dimname, branch, tick_from, thingname, effect=None, deck=None, event=None):
        thing = self.thingdict[dimname][branch][tick_from][thingname]
        (newplace, newport) = thing.journey.step()
        return (effect, newplace, newport, None)

    def mi_create_place(self, menuitem, arg):
        return menuitem.gw.create_place()

    def mi_create_thing(self, menuitem, arg):
        return menuitem.gw.create_thing()

    def mi_create_portal(self, menuitem, arg):
        return menuitem.gw.create_portal()

    def load_cards(self, names):
        load_cards(self, names)

    def load_card(self, name):
        self.load_cards([name])

    def get_card_base(self, name):
        """Return the CardBase named thus, loading it first if necessary."""
        if name not in self.carddict:
            self.load_card(name)
        return self.carddict[name]

    def load_styles(self, names):
        """Load all styles with names in the given iterable."""
        read_styles(self, names)

    def load_style(self, name):
        """Load the style by the given name."""
        read_styles(self, [name])

    def get_style(self, name):
        """Return the Style by the given name, loading it first if
necessary."""
        if name not in self.styledict:
            self.load_styles(name)
        return self.styledict[name]

    def get_board(self, name):
        return self.boarddict[name]

    def make_igraph_graph(self, name):
        self.graphdict[name] = igraph.Graph(directed=True)

    def get_igraph_graph(self, name):
        if name not in self.graphdict:
            self.make_igraph_graph(name)
        return self.graphdict[name]

    def handle_effect(self, effect, deck, event):
        (fun, ex) = self.func[effect._func]
        argmatch = re.match(ex, effect.arg)
        args = argmatch.groups() + (effect, deck, event)
        return fun(*args)

    def save_game(self):
        self.c.execute("DELETE FROM game")
        fieldnames = self.game.keys()
        qrystr = "INSERT INTO game ({0}) VALUES ({1})".format(
            ", ".join(fieldnames), ", ".join(["?"] * len(fieldnames)))
        qrylst = [self.game[field] for field in fieldnames]
        qrytup = tuple(qrylst)
        self.c.execute(qrystr, qrytup)
        for dimension in self.dimensiondict.itervalues():
            dimension.save()

    def get_world_state(self, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if branch not in self.tickdict:
            self.tickdict[branch] = {}
        if tick not in self.tickdict[branch]:
            prevticks = [n for n in self.tickdict[branch] if n<tick]
            if prevticks == []:
                self.tickdict[branch][tick] = Tick(self, branch, tick)
            else:
                prevtick = max(prevticks)
                for i in xrange(prevtick+1, tick):
                    self.tickdict[branch][i] = self.tickdict[branch][i-1].successor()
        return self.tickdict[branch][tick]
    # TODO: For all these schedule functions, handle the case where I
    # try to schedule something for a time outside of the given
    # branch. These functions may not be the most appropriate *place*
    # to handle that.

    def schedule_something(self, scheddict, dictkeytup,
                           val=None, branch=None, tick_from=None, tick_to=None):
        if branch is None:
            branch = self.branch
        if tick_from is None:
            tick_from = self.tick
        ptr = scheddict
        for key in dictkeytup + (branch,):
            if key not in ptr:
                ptr[key] = {}
            ptr = ptr[key]
        if val is None:
            ptr[tick_from] = tick_to
        else:
            ptr[tick_from] = (val, tick_to)

    def schedule_event(self, name, branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.event_scheduled, (name,), None, branch, tick_from, tick_to)

    def event_is_commencing(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        return (name in self.event_scheduled and
                branch in self.event_scheduled[name] and
                tick in self.event_scheduled[name][branch])

    def event_is_concluding(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if name not in self.event_scheduled or branch not in self.event_scheduled[name]:
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if prevstart < tick and self.event_scheduled[name][branch][prevstart] == tick:
                return True
        return False

    def event_is_proceeding(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if name not in self.event_scheduled or branch not in self.event_scheduled[name]:
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if prevstart < tick and self.event_scheduled[name][branch][prevstart] > tick:
                return True
        return False

    def event_is_starting_or_proceeding(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if name not in self.event_scheduled or branch not in self.event_scheduled[name]:
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if prevstart == tick:
                return True
            elif prevstart < tick and self.event_scheduled[name][branch][prevstart] > tick:
                return True
        return False

    def event_is_proceeding_or_concluding(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if name not in self.event_scheduled or branch not in self.event_scheduled[name]:
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if prevstart < tick:
                if self.event_scheduled[name][branch][prevstart] >= tick:
                    return True
        return False

    def event_is_happening(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if name not in self.event_scheduled or branch not in self.event_scheduled[name]:
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if prevstart == tick:
                return True
            elif prevstart < tick:
                if self.event_scheduled[name][branch][prevstart] >= tick:
                    return True
        return False

    def schedule_effect_deck(self, name, cards,
                             branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.effect_deck_scheduled, (name,), cards, branch, tick_from, tick_to)

    def get_effect_deck_card_names(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, (cards, conclusion)) in self.effect_deck_scheduled[
                name][branch].iteritems():
            if commencement <= tick and conclusion >= tick:
                return cards
        return None

    def schedule_char_att(self, char_s, att_s, val,
                          branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.char_att_scheduled, (char_s, att_s), val, branch, tick_from, tick_to)

    def get_char_att_val(self, char_s, att_s, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, (value, conclusion)) in self.char_att_scheduled[
                char_s][att_s][branch].iteritems():
            if commencement <= tick and conclusion >= tick:
                return value
        return None

    def schedule_char_skill(self, char_s, skill_s, effect_deck_s,
                            branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.char_skill_scheduled, (char_s, skill_s), effect_deck_s,
            branch, tick_from, tick_to)

    def get_char_skill_deck_name(self, char_s, skill_s, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, (deck, conclusion)) in self.char_skill_scheduled[
                char_s][skill_s][branch_s].iteritems():
            if commencement <= tick and conclusion >= tick:
                return deck
        return ''

    def schedule_char_item(self, char_s, dimension_s, item_s,
                           branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.char_item_scheduled, (char_s, dimension_s, item_s),
            None, branch, tick_from, tick_to)

    def character_is_item(self, char_s, dimension_s, item_s,
                          branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, conclusion) in self.char_item_scheduled[char_s][dimension_s][item_s][branch]:
            if commencement <= tick and conclusion >= tick:
                return True
        return False

    def schedule_location(self, dimension_s, thing_s, place_s,
                          branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.location_scheduled, (dimension_s, thing_s),
            place_s, branch, tick_from, tick_to)

    def get_location_name(self, dimension_s, thing_s, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, (locn, conclusion)) in self.location_scheduled[
                dimension_s][thing_s][branch].iteritems():
            if commencement <= tick and conclusion >= tick:
                return locn
        return ''

    def schedule_progress(self, dimension_s, thing_s, new_prog,
                          branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.progress_scheduled, (dimension_s, thing_s), new_prog,
            branch, tick_from, tick_to)

    def get_progress(self, dimension_s, thing_s, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, (progress, conclusion)) in self.progress_scheduled[
                dimension_s][thing_s][branch]:
            if commencement <= tick and conclusion >= tick:
                return progress
        return 0.0

    def schedule_hand_card(self, hand_s, card_s, card_n,
                           branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.hand_card_scheduled, (hand_s, card_s), card_n,
            branch, tick_from, tick_to)

    def card_copies_in_hand(self, hand_s, card_s, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, (n, conclusion)) in self.hand_card_scheduled[
                hand_s][card_s][branch].iteritems():
            if commencement <= tick and conclusion >= tick:
                return n
        return 0

    def schedule_place(self, dimension_s, place_s,
                       branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.place_scheduled, (dimension_s, place_s),
            None, branch, tick_from, tick_to)

    def place_exists(self, dimension_s, place_s, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, conclusion) in self.place_scheduled[
                dimension_s][place_s][branch].iteritems():
            if commencement <= tick and conclusion >= tick:
                return True
        return False

    def schedule_portal(self, dimension_s, orig_s, dest_s,
                        branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.portal_scheduled, (dimension_s, orig_s, dest_s),
            None, branch, tick_from, tick_to)

    def portal_exists(self, dimension_s, orig_s, dest_s,
                      branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, conclusion) in self.portal_scheduled[
                dimension_s][orig_s][dest_s][branch].iteritems():
            if commencement <= tick and conclusion >= tick:
                return True
        return False

    def schedule_thing(self, dimension_s, thing_s,
                       branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.thing_scheduled, (dimension_s, thing_s),
            None, branch, tick_from, tick_to)

    def thing_exists(self, dimension_s, thing_s, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, conclusion) in self.thing_scheduled[
                dimension_s][thing_s][branch].iteritems():
            if commencement <= tick and conclusion >= tick:
                return True
        return False

def load_game(dbfilen, language):
    """Load the game in the database file by the given name. Load strings
for the given language. Return a RumorMill object.

    """
    db = RumorMill(dbfilen)
    db.load_game(language)
    return db
