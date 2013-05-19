import sqlite3
import board
import dimension
from collections import OrderedDict


"""The database backend, with dictionaries of loaded objects.

This is a caching database connector. There are dictionaries for all
objects that can be loaded from the database.

This module does not contain the code used to generate
SQL. That's in util.py, the class SaveableMetaclass.

"""


def noop(nope):
    pass


class Database:
    """Container for an SQLite database connection.

You need to create a SQLite database file with the appropriate schema
before this will work. For that, run mkdb.py. You may want to insert
some test data with popdb.py.

The database container has various dictionary attributes. Normally
these hold objects loaded from the database, and have the same key as
the main table for that object class. Storing an object there does not
mean it will be saved. Mark objects to be saved by passing them to the
remember() method. It's best to do this for objects already saved
that you want to change, as well.

Call the sync() method to write remembered objects to disk. This
*should* be done automatically on destruction, but if, eg., the
program closes just after destruction, the garbage collector might not
have gotten around to finishing the job.

    """

    def __init__(self, dbfile, xfuncs={}):
        """Return a database wrapper around the given SQLite database file.

Optional argument xfuncs is a dictionary of functions, with strings
for keys. They should take only one argument, also a string. Effects
will be able to call those functions with arbitrary string
arguments.

        """
        self.conn = sqlite3.connect(dbfile)
        self.c = self.conn.cursor()
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
        self.portaldict = {}
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
        self.containerdict = {}
        self.placecontentsdict = {}
        self.portalorigdestdict = {}
        self.portaldestorigdict = {}
        self.effectdict = {}
        self.effectdeckdict = {}
        self.stringdict = {}
        self.func = {
            'toggle_menu_visibility': self.toggle_menu_visibility,
            'toggle_calendar_visibility': self.toggle_calendar_visibility,
            'hide_menu': self.hide_menu,
            'hide_calendar': self.hide_calendar,
            'show_menu': self.show_menu,
            'show_calendar': self.show_calendar,
            'hide_menus_in_board': self.hide_menus_in_board,
            'hide_calendars_in_board': self.hide_calendars_in_board,
            'hide_other_menus_in_board': self.hide_other_menus_in_board,
            'hide_other_calendars_in_board':
            self.hide_other_calendars_in_board,
            'start_new_map': noop,
            'open_map': noop,
            'save_map': noop,
            'quit_map_editor': noop,
            'editor_select': noop,
            'editor_copy': noop,
            'editor_paste': noop,
            'editor_delete': noop,
            'new_place': noop,
            'new_thing': noop}
        self.func.update(xfuncs)

    def __del__(self):
        """Try to write changes to disk before dying.

Python doesn't necessarily finish deleting all objects before
exiting. You'd probably better call self.sync() on your own before
then.

        """
        self.sync()
        self.c.close()
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

    def call_func(self, fname, farg):
        """Look up a function by its name in self.func, then call it with
argument farg.

Returns whatever that function does."""
        return self.func[fname](farg)

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

    def remember(self, obj):
        """Indicate that the object should be saved to disk on next sync."""
        self.altered.add(obj)
        self.removed.discard(obj)

    def forget(self, obj):
        """Indicate that the object should be deleted from disk on next
sync."""
        self.removed.add(obj)
        self.altered.discard(obj)

    def sync(self):

        """Write all remembered objects to disk. Delete all forgotten objects
from disk.

        """
        # Handle additions and changes first.
        #
        # To sort the objects into known, unknown, and changed, I'll
        # need to query all their tables with their respective
        # keys. To do that I need to group these objects according to
        # what table they go in.

        tabdict = {}
        for obj in iter(self.altered):
            if obj.tabname not in tabdict:
                tabdict[obj.tabname] = []
            tabdict[obj.tabname].append(obj)
        # get known objects for each table
        knowndict = {}
        for tabset in tabdict.iteritems():
            (tabname, objs) = tabset
            clas = objs[0].__class__
            keynames = clas.keynames
            qmstr = clas.keys_qm(len(objs))
            keystr = ", ".join(keynames)
            qrystr = "SELECT %s FROM %s WHERE (%s) IN (%s)" % (
                keystr, tabname, keystr, qmstr)
            keys = []
            for obj in objs:
                keys.extend([getattr(obj, keyname) for keyname in keynames])
            qrytup = tuple(keys)
            self.c.execute(qrystr, qrytup)
            knowndict[tabname] = self.c.fetchall()
        knownobjs = {}
        for item in knowndict.iteritems():
            (tabname, rows) = item
            knownobjs[tabname] = set(rows)
        # Get changed objects for each table. For this I need only
        # consider objects that are known.
        changeddict = {}
        for known in knownobjs.iteritems():
            (table, objs) = known
            clas = objs[0].__class__
            colnames = clas.colnames
            qmstr = clas.rows_qm(len(objs))
            colstr = ", ".join(colnames)
            qrystr = "SELECT %s FROM %s WHERE (%s) NOT IN (%s)" % (
                colstr, tabname, colstr, qmstr)
            cols = []
            for obj in objs:
                cols.extend([getattr(obj, colname) for colname in colnames])
            qrytup = tuple(cols)
            self.c.execute(qrystr, qrytup)
            changeddict[tabname] = self.c.fetchall()
        changedobjs = {}
        for item in changeddict.iteritems():
            (tabname, rows) = item
            # The objects represented here are going to be the same
            # kind as are always represented by this table, so grab
            # the keynames from knownobjs--they're the same
            keynames = knownobjs[tabname][0].keynames
            keylen = len(keynames)
            keys = [row[:keylen] for row in rows]
            objlst = [tabdict[tabname][key] for key in keys]
            changedobjs[tabname] = set(objlst)
        # I can find the unknown objects without touching the
        # database, using set differences
        tabsetdict = {}
        for item in tabdict.iteritems():
            if item[0] not in tabsetdict:
                tabsetdict[item[0]] = item[1].viewvalues()
        unknownobjs = {}
        for item in tabsetdict.iteritems():
            (table, objset) = item
            unknownobjs[table] = objset - unknownobjs[table]
        deletions_by_table = {}
        insertions_by_table = {}
        changel = [
            (item[0], list(item[1])) for item in changedobjs.iteritems()]
        # changel is pairs where the first item is the table name and
        # the last item is a list of objects changed in that table
        for pair in changel:
            (table, objs) = pair
            # invariant: all the objs are of the same class
            # list of tuples representing keys to delete
            dellst = [obj.key for obj in objs]
            deletions_by_table[table] = dellst
            # list of tuples representing rows to insert
            inslst = [obj.key + obj.val for obj in objs]
            insertions_by_table[table] = inslst
        newl = [
            (item[0], list(item[1])) for item in unknownobjs.iteritems()]
        for pair in newl:
            (table, objs) = pair
            inslst = [obj.key + obj.val for obj in objs]
            if table in insertions_by_table:
                insertions_by_table[table].extend(inslst)
            else:
                insertions_by_table[table] = inslst
        # Now handle things that have actually been deleted from the
        # world.
        #
        # If and when I get my own special-snowflake journal
        # system working, journal entries should not be included here.
        #
        # Invariant: No object is in both self.altered and self.removed.
        for obj in self.removed:
            deletions_by_table[obj.tabname].append(obj)
        # delete things to be changed, and things to be actually deleted
        for item in deletions_by_table.iteritems():
            (table, keys) = item
            keynamestr = ", ".join(keys[0].keynames)
            qmstr = keys[0].keys_qm(len(keys))
            keylst = []
            for key in keys:
                keylst.extend(key)
            qrystr = "DELETE FROM %s WHERE (%s) IN (%s)" % (
                table, keynamestr, qmstr)
            qrytup = tuple(keylst)
            self.c.execute(qrystr, qrytup)
        # insert things whether they're changed or new
        for item in insertions_by_table.iteritems():
            (table, rows) = item
            qmstr = rows[0].rows_qm(len(rows))
            vallst = []
            for row in rows:
                vallst.extend(row)
            qrystr = "INSERT INTO %s VALUES (%s)" % (
                table, qmstr)
            qrytup = tuple(vallst)
            self.c.execute(qrystr, qrytup)
        # that'll do.
        self.altered = set()
        self.removed = set()

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

    def inverse_portal(self, portal):
        """Return the portal whose origin is the given portal's destination
and vice-versa.

        """
        orign = portal.orig.name
        destn = portal.dest.name
        pdod = self.portaldestorigdict[portal.dimension]
        try:
            return pdod[orign][destn]
        except:
            return None

    def toggle_menu_visibility(self, menuspec):
        """Given a string consisting of a board name, a dot, and a menu name,
toggle the visibility of that menu.

        """
        (boardn, itn) = menuspec.split('.')
        self.menudict[boardn][itn].toggle_visibility()

    def toggle_calendar_visibility(self, calspec):
        """Given a string consisting of a dimension name, a dot, and an item
name, toggle the visibility of the calendar representing the schedule
for that item."""
        (boardn, itn) = calspec.split('.')
        self.calendardict[boardn][itn].toggle_visibility()

    def hide_menu(self, menuspec):
        """Given a string consisting of a board dimension name, a dot, and a
menu name, hide the menu in that board by that name."""
        (boardn, menun) = menuspec.split('.')
        self.menudict[boardn][menun].hide()

    def hide_calendar(self, calspec):
        """Given a string consisting of a board dimension name, a dot, and an
item name, hide the calendar representing the schedule of that item in
that board."""
        (boardn, itn) = calspec.split('.')
        self.calendardict[boardn][itn].hide()

    def show_menu(self, menuspec):
        """Given a string consisting of a board dimension name, a dot, and a
menu name, show the menu of that name in that board."""
        (boardn, menun) = menuspec.split('.')
        self.menudict[boardn][menun].show()

    def show_calendar(self, calspec):
        """Given a string consisting of a board dimension name, a dot, and an
item name, show the calendar representing the item's schedule in that
board."""
        (boardn, itn) = calspec.split('.')
        self.calendardict[boardn][itn].show()

    def hide_menus_in_board(self, boardn):
        """Hide every menu, apart from the main menu, in the board with the
given dimension name."""
        for menu in self.menudict[boardn].itervalues():
            if not menu.main_for_window:
                menu.hide()

    def hide_other_menus_in_board(self, menuspec):
        """Given a string consisting of a board dimension name, a dot, and a
menu name, hide every menu apart from that one in that board, except
the main menu."""
        (boardn, menun) = menuspec.split('.')
        for menu in self.menudict[boardn].itervalues():
            if not menu.main_for_window and menu.name != menun:
                menu.hide()

    def hide_calendars_in_board(self, boardn):
        """Hide every calendar in the board with the given dimension name."""
        for calendar in self.calendardict[boardn].itervalues():
            calendar.hide()

    def hide_other_calendars_in_board(self, calspec):
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
            (atstringn, lang, string) = row
            stringn = atstringn[1:]
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


def load_game(dbfilen, language):
    """Load the game in the given SQLite3 database file. Load strings for
the given language. Return a lise.Database object."""
    db = Database(dbfilen)
    db.load_game(language)
    return db
