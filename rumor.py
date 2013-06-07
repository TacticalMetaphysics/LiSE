import sqlite3
import board
import dimension
import item
import re
from collections import OrderedDict
from style import read_colors
from spot import Spot
from pawn import Pawn


"""The database backend, with dictionaries of loaded objects.

This is a caching database connector. There are dictionaries for all
objects that can be loaded from the database.

This module does not contain the code used to generate
SQL. That's in util.py, the class SaveableMetaclass.

"""


def noop(*args, **kwargs):
    """Do nothing."""
    pass

ITEM_RE = re.compile("(.*)\.(.*)")
THING_INTO_PORTAL_RE = re.compile("(.*)\.(.*)->Portal\((.*)->(.*)\)")
THING_ALONG_PORTAL_RE = ITEM_RE
THING_OUT_OF_PORTAL_RE = ITEM_RE


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
        self.altered = set()
        self.removed = set()
        self.dimensiondict = {}
        self.caldict = {}
        self.calcoldict = OrderedDict()
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
            'toggle_menu_visibility':
            self.toggle_menu_visibility,
            'toggle_calendar_visibility':
            self.toggle_calendar_visibility,
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
            'new_place': noop,
            'new_thing': noop,
            'create_place':
            self.create_place,
            'create_generic_place':
            self.create_generic_place,
            'create_spot':
            self.create_spot}
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

    def gen_place(self, dimension, name, save=True, unravel=True):
        """Return a new Place object by the given name, in the given
dimension.

By default, it will be saved to the database immediately, and then
unraveled.

        """
        pl = item.Place(self, dimension, name)
        if save:
            item.save()
        if unravel:
            item.unravel()
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


    def gen_spot(self, dimension, place, x, y, img="default-spot",
                 save=True, unravel=True):
        """Return a Spot at the given coordinates, representing the place by
the given name in the given dimension.

It will use the image named 'default-spot' by default, and will be
visible and interactive. Also by default, it will be saved to the
database and unraveled. If the Place doesn't exist, it will be created with gen_place().

        """
        if dimension not in self.placedict or name not in self.placedict[dimension]:
            self.gen_place(dimension, place, save, unravel)
        sp = Spot(self, dimension, place, img, x, y, visible, interactive)
        if save:
            sp.save()
        if unravel:
            sp.unravel()
        return sp

    def pawns_on_spot(self, spot):
        """Return a list of pawns on the given spot."""
        return [thing.pawn for thing in
                spot.place.contents
                if thing.name in self.pawndict[spot.dimension]]

    def gen_thing(self, dimension, name, location, save=True, unravel=True):
        """Return a new Thing in the given location of the given dimension, by
the given name.

By default, it will be saved and unraveled.

        """
        th = Thing(dimension, name, location)
        if save:
            th.save()
        if unravel:
            th.unravel()
        return th

    def gen_pawn(self, dimension, thing, img,
                 save=True, unravel=True):
        """Return a new Pawn on the board for the named Dimension representing
the named Thing with the named Img.
        
Raises a KeyError if the underlying Thing hasn't been created. By
default, the Pawn will be saved and unraveled.

        """
        pwn = Pawn(self, dimension, thing, img)
        if save:
            pawn.save()
        if unravel:
            pawn.unravel()
        return pwn

    def gen_portal(self, dimension, origin, destination,
                   save=True, unravel=True):
        """Return a new Portal connecting the given origin and destination in
the given dimension.

By default, it will be saved and unraveled.

        """
        port = Portal(self, dimension, origin, destination)
        if save:
            port.save()
        if unravel:
            port.unravel()
        return port

    def toggle_menu_visibility(self, menuspec, evt=None):

        """Given a string consisting of a board name, a dot, and a menu name,
toggle the visibility of that menu.

        """
        (boardn, itn) = menuspec.split('.')
        self.menudict[boardn][itn].toggle_visibility()

    def toggle_calendar_visibility(self, calspec, evt=None):
        """Given a string consisting of a dimension name, a dot, and an item
name, toggle the visibility of the calendar representing the schedule
for that item."""
        (boardn, itn) = calspec.split('.')
        self.calendardict[boardn][itn].toggle_visibility()

    def hide_menu(self, menuspec, evt=None):
        """Given a string consisting of a board dimension name, a dot, and a
menu name, hide the menu in that board by that name."""
        (boardn, menun) = menuspec.split('.')
        self.menudict[boardn][menun].hide()

    def hide_calendar(self, calspec, evt=None):
        """Given a string consisting of a board dimension name, a dot, and an
item name, hide the calendar representing the schedule of that item in
that board."""
        (boardn, itn) = calspec.split('.')
        self.calendardict[boardn][itn].hide()

    def show_menu(self, menuspec, evt=None):
        """Given a string consisting of a board dimension name, a dot, and a
menu name, show the menu of that name in that board."""
        (boardn, menun) = menuspec.split('.')
        self.menudict[boardn][menun].show()

    def show_calendar(self, calspec, evt=None):
        """Given a string consisting of a board dimension name, a dot, and an
item name, show the calendar representing the item's schedule in that
board."""
        (boardn, itn) = calspec.split('.')
        self.calendardict[boardn][itn].show()

    def hide_menus_in_board(self, boardn, evt=None):
        """Hide every menu, apart from the main menu, in the board with the
given dimension name."""
        for menu in self.menudict[boardn].itervalues():
            if not menu.main_for_window:
                menu.hide()

    def hide_other_menus_in_board(self, menuspec, evt=None):
        """Given a string consisting of a board dimension name, a dot, and a
menu name, hide every menu apart from that one in that board, except
the main menu."""
        (boardn, menun) = menuspec.split('.')
        for menu in self.menudict[boardn].itervalues():
            if not menu.main_for_window and menu.name != menun:
                menu.hide()

    def hide_calendars_in_board(self, boardn, evt=None):
        """Hide every calendar in the board with the given dimension name."""
        for calendar in self.calendardict[boardn].itervalues():
            calendar.hide()

    def hide_other_calendars_in_board(self, calspec, evt=None):
        """Given a string consisting of a board dimension name, a dot, and an
item name, hide every calendar apart from that one in that board."""
        (boardn, itn) = calspec.split('.')
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

    def thing_into_portal(self, arg, evt):
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
        return thing.enter(portal)

    def thing_along_portal(self, arg, evt):
        """Move the thing some amount along the portal it's in.

Argument is a mere string, structured like:

dimension.item

The given item in the given dimension will be moved along the portal
some amount, calculated by its speed_thru method.

        """
        rex = THING_ALONG_PORTAL_RE
        (dimname, thingname) = re.match(rex, arg).groups()
        thing = self.thingdict[dimname][thingname]
        port = thing.location
        speed = thing.speed_thru(port)
        amount = 1 / float(speed)
        return thing.move_thru_portal(amount)

    def thing_out_of_portal(self, arg, evt):
        """Take the thing out of the portal it's in, and put it in the
portal's destination.

Argument is a string like:

dimension.item

The given item in the given dimension will be moved to the portal's
destination.

        """
        rex = THING_OUT_OF_PORTAL_RE
        (dimname, thingname) = re.match(rex, arg).groups()
        thing = self.thingdict[dimname][thingname]
        return thing.journey.next()

    def create_place(self, arg, evt):
        """Take a dotstring like dimension.place, and create that place.

This includes unraveling the place after creation but before return."""
        rex = ITEM_RE
        (dimname, placename) = re.match(rex, arg).groups()
        place = Place(self, dimname, placename)
        place.unravel()
        return place

    def create_generic_place(self, arg, evt):
        """Take the name of a dimension and return a place in it with a boring name."""
        placename = "Place_{0}".format(self.hi_place + 1)
        place = Place(self, arg, placename)
        place.unravel()
        return place

    def create_spot(self, arg, evt):
        """Create a spot with the default sprite representing some extant place.

The place is specified like dimension.placename"""
        rex = ITEM_RE
        (dimname, placename) = re.match(rex, arg).groups()
        spot = Spot(self, dimname, placename)
        spot.unravel()
        return spot


def load_game(dbfilen, language):
    """Load the game in the database file by the given name. Load strings
for the given language. Return a RumorMill object.

    """
    db = RumorMill(dbfilen)
    db.load_game(language)
    return db
