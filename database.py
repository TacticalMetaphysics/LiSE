import sqlite3
import board
import dimension
from util import compile_tabdicts


class Database:
    def __init__(self, dbfile):
        self.conn = sqlite3.connect(dbfile)
        self.c = self.conn.cursor()
        self.altered = set()
        self.removed = set()
        self.dimensiondict = {}
        self.calendardict = {}
        self.scheduledict = {}
        self.itemdict = {}
        self.spotdict = {}
        self.imgdict = {}
        self.boarddict = {}
        self.menudict = {}
        self.menuitemdict = {}
        self.boardmenudict = {}
        self.pawndict = {}
        self.styledict = {}
        self.colordict = {}
        self.journeydict = {}
        self.contentsdict = {}
        self.containerdict = {}
        self.placecontentsdict = {}
        self.portalorigdestdict = {}
        self.portaldestorigdict = {}
        self.func = {'toggle_menu_visibility': self.toggle_menu_visibility}

    def __del__(self):
        self.c.close()
        self.conn.commit()
        self.conn.close()

    def insert_rowdict_table(self, rowdict, clas, tablename):
        if rowdict != []:
            clas.dbop['insert'](self, rowdict, tablename)

    def delete_keydict_table(self, keydict, clas, tablename):
        if keydict != []:
            clas.dbop['delete'](self, keydict, tablename)

    def detect_keydict_table(self, keydict, clas, tablename):
        if keydict != []:
            return clas.dbop['detect'](self, keydict, tablename)
        else:
            return []

    def missing_keydict_table(self, keydict, clas, tablename):
        if keydict != []:
            return clas.dbop['missing'](self, keydict, tablename)
        else:
            return []

    def insert_obj_table(self, obj, tablename):
        if isinstance(obj, list):
            objs = obj
        else:
            objs = [obj]
        rowdicts = [o.tabdict[tablename] for o in objs]
        self.insert_rowdict_table(rowdicts, objs[0], tablename)

    def delete_obj_table(self, obj, tablename):
        if isinstance(obj, list):
            objs = obj
        else:
            objs = [obj]
        rowdicts = [o.tabdict[tablename] for o in objs]
        self.delete_keydict_table(rowdicts, objs[0], tablename)

    def detect_obj_table(self, obj, tablename):
        if isinstance(obj, list):
            objs = obj
        else:
            objs = [obj]
        rowdicts = [o.tabdict[tablename] for o in objs]
        return self.detect_keydict_table(rowdicts, objs[0], tablename)

    def missing_obj_table(self, obj, tablename):
        if isinstance(obj, list):
            objs = obj
        else:
            objs = [obj]
        rowdicts = [o.tabdict[tablename] for o in objs]
        return self.missing_keydict_table(rowdicts, objs[0], tablename)

    def insert_obj(self, obj):
        if isinstance(obj, list):
            objs = obj
        else:
            objs = [obj]
        clas = objs[0].__class__
        mastertab = compile_tabdicts(objs)
        for tabname in mastertab.iterkeys():
            self.insert_rowdict_table(mastertab[tabname], clas, tabname)

    def delete_obj(self, obj):
        if isinstance(obj, list):
            objs = obj
        else:
            objs = [obj]
        clas = objs[0].__class__
        mastertab = compile_tabdicts(objs)
        for tabname in mastertab.iterkeys():
            self.delete_keydict_table(mastertab[tabname], clas, tabname)

    def detect_obj(self, obj):
        if isinstance(obj, list):
            objs = obj
        else:
            objs = [obj]
        clas = objs[0].__class__
        mastertab = compile_tabdicts(objs)
        r = []
        for tabname in mastertab.iterkeys():
            r.extend(self.detect_keydict_table(
                mastertab[tabname], clas, tabname))
        return r

    def missing_obj(self, obj):
        if isinstance(obj, list):
            objs = obj
        else:
            objs = [obj]
        clas = objs[0].__class__
        mastertab = compile_tabdicts(objs)
        r = []
        for tabname in mastertab.iterkeys():
            r.extend(self.missing_keydict_table(
                mastertab[tabname], clas, tabname))
        return r

    def mkschema(self, table_classes):
        for clas in table_classes:
            for tab in clas.schemata:
                self.c.execute(tab)
        self.conn.commit()

    def xfunc(self, func):
        self.func[func.__name__] = func

    def call_func(self, fname, farg):
        return self.func[fname](farg)

    def load_dimensions(self, dimname):
        return dimension.load_dimensions(self, dimname)

    def load_dimension(self, dimname):
        return self.load_dimensions([dimname])

    def load_boards(self, dimname):
        return board.load_boards(self, dimname)

    def load_board(self, dimname):
        return self.load_boards([dimname])

    def toggle_menu_visibility(self, stringly):
        """Given a string arg of the form boardname.menuname, toggle the
visibility of the given menu on the given board.

"""
        splot = stringly.split('.')
        if len(splot) == 1:
            # I only got the menu name.
            # Maybe I've gotten an appropriate xfunc for that?
            if "toggle_menu_visibility_by_name" in self.func:
                return self.func["toggle_menu_visibility_by_name"](stringly)
            # I might be able to find the right menu object anyhow: if
            # there's only one by that name, toggle it.
            menuname = splot[0]
            menu = None
            for boardmenu in self.boardmenudict.itervalues():
                for boardmenuitem in boardmenu.iteritems():
                    if boardmenuitem[0] == menuname:
                        if menu is None:
                            menu = boardmenuitem[1]
                        else:
                            raise Exception("Unable to disambiguate"
                                            "the menu identifier: " + stringly)
            menu.toggle_visibility()
        else:
            # Nice. Toggle that.
            (boardname, menuname) = splot
            self.boardmenudict[boardname][menuname].toggle_visibility()

    def remember(self, obj):
        self.altered.add(obj)

    def forget(self, obj):
        self.removed.add(obj)

    def sync(self):
        """Write all altered objects to disk. Delete all deleted objects from
disk.

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
            (item[0], list(item[1])) for item in unknownobjs.iteritems]
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
        dim = place.dimension
        pname = place.name
        pcd = self.placecontentsdict
        if dim not in pcd or pname not in pcd[dim]:
            return []
        thingnames = self.placecontentsdict[dim][pname]
        return [self.itemdict[dim][name] for name in thingnames]

    def pawns_on_spot(self, spot):
        return [thing.pawn for thing in
                spot.place.contents
                if thing.name in self.pawndict[spot.dimension]]

    def inverse_portal(self, portal):
        orign = portal.orig.name
        destn = portal.dest.name
        pdod = self.portaldestorigdict[portal.dimension]
        try:
            return pdod[orign][destn]
        except:
            return None
