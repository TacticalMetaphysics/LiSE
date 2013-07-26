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
        self.itemdict = {}
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

    def get_event_start(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if name not in self.event_scheduled or branch not in self.event_scheduled[name]:
            return None
        for (tick_from, tick_to) in self.event_scheduled[name][branch].iteritems():
            if tick_from <= tick and tick <= tick_to:
                return tick_from
        return None

    def get_event_end(self, name, branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        if name not in self.event_scheduled or branch not in self.event_scheduled[name]:
            return None
        for (tick_from, tick_to) in self.event_scheduled[name][branch].iteritems():
            if tick_from <= tick and tick <= tick_to:
                return tick_to
        return None

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


def load_game(dbfilen, language):
    """Load the game in the database file by the given name. Load strings
for the given language. Return a RumorMill object.

    """
    db = RumorMill(dbfilen)
    db.load_game(language)
    return db
