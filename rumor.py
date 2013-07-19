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
from thing import Thing, Schedule
from dimension import Dimension, load_dimensions
from util import dictify_row
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
                 front_board="Physical", seed=0, age=0,
                 hi_place=0, hi_portal=0):
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
        self.caldict = {}
        self.calcoldict = OrderedDict()
        self.carddict = {}
        self.colordict = {}
        self.contentsdict = {}
        self.contevdict = {}
        self.dimensiondict = {}
        self.arrowdict = OrderedDict()
        self.effectdict = {}
        self.effectdeckdict = {}
        self.endevdict = {}
        self.eventdict = {}
        self.graphdict = {}
        self.handdict = {}
        self.handcarddict = {}
        self.imgdict = {}
        self.itemdict = {}
        self.journeydict = {}
        self.locdict = {}
        self.menudict = {}
        self.menuitemdict = {}
        self.pathdestorigdict = {}
        self.pawndict = {}
        self.placedict = {}
        self.placeidxdict = {}
        self.portalorigdestdict = {}
        self.portaldestorigdict = {}
        self.portalidxdict = {}
        self.scheduledict = {}
        self.spotdict = OrderedDict()
        self.startevdict = {}
        self.stringdict = {}
        self.styledict = {}
        self.thingdict = {}
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
            "seed": seed,
            "age": age,
            "hi_place": hi_place,
            "hi_portal": hi_portal}

    def __getattr__(self, attrn):
        if attrn == "front_board":
            return self.game["front_board"]
        elif attrn == "seed":
            return self.game["seed"]
        elif attrn == "age":
            return self.game["age"]
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

    def make_place(self, dimension, name, effect=None, deck=None, event=None):
        index = self.hi_place
        self.hi_place += 1
        pl = Place(self, dimension, name, index)
        pl.unravel()
        pl.save()
        return pl

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

    def make_spot(self, dimension, place, x, y,
                  img=None, effect=None, deck=None, event=None):
        """Return a Spot at the given coordinates, representing the place by
the given name in the given dimension.

If the place does not exist, it will be created.
        """
        if (
                dimension not in self.placedict or
                place not in self.placedict[dimension]):
            self.make_place(dimension, place)
        sp = Spot(self, dimension, place, img, x, y)
        sp.unravel()
        sp.save()
        return sp

    def pawns_on_spot(self, spot):
        """Return a list of pawns on the given spot."""
        return [thing.pawn for thing in
                spot.place.contents
                if thing.name in self.pawndict[spot.dimension]]

    def make_thing(self, dimension, name, location,
                   effect=None, deck=None, event=None):
        th = Thing(dimension, name, location)
        th.unravel()
        th.save()
        return th

    def make_pawn(self, dimension, thing, img,
                  effect=None, deck=None, event=None):
        pwn = Pawn(self, dimension, thing, img)
        pwn.unravel()
        pwn.save()
        return pwn

    def make_portal(self, dimension, origin, destination,
                    effect=None, deck=None, event=None):
        index = self.hi_portal
        self.hi_portal += 1
        port = Portal(self, dimension, origin, destination, index)
        port.unravel()
        port.save()
        dimension.index_portal(port)
        return port

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

    def add_event(self, ev):
        """Add the event to the various dictionaries events go in."""
        self.eventdict[ev.name] = ev
        if hasattr(ev, 'start') and hasattr(ev, 'length'):
            if ev.start not in self.startevdict:
                self.startevdict[ev.start] = set()
            self.startevdict[ev.start].add(ev)
            ev_end = ev.start + ev.length
            for i in xrange(ev.start+1, ev_end-1):
                if i not in self.contevdict:
                    self.contevdict[i] = set()
                self.contevdict[i].add(ev)
            if ev_end not in self.endevdict:
                self.endevdict[ev_end] = set()
            self.endevdict[ev_end].add(ev)

    def remove_event(self, ev):
        """Remove the event from all the dictionaries events go in."""
        del self.eventdict[ev.name]
        if hasattr(ev, 'start'):
            self.startevdict[ev.start].remove(ev)
            if hasattr(ev, 'length'):
                ev_end = ev.start + ev.length
                for i in xrange(ev.start+1, ev_end-1):
                    self.contevdict[i].remove(ev)
                self.endevdict[ev_end].remove(ev)

    def discard_event(self, ev):
        """Remove the event from all the relevant dictionaries here, if it is
a member."""
        if ev.name in self.eventdict:
            del self.eventdict[ev.name]
        if hasattr(ev, 'start') and ev.start in self.startevdict:
            self.startevdict[ev.start].discard(ev)
        if hasattr(ev, 'start') and hasattr(ev, 'length'):
            ev_end = ev.start + ev.length
            for i in xrange(ev.start+1, ev_end-1):
                if i in self.contevdict:
                    self.contevdict[i].discard(ev)
            if ev_end in self.endevdict:
                self.endevdict[ev_end].discard(ev)

    def thing_into_portal(self, dimension_s, thing_s, orig_s, dest_s,
                          effect=None, deck=None, event=None):
        thing = self.thingdict[dimension_s][thing_s]
        portal = self.portalorigdestdict[dimension_s][orig_s][dest_s]
        thing.enter(portal)

    def thing_along_portal(
            self, dimname, thingname, effect=None, deck=None, event=None):
        global dropflag
        thing = self.thingdict[dimname][thingname]
        journey = thing.journey
        portal = journey[0]
        speed = thing.speed_thru(portal)
        journey.move_thing(speed)
        return (effect, thing, portal, speed, None)

    def thing_out_of_portal(
            self, dimname, thingname, effect=None, deck=None, event=None):
        thing = self.thingdict[dimname][thingname]
        (newplace, newport) = thing.journey.step()
        return (effect, newplace, newport, None)

    def create_generic_place(self, arg, effect=None, deck=None, event=None):
        """Take the name of a dimension and return a place in it with a boring
name."""
        return self.make_generic_place(arg)

    def make_generic_place(self, dimension):
        placename = "Place_{0}".format(dimension.hi_place)
        return self.make_place(dimension, placename)

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

    def get_place(self, dimension, name):
        if dimension in self.placedict and name in self.placedict[dimension]:
            return self.placedict[dimension][name]
        elif dimension in self.placeidxdict and name in self.placeidxdict[dimension]:
            return self.placeidxdict[dimension][name]
        else:
            raise KeyError("No place named %s in dimension %s.", name, dimension)

    def get_portal(self, dimension, name):
        if dimension in self.itemdict and name in self.itemdict[dimension]:
            return self.itemdict[dimension][name]
        elif dimension in self.portalidxdict and name in self.portalidxdict[dimension]:
            return self.portalidxdict[dimension][name]
        else:
            raise KeyError("%s is not in dimension %s", name, dimension)

    def get_thing(self, dimension, name):
        return self.thingdict[dimension][name]

    def make_schedule(self, dimname, thingname):
        self.scheduledict[dimname][thingname] = Schedule(
            self, dimname, thingname)

    def get_schedule(self, dimname, thingname):
        if dimname not in self.scheduledict:
            self.scheduledict[dimname] = {}
        if thingname not in self.scheduledict[dimname]:
            self.make_schedule(dimname, thingname)
        return self.scheduledict[dimname][thingname]

    def make_dimension(self, name):
        self.dimensiondict[name] = Dimension(self, name)

    def get_dimension(self, name):
        if name not in self.dimensiondict:
            self.make_dimension(name)
        return self.dimensiondict[name]

    def make_igraph_graph(self, name):
        self.graphdict[name] = igraph.Graph()

    def get_igraph_graph(self, name):
        if name not in self.graphdict:
            self.make_igraph_graph(name)
        return self.graphdict[name]

    def handle_effect(self, effect, deck, event):
        (fun, ex) = self.func[effect._func]
        argmatch = re.match(ex, effect.arg)
        args = argmatch.groups() + (effect, deck, event)
        return fun(*args)


def load_game(dbfilen, language):
    """Load the game in the database file by the given name. Load strings
for the given language. Return a RumorMill object.

    """
    db = RumorMill(dbfilen)
    db.load_game(language)
    return db
