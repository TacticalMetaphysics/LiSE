"""The database backend, with dictionaries of loaded objects.

This is a caching database connector. There are dictionaries for all
objects that can be loaded from the database.

This module does not contain the code used to generate
SQL. That's in util.py, the class SaveableMetaclass.

"""

import sqlite3
import board
import dimension
import item
import re
import logging
from collections import OrderedDict
from style import read_colors, read_styles
from spot import Spot
from pawn import Pawn
from card import load_cards


logger = logging.getLogger(__name__)


def noop(*args, **kwargs):
    """Do nothing."""
    pass

ITEM_RE = re.compile("(.*)\.(.*)")
MAKE_SPOT_RE = re.compile(
    "make_spot\(([a-zA-Z0-9]+)\."
    "([a-zA-Z0-9]+),([0-9]+),([0-9]+),?([a-zA-Z0-9]*)\)")
MAKE_PORTAL_RE = re.compile(
    "make_portal\(([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)->"
    "([a-zA-Z0-9]+)\.([a-zA-Z0-9]+)\)")
THING_INTO_PORTAL_RE = re.compile("(.*)\.(.*)->Portal\((.*)->(.*)\)")


class RumorMill:
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

    def __init__(self, dbfilen, xfuncs={}):
        """Return a database wrapper around the SQLite database file by the given name.

Optional argument xfuncs is a dictionary of functions, with strings
for keys. They should take only one argument, also a string. Effects
will be able to call those functions with arbitrary string
arguments.

        """
        self.conn = sqlite3.connect(dbfilen)
        self.cursor = self.conn.cursor()
        self.c = self.cursor
        self.handdict = {}
        self.handcarddict = {}
        self.boardhanddict = {}
        self.carddict = {}
        self.dimensiondict = {}
        self.caldict = {}
        self.calcoldict = OrderedDict()
        self.edgedict = {}
        self.scheduledict = {}
        self.eventdict = {}
        self.startevdict = {}
        self.contevdict = {}
        self.endevdict = {}
        self.itemdict = {}
        self.placedict = {}
        self.hi_place = 0
        self.thingdict = {}
        self.spotdict = {}
        self.imgdict = {}
        self.boarddict = {}
        self.menudict = {}
        self.menuitemdict = {}
        self.pawndict = {}
        self.styledict = {}
        self.colordict = {}
        self.journeydict = {}
        self.contentsdict = {}
        self.locdict = {}
        self.portalorigdestdict = {}
        self.portaldestorigdict = {}
        self.effectdict = {}
        self.effectdeckdict = {}
        self.stringdict = {}
        self.func = {
            'toggle_menu':
            self.toggle_menu,
            'toggle_calendar':
            self.toggle_calendar,
            'hide_menu':
            self.hide_menu,
            'hide_calendar':
            self.hide_calendar,
            'show_menu':
            self.show_menu,
            'show_calendar':
            self.show_calendar,
            'hide_menus_in_board':
            self.hide_menus_in_board,
            'hide_calendars_in_board':
            self.hide_calendars_in_board,
            'hide_other_menus_in_board':
            self.hide_other_menus_in_board,
            'hide_other_calendars_in_board':
            self.hide_other_calendars_in_board,
            'thing_into_portal':
            self.thing_into_portal,
            'thing_along_portal':
            self.thing_along_portal,
            'thing_out_of_portal':
            self.thing_out_of_portal,
            'start_new_map': noop,
            'open_map': noop,
            'save_map': noop,
            'quit_map_editor': noop,
            'editor_select': noop,
            'editor_copy': noop,
            'editor_paste': noop,
            'editor_delete': noop,
            'mi_create_place':
            self.mi_create_place,
            'create_place':
            self.create_place,
            'create_generic_place':
            self.create_generic_place,
            'mi_create_thing':
            self.mi_create_thing,
            'create_thing':
            self.create_thing,
            'create_portal':
            self.create_portal,
            'mi_create_portal':
            self.mi_create_portal}
        self.func.update(xfuncs)

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
        return dimension.load_dimensions(self, dimname)

    def load_dimension(self, dimname):
        """Load and return the dimension with the given name."""
        return self.load_dimensions([dimname])[0]

    def load_boards(self, dimname):
        """Load the boards representing the named dimensions. Return them in a
list.

        """
        return board.load_boards(self, dimname)

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

    def make_place(self, arg, effect=None, deck=None, event=None):
        """Return a new Place object by the given name, in the given
dimension.

Argument is like:

dimension.place
        """
        mat = re.match(MAKE_PLACE_RE, arg)
        (dimension, name) = mat.groups()
        return self.create_place(dimension, name)

    def create_place(self, dimension, name):
        pl = item.Place(self, dimension, name)
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


    def create_spot(self, arg, effect=None, deck=None, event=None):
        """Return a Spot at the given coordinates, representing the place by
the given name in the given dimension.

Argument is like:
        dimension.place,x,y,img

place: The name of the place represented by this spot.
dimension: The dimension the place is in.
x,y: Coordinates on the board (not necessarily the screen).
img: The name of the image. May be omitted, in which case default_spot is used.

If the place does not exist, it will be created.
        """
        mat = re.match(MAKE_SPOT_RE, arg)
        (dimension, place, x, y, img) = mat.groups()
        return self.create_spot(dimension, place, x, y, img)

    def make_spot(self, dimension, place, x, y, img=None):
        if dimension not in self.placedict or place not in self.placedict[dimension]:
            self.make_place("{0}.{1}".format(dimension, place))
        sp = Spot(self, dimension, place, img, x, y)
        sp.unravel()
        sp.save()
        return sp

    def pawns_on_spot(self, spot):
        """Return a list of pawns on the given spot."""
        return [thing.pawn for thing in
                spot.place.contents
                if thing.name in self.pawndict[spot.dimension]]

    def create_thing(self, arg, effect=None, deck=None, event=None):
        """Return a new Thing in the given location of the given dimension, by
the given name.

Argument is like:
        dimension.thing@location

thing: The name of the thing you want to make.
dimension: The name of the dimension it should go in.
location: The name of a place in that dimension.

        """
        mat = re.match(MAKE_PLACE_RE, arg)
        (dimension, name, location) = mat.groups()
        return self.create_thing(dimension, name, location)

    def make_thing(self, dimension, name, location):
        th = Thing(dimension, name, location)
        th.unravel()
        th.save()
        return th

    def create_pawn(self, arg, effect=None, deck=None, event=None):
        """Return a new Pawn on the board for the named Dimension representing
the named Thing with the named Img.

Argument is like:
        dimension.thing,img
thing: The thing that the pawn represents.
dimension: The name of the dimension the thing is in.
img: The image that the pawn should display.

Pawns are placed automatically to reflect the location of the underlying thing object.

Raises a KeyError if the underlying Thing hasn't been created.
"""
        mat = re.match(PAWN_RE, arg)
        (dimension, thing, img) = mat.groups()
        return self.make_pawn(dimension, thing, img)

    def make_pawn(self, dimension, thing, img):
        pwn = Pawn(self, dimension, thing, img)
        pwn.unravel()
        pwn.save()
        return pwn

    def create_portal(self, arg, effect=None, deck=None, event=None):
        """Return a new Portal connecting the given origin and destination in
the given dimension.

Argument is like:
        dimension.origin->destination
origin, destination: names of two places to be connected.
dimension: The name of the dimension that both places are in.
        """
        mat = re.match(MAKE_PORTAL_RE, arg)
        (dimension, origin, destination) = mat.groups()
        return self.make_portal(dimension, origin, destination)

    def make_portal(self, dimension, origin, destination):
        port = item.Portal(self, dimension, origin, destination)
        port.unravel()
        port.save()
        return port

    def toggle_menu(self, menuitem, menu):
        boardname = str(menuitem.board)
        menuname = str(menu)
        self.hide_other_menus_in_board(boardname, menuname)
        self.menudict[boardname][menuname].toggle_visibility()

    def toggle_calendar(self, menuitem, cal):
        boardname = str(menuitem.board)
        calname = str(cal)
        self.hide_other_calendars_in_board(boardname, calname)
        self.calendardict[boardname][calname].toggle_visibility()

    def hide_menu(self, menuitem, menuname):
        """A callback for MenuItem. Hide the menu of the given name, in the
same board as the caller."""
        boardname = str(menuitem.board)
        self.menudict[boardname][menuname].hide()

    def hide_calendar(self, menuitem, calname):
        boardname = str(menuitem.board)
        self.calendardict[boardname][calname].hide()

    def show_menu(self, menuitem, menuname):
        """A callback for MenuItem. Show the menu of the given name, in the
same board as the caller."""
        boardname = str(menuitem.board)
        self.menudict[boardname][menuname].show()

    def show_calendar(self, menuitem, calname):
        boardname = str(menuitem.board)
        self.calendardict[boardname][calname].show()

    def hide_menus_in_board(self, board):
        boardn = str(board)
        for menu in self.menudict[boardn].itervalues():
            if not menu.main_for_window:
                menu.hide()

    def hide_other_menus_in_board(self, board, menu):
        boardn = str(board)
        menun = str(menu)
        for menu in self.menudict[boardn].itervalues():
            if not menu.main_for_window and menu.name != menun:
                menu.hide()

    def hide_calendars_in_board(self, board):
        boardn = str(board)
        for calendar in self.calendardict[boardn].itervalues():
            calendar.hide()

    def hide_other_calendars_in_board(self, board, calendar):
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
        if not hasattr(self, 'game'):
            self.load_game()
        return self.game[1]

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
        self.game = self.c.fetchone()
        self.lang = lang
        self.load_strings()
        self.load_board(self.game[0])

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

    def thing_into_portal(self, arg, effect=None, deck=None, event=None):
        """Put the item into the portal.

Argument is a mere string, structured as so:

dimension.item->portal

All of these are the names of their referents, and will be looked up
in the appropriate dictionary.

        """
        rex = THING_INTO_PORTAL_RE
        (dimname, itname, orig, dest) = re.match(rex, arg).groups()
        thing = self.thingdict[dimname][itname]
        portal = self.portalorigdestdict[dimname][orig][dest]
        thing.enter(portal)

    def thing_along_portal(self, arg, effect=None, deck=None, event=None):
        """Move the thing some amount along the portal it's in.

Argument is a mere string, structured like:

dimension.item

The given item in the given dimension will be moved along the portal
some amount, calculated by its speed_thru method.

        """
        rex = ITEM_RE
        (dimname, thingname) = re.match(rex, arg).groups()
        thing = self.thingdict[dimname][thingname]
        journey = thing.journey
        portal = journey[0]
        speed = thing.speed_thru(portal)
        journey.move_thing(speed)
        return (effect, thing, portal, speed, None)

    def thing_out_of_portal(self, arg, effect=None, deck=None, event=None):
        """Take the thing out of the portal it's in, and put it in the
portal's destination.

Argument is a string like:

dimension.item

The given item in the given dimension will be moved to the portal's
destination.

        """
        rex = ITEM_RE
        (dimname, thingname) = re.match(rex, arg).groups()
        thing = self.thingdict[dimname][thingname]
        (newplace, newport) = thing.journey.step()
        return (effect, newplace, newport, None)

    def create_generic_place(self, arg, effect=None, deck=None, event=None):
        """Take the name of a dimension and return a place in it with a boring name."""
        return self.make_generic_place(arg)

    def make_generic_place(self, dimension):
        placename = "Place_{0}".format(self.hi_place + 1)
        place = item.Place(self, dimension, placename)
        place.unravel()
        place.save()
        return place

    def mi_create_place(self, menuitem, arg):
        return menuitem.gw.create_place()

    def mi_create_thing(self, menuitem, arg):
        return menuitem.gw.create_thing()

    def mi_create_portal(self, menuitem, arg):
        return menuitem.gw.create_portal()

    def load_cards(self, names):
        load_cards(self, names)

    def load_card(self, name):
        load_card(self, [name])

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
        """Return the Style by the given name, loading it first if necessary."""
        if name not in self.styledict:
            self.load_styles(name)
        return self.styledict[name]


def load_game(dbfilen, language):
    """Load the game in the database file by the given name. Load strings
for the given language. Return a RumorMill object.

    """
    db = RumorMill(dbfilen)
    db.load_game(language)
    return db
