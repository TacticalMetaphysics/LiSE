"""The database backend, with dictionaries of loaded objects.

This is a caching database connector. There are dictionaries for all
objects that can be loaded from the database.

This module does not contain the code used to generate
SQL. That's in util.py, the class SaveableMetaclass.

"""

import sqlite3
import re
import igraph
from dimension import Dimension
from place import Place
from portal import Portal
from spot import Spot
from collections import OrderedDict
from logging import getLogger
from util import dictify_row


logger = getLogger(__name__)


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
                 front_board="default_board", front_branch=0, seed=0, tick=0,
                 hi_branch=0, hi_place=0, hi_portal=0, lang="eng"):
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
        self.effectdict = {}
        self.effectdeckdict = {}
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
        self.itemdict = {}
        self.lang = lang
        # "scheduled" dictionaries have a key that includes a branch
        # and a tick. Their values may be either another tick, or else
        # a pair containing some time-sensitive data as the 0th item
        # and a tick as the 1th item. The tick in the value is when a
        # fact stops being true. The tick in the key is when the fact
        # begins being true. The tick in the value may be None, in which
        # case the fact will stay true forever.
        self.effect_deck_scheduled = {}
        self.char_att_scheduled = {}
        self.char_skill_scheduled = {}
        self.char_item_scheduled = {}
        self.hand_card_scheduled = {}

        placeholder = (noop, ITEM_ARG_RE)
        self.func = {
            'one': placeholder,
            'two': placeholder,
            'toggle_menu':
            (self.toggle_menu, ONE_ARG_RE),
            'hide_menu':
            (self.hide_menu, ONE_ARG_RE),
            'show_menu':
            (self.show_menu, ONE_ARG_RE),
            'make_generic_place':
            (self.make_generic_place, ONE_ARG_RE),
            'start_new_map': placeholder,
            'open_map': placeholder,
            'save_map': placeholder,
            'quit_map_editor': placeholder,
            'editor_select': placeholder,
            'editor_copy': placeholder,
            'editor_paste': placeholder,
            'editor_delete': placeholder,
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
        elif attrn == "hi_branch":
            return self.game["hi_branch"]
        elif attrn == "hi_place":
            return self.game["hi_place"]
        elif attrn == "hi_portal":
            return self.game["hi_portal"]
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

    def pawns_on_spot(self, spot):
        """Return a list of pawns on the given spot."""
        return [thing.pawn for thing in
                spot.place.contents
                if thing.name in self.pawndict[spot.dimension]]

    def toggle_menu(self, menuitem, menuname,
                    effect=None, deck=None, event=None):
        window = menuitem.menu.window
        menu = window.menus_by_name[menuname]
        menu.visible = not menu.visible
        menu.tweaks += 1

    def hide_menu(self, menuitem, menuname,
                  effect=None, deck=None, event=None):
        window = menuitem.menu.window
        menu = window.menus_by_name[menuname]
        menu.visible = False
        menu.tweaks += 1

    def show_menu(self, menuitem, menuname,
                  effect=None, deck=None, event=None):
        window = menuitem.menu.window
        menu = window.menus_by_name[menuname]
        menu.visible = True
        menu.tweaks += 1

    def get_age(self):
        """Get the number of ticks since the start of the game. Persists
between sessions.

This is game-world time. It doesn't always go forwards.

        """
        return self.game["age"]

    def get_text(self, strname):
        """Get the string of the given name in the language set at startup."""
        return self.stringdict[strname][self.lang]

    def mi_create_place(self, menuitem):
        return menuitem.window.create_place()

    def mi_create_thing(self, menuitem):
        return menuitem.window.create_thing()

    def mi_create_portal(self, menuitem):
        return menuitem.window.create_portal()

    def get_card_base(self, name):
        """Return the CardBase named thus, loading it first if necessary."""
        if name not in self.carddict:
            self.load_card(name)
        return self.carddict[name]

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

    # TODO: For all these schedule functions, handle the case where I
    # try to schedule something for a time outside of the given
    # branch. These functions may not be the most appropriate *place*
    # to handle that.

    def schedule_something(
            self, scheddict, dictkeytup,
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

    def schedule_event(self, ev, branch=None, tick_from=None, tick_to=None):
        if not hasattr(ev, 'schedule'):
            ev.schedule = {}
        if branch not in ev.schedule:
            ev.schedule[branch] = {}
        ev.schedule[branch][tick_from] = tick_to

    def event_is_commencing(self, ev, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick

    def event_is_concluding(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if (
                name not in self.event_scheduled or
                branch not in self.event_scheduled[name]):
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if (
                    prevstart < tick and
                    self.event_scheduled[
                        name][branch][prevstart] == tick):
                return True
        return False

    def event_is_proceeding(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if (
                name not in self.event_scheduled or
                branch not in self.event_scheduled[name]):
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if (
                    prevstart < tick and
                    self.event_scheduled[
                        name][branch][prevstart] > tick):
                return True
        return False

    def event_is_starting_or_proceeding(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if (
                name not in self.event_scheduled or
                branch not in self.event_scheduled[name]):
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if prevstart == tick:
                return True
            elif (
                    prevstart < tick and
                    self.event_scheduled[
                        name][branch][prevstart] > tick):
                return True
        return False

    def event_is_proceeding_or_concluding(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if (
                name not in self.event_scheduled or
                branch not in self.event_scheduled[name]):
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
        if (
                name not in self.event_scheduled or
                branch not in self.event_scheduled[name]):
            return False
        for prevstart in self.event_scheduled[name][branch]:
            if prevstart == tick:
                return True
            elif prevstart < tick:
                if self.event_scheduled[name][branch][prevstart] >= tick:
                    return True
        return False

    def get_event_start(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if (
                name not in self.event_scheduled or
                branch not in self.event_scheduled[name]):
            return None
        for (tick_from, tick_to) in (
                self.event_scheduled[name][branch].iteritems()):
            if tick_from <= tick and tick <= tick_to:
                return tick_from
        return None

    def get_event_end(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if (
                name not in self.event_scheduled or
                branch not in self.event_scheduled[name]):
            return None
        for (tick_from, tick_to) in (
                self.event_scheduled[name][branch].iteritems()):
            if tick_from <= tick and tick <= tick_to:
                return tick_to
        return None

    def schedule_effect_deck(self, name, cards,
                             branch=None, tick_from=None, tick_to=None):
        self.schedule_something(
            self.effect_deck_scheduled,
            (name,), cards, branch, tick_from, tick_to)

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
            self.char_att_scheduled,
            (char_s, att_s), val, branch, tick_from, tick_to)

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

    def get_char_skill_deck_name(
            self, char_s, skill_s, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        for (commencement, (deck, conclusion)) in self.char_skill_scheduled[
                char_s][skill_s][branch].iteritems():
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
        for (commencement, conclusion) in (
                self.char_item_scheduled[
                    char_s][dimension_s][item_s][branch]):
            if commencement <= tick and conclusion >= tick:
                return True
        return False

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

    def load_game(self):
        self.c.execute(
            "SELECT front_board, front_branch, tick, seed, "
            "hi_branch, hi_place, hi_portal FROM game")
        for row in self.c:
            self.game = {
                "front_board": row[0],
                "front_branch": row[1],
                "tick": row[2],
                "seed": row[3],
                "hi_branch": row[4],
                "hi_place": row[5],
                "hi_portal": row[6]}

    def load_strings(self):
        self.c.execute("SELECT stringname, language, string FROM strings")
        for row in self.c:
            rowd = dictify_row(row, ("stringname", "language", "string"))
            if rowd["stringname"] not in self.stringdict:
                self.stringdict[rowd["stringname"]] = {}
            self.stringdict[rowd["stringname"]][rowd["language"]] = rowd["string"]

    def get_dimension(self, dimn):
        if dimn not in self.dimensiondict:
            self.dimensiondict[dimn] = Dimension(self, dimn)
            self.dimensiondict[dimn].load()
        return self.dimensiondict[dimn]

    def make_generic_place(self, dimension):
        placen = "generic_place_{0}".format(self.hi_place)
        self.hi_place += 1
        pl = Place(dimension, placen)
        dimension.places_by_name[placen] = pl
        dimension.places.append(pl)
        return pl

    def make_spot(self, board, place, x, y):
        spot = Spot(board, place)
        if not hasattr(place, 'spots'):
            place.spots = []
        while len(place.spots) <= int(board):
            place.spots.append(None)
        place.spots[int(board)] = spot
        spot.set_img(self.imgdict['default_spot'])
        spot.set_coords(x, y)

    def make_portal(self, orig, dest):
        dimension = orig.dimension
        port = Portal(dimension, orig, dest)
        port.exist()
        if str(orig) not in dimension.portals_by_orign_destn:
            dimension.portals_by_orign_destn[str(orig)] = {}
        dimension.portals_by_orign_destn[str(orig)][str(dest)] = port
        dimension.portals.append(port)
        return port

def load_game(dbfn, lang="eng"):
    db = RumorMill(dbfn, lang=lang)
    db.load_game()
    db.load_strings()
    return db
