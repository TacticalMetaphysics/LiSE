import pyglet

class PatternHolder:
    """Takes a style and makes pyglet.image.SolidColorImagePatterns out of
its four colors, accessible through the attributes bg_active,
bg_inactive, fg_active, and fg_inactive."""
    def __init__(self, sty):
        self.bg_inactive = pyglet.image.SolidColorImagePattern(sty.bg_inactive.tup)
        self.bg_active = pyglet.image.SolidColorImagePattern(sty.bg_active.tup)
        self.fg_inactive = pyglet.image.SolidColorImagePattern(sty.fg_inactive.tup)
        self.fg_active = pyglet.image.SolidColorImagePattern(sty.fg_active.tup)

class DictValues2DIterator:
    def __init__(self, d):
        self.d = d
        self.layer1 = self.d.itervalues()
        self.layer2 = None

    def __iter__(self):
        return self

    def next(self):
        try:
            return self.layer2.next()
        except (AttributeError, TypeError, StopIteration):
            try:
                self.layer2 = self.layer1.next().itervalues()
                return self.layer2.next()
            except StopIteration:
                raise StopIteration


class DictWrapper2D:
    def __init__(self, d):
        self.d = d

    def __getattr__(self, attrn):
        return getattr(self.d, attrn)

    def itervalues(self):
        return DictValues2DIterator(self.d)


class LocationException(Exception):
    pass


class ContainmentException(Exception):
    """Exception raised when a Thing tried to go into or out of another
Thing, and it made no sense.

    """
    pass


class PortalException(Exception):
    """Exception raised when a Thing tried to move into or out of or along
a Portal, and it made no sense."""
    pass


schemata = set()


class SaveableMetaclass(type):
    """Sort of an object relational mapper.

Classes with this metaclass need to be declared with an attribute
called tables. This is a sequence of tuples. Each of the tuples is of
length 5. Each describes a table that records what's in the class.

The meaning of each tuple is thus:

(name, column_declarations, primary_key, foreign_keys, checks)

name is the name of the table as sqlite3 will use it.

column_declarations is a dictionary. The keys are field names, aka
column names. Each value is the type for its field, perhaps including
a clause like DEFAULT 0.

primary_key is an iterable over strings that are column names as
declared in the previous argument. Together the columns so named form
the primary key for this table.

foreign_keys is a dictionary. Each foreign key is a key here, and its
value is a pair. The first element of the pair is the foreign table
that the foreign key refers to. The second element is the field or
fields in that table that the foreign key points to.

checks is an iterable over strings that will end up in a CHECK(...)
clause in sqlite3.

A class can have any number of such table-tuples. The tables will be
declared in the order they appear in the tables attribute.

To save, you need to define a method called get_tabdict. It should
return a dictionary where the keys are table names. The values are
either rowdicts or iterables over rowdicts. A rowdict is a dictionary
containing the information in a single record of a table; the keys are
the names of the fields.

To load, you need to define a method called from_tabdict that takes
that same kind of dictionary and returns an instance of your class.

Once you've defined those, the save(db) and load(db) methods will save
or load your class in the given database. If you need to create the
database, look at the schemata attribute: execute that in a SQL cursor
and your table will be ready.

    """
    def __new__(metaclass, clas, parents, attrs):
        if clas in parents:
            return clas
        tablenames = []
        primarykeys = {}
        foreignkeys = {}
        coldecls = {}
        checks = {}
        if 'tables' in attrs:
            tablist = attrs['tables']
        elif hasattr(clas, 'tables'):
            tablist = clas.tables
        else:
            for par in parents:
                if hasattr(par, 'tables'):
                    tablist = par.tables
                    break
            assert(tablist is not None)
        for tabtup in tablist:
            (name, decls, pkey, fkeys, cks) = tabtup
            tablenames.append(name)
            coldecls[name] = decls
            primarykeys[name] = pkey
            foreignkeys[name] = fkeys
            checks[name] = cks
        inserts = {}
        deletes = {}
        detects = {}
        missings = {}
        keylen = {}
        rowlen = {}
        keyqms = {}
        rowqms = {}
        keystrs = {}
        rowstrs = {}
        keynames = {}
        valnames = {}
        colnames = {}
        colnamestr = {}
        for item in primarykeys.iteritems():
            (tablename, pkey) = item
            keynames[tablename] = sorted(pkey)
            keylen[tablename] = len(pkey)
            keyqms[tablename] = ", ".join(["?"] * keylen[tablename])
            keystrs[tablename] = "(" + keyqms[tablename] + ")"
        for item in coldecls.iteritems():
            (tablename, coldict) = item
            valnames[tablename] = sorted(
                [key for key in coldict.keys()
                 if key not in keynames[tablename]])
            rowlen[tablename] = len(coldict)
            rowqms[tablename] = ", ".join(["?"] * rowlen[tablename])
            rowstrs[tablename] = "(" + rowqms[tablename] + ")"
        for tablename in coldecls.iterkeys():
            colnames[tablename] = keynames[tablename] + valnames[tablename]
        for tablename in tablenames:
            coldecl = coldecls[tablename]
            pkey = primarykeys[tablename]
            fkeys = foreignkeys[tablename]
            cks = ["CHECK(%s)" % ck for ck in checks[tablename]]
            pkeydecs = [keyname + " " + typ
                        for (keyname, typ) in coldecl.iteritems()
                        if keyname in pkey]
            valdecs = [valname + " " + typ
                       for (valname, typ) in coldecl.iteritems()
                       if valname not in pkey]
            coldecs = sorted(pkeydecs) + sorted(valdecs)
            coldecstr = ", ".join(coldecs)
            pkeycolstr = ", ".join(pkey)
            pkeys = [keyname for (keyname, typ) in coldecl.iteritems()
                     if keyname in pkey]
            pkeynamestr = ", ".join(sorted(pkeys))
            vals = [valname for (valname, typ) in coldecl.iteritems()
                    if valname not in pkey]
            colnamestr[tablename] = ", ".join(sorted(pkeys) + sorted(vals))
            pkeystr = "PRIMARY KEY (%s)" % (pkeycolstr,)
            fkeystrs = ["FOREIGN KEY (%s) REFERENCES %s(%s)" %
                        (item[0], item[1][0], item[1][1])
                        for item in fkeys.iteritems()]
            fkeystr = ", ".join(fkeystrs)
            chkstr = ", ".join(cks)
            table_decl_data = [coldecstr]
            if len(pkey) > 0:
                table_decl_data.append(pkeystr)
            if len(fkeystrs) > 0:
                table_decl_data.append(fkeystr)
            if len(cks) > 0:
                table_decl_data.append(chkstr)
            table_decl = ", ".join(table_decl_data)
            create_stmt = "CREATE TABLE %s (%s);" % (tablename, table_decl)
            insert_stmt_start = ("INSERT INTO " + tablename +
                                 " ({0}) VALUES {1};")
            inserts[tablename] = insert_stmt_start
            delete_stmt_start = "DELETE FROM %s WHERE (%s) IN " % (
                tablename, pkeycolstr)
            deletes[tablename] = delete_stmt_start
            detect_stmt_start = "SELECT %s FROM %s WHERE (%s) IN " % (
                colnamestr[tablename], tablename, pkeynamestr)
            detects[tablename] = detect_stmt_start
            missing_stmt_start = "SELECT %s FROM %s WHERE (%s) NOT IN " % (
                colnamestr[tablename], tablename, pkeynamestr)
            missings[tablename] = missing_stmt_start
            schemata.add(create_stmt)

        def insert_rowdicts_table(db, rowdicts, tabname):
            sample = rowdicts[0]
            cols_used = [col for col in colnames[tabname] if col in sample]
            colsstr = ", ".join(cols_used)
            row_qms = ", ".join(["?"] * len(sample))
            rowstr = "({0})".format(row_qms)
            rowsstr = ", ".join([rowstr] * len(rowdicts))
            qrystr = inserts[tabname].format(colsstr, rowsstr)
            qrylst = []
            for rowdict in rowdicts:
                for col in cols_used:
                    qrylst.append(rowdict[col])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return []

        def delete_keydicts_table(db, keydicts, tabname):
            keyns = keynames[tabname]
            keys = []
            wheres = []
            for keydict in keydicts:
                checks = []
                for keyn in keyns:
                    checks.append(keyn + "=?")
                    keys.append(keydict[keyn])
                wheres.append("(" + " AND ".join(checks) + ")")
            wherestr = " OR ".join(wheres)
            qrystr = "DELETE FROM {0} WHERE {1}".format(tabname, wherestr)
            db.c.execute(qrystr, tuple(keys))

        def detect_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = detects[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                for col in keynames[tabname]:
                    if col in keydict:
                        qrylst.append(keydict[col])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return db.c.fetchall()

        def missing_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = missings[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                for col in keynames[tabname]:
                    if col in keydict:
                        qrylst.append(keydict[col])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return db.c.fetchall()

        def insert_tabdict(db, tabdict):
            for item in tabdict.iteritems():
                (tabname, rd) = item
                if isinstance(rd, dict):
                    insert_rowdicts_table(db, [rd], tabname)
                else:
                    insert_rowdicts_table(db, rd, tabname)

        def delete_tabdict(db, tabdict):
            for item in tabdict.iteritems():
                (tabname, rd) = item
                if isinstance(rd, dict):
                    delete_keydicts_table(db, [rd], tabname)
                else:
                    delete_keydicts_table(db, rd, tabname)

        def detect_tabdict(db, tabdict):
            r = {}
            for item in tabdict.iteritems():
                (tabname, rd) = item
                if isinstance(rd, dict):
                    r[tabname] = detect_keydicts_table(db, [rd], tabname)
                else:
                    r[tabname] = detect_keydicts_table(db, rd, tabname)
            return r

        def missing_tabdict(db, tabdict):
            r = {}
            for item in tabdict.iteritems():
                (tabname, rd) = item
                if isinstance(rd, dict):
                    r[tabname] = missing_keydicts_table(db, [rd], tabname)
                else:
                    r[tabname] = missing_keydicts_table(db, rd, tabname)
            return r

        def mkrow(self, tabn=None, rowdict=None):
            if tabn is None:
                tabn = self.maintab
            if rowdict is None:
                rowdict = self.get_rowdict(tabn)
            r = []
            for coln in self.colnames[tabn]:
                r.append(rowdict[coln])
            return tuple(r)

        def mkrowdict(self, tabname):
            # Invariant: For the named table, I have attributes named
            # and typed the same way as the columns.
            r = {}
            for colname in self.colnames[tabname]:
                if getattr(self, colname).__class__ in (int, float, bool):
                    r[colname] = getattr(self, colname)
                else:
                    r[colname] = str(getattr(self, colname))
            return r

        def mktabdict(self):
            r = {}
            for tabname in tablenames:
                r[tabname] = mkrowdict(self, tabname)
            return r

        def save(self, db=None):
            if db is None:
                db = self.db
            td = self.get_tabdict()
            delete_tabdict(db, td)
            insert_tabdict(db, td)

        dbop = {'insert': insert_tabdict,
                'delete': delete_tabdict,
                'detect': detect_tabdict,
                'missing': missing_tabdict}
        atrdic = {'colnames': colnames,
                  'colnamestr': colnamestr,
                  'colnstr': colnamestr[tablenames[0]],
                  'keynames': keynames,
                  'valnames': valnames,
                  'keyns': keynames[tablenames[0]],
                  'valns': valnames[tablenames[0]],
                  'colns': colnames[tablenames[0]],
                  'schemata': schemata,
                  'keylen': keylen,
                  'rowlen': rowlen,
                  'keyqms': keyqms,
                  'rowqms': rowqms,
                  'dbop': dbop,
                  'get_row': mkrow,
                  'get_tabdict': mktabdict,
                  'save': save,
                  'maintab': tablenames[0]}
        atrdic.update(attrs)

        return type.__new__(metaclass, clas, parents, atrdic)


def start_new_map(nope):
    pass


def open_map(nope):
    pass


def save_map(nope):
    pass


def quit_map_editor(nope):
    pass


def editor_select(nope):
    pass


def editor_copy(nope):
    pass


def editor_paste(nope):
    pass


def editor_delete(nope):
    pass


def new_place(place_type):
    pass


def new_thing(thing_type):
    pass


funcs = [start_new_map, open_map, save_map, quit_map_editor, editor_select,
         editor_copy, editor_paste, editor_delete, new_place, new_thing]


def mkitemd(dimension, name):
    return {'dimension': dimension,
            'name': name}


def reciprocate(porttup):
    return (porttup[1], porttup[0])


def reciprocate_all(porttups):
    return [reciprocate(port) for port in porttups]


def reciprocal_pairs(pairs):
    return pairs + [reciprocate(pair) for pair in pairs]


def mkportald(dimension, orig, dest):
    return {'dimension': dimension,
            'name': "portal[%s->%s]" % (orig, dest),
            'from_place': orig,
            'to_place': dest}


def mklocd(dimension, thing, place):
    return {'dimension': dimension,
            'thing': thing,
            'place': place}


def mkstepd(dimension, thing, idx, portal):
    return {"dimension": dimension,
            "thing": thing,
            "idx": idx,
            "portal": portal}


def translate_color(name, rgb):
    return {
        'name': name,
        'red': rgb[0],
        'green': rgb[1],
        'blue': rgb[2],
        'alpha': 255}


def mkcontd(dimension, contained, container):
    # I have not made any containments yet
    return {"dimension": dimension,
            "contained": contained,
            "container": container}


def mkjourneyd(thing):
    return {"dimension": "Physical",
            "thing": thing,
            "curstep": 0,
            "progress": 0.0}


def mkboardd(dimension, width, height, wallpaper):
    return {"dimension": dimension,
            "width": width,
            "height": height,
            "wallpaper": wallpaper}


def mkboardmenud(board, menu):
    return {"board": board,
            "menu": menu}


def mkimgd(name, path, rltile):
    return {"name": name,
            "path": path,
            "rltile": rltile}


def mkspotd(dimension, place, img, x, y, visible, interactive):
    return {"dimension": dimension,
            "place": place,
            "img": img,
            "x": x,
            "y": y,
            "visible": visible,
            "interactive": interactive}


def mkpawnd(dimension, thing, img, visible, interactive):
    return {"dimension": dimension,
            "thing": thing,
            "img": img,
            "visible": visible,
            "interactive": interactive}


def mkstyled(name, fontface, fontsize, spacing,
             bg_inactive, bg_active,
             fg_inactive, fg_active):
    return {'name': name,
            'fontface': fontface,
            'fontsize': fontsize,
            'spacing': spacing,
            'bg_inactive': bg_inactive,
            'bg_active': bg_active,
            'fg_inactive': fg_inactive,
            'fg_active': fg_active}


def untuple(list_o_tups):
    r = []
    for tup in list_o_tups:
        for val in tup:
            r.append(val)
    return r


def dictify_row(row, colnames):
    return dict(zip(colnames, row))


def dictify_rows(rows, keynames, colnames):
    # Produce a dictionary with which to look up rows--but rows that
    # have themselves been turned into dictionaries.
    r = {}
    # Start this dictionary with empty dicts, deep enough to hold
    # all the partial keys in keynames and then a value.
    # I think this fills deeper than necessary?
    keys = len(keynames)  # use this many fields as keys
    for row in rows:
        ptr = r
        i = 0
        while i < keys:
            i += 1
            try:
                ptr = ptr[row[i]]
            except:
                ptr = {}
        # Now ptr points to the dict of the last key that doesn't get
        # a dictified row. i is one beyond that.
        ptr[row[i]] = dictify_row(row)
    return r


def dicl2tupl(dicl):
    # Converts list of dicts with one set of keys to list of tuples of
    # *values only*, not keys. They'll be in the same order as given
    # by dict.keys().
    keys = dicl[0].keys()
    r = []
    for dic in dicl:
        l = [dic[k] for k in keys]
        r.append(tuple(l))
    return r


def deep_lookup(dic, keylst):
    key = keylst.pop()
    ptr = dic
    while keylst != []:
        ptr = ptr[key]
        key = keylst.pop()
    return ptr[key]


def compile_tabdicts(objs):
    tabdicts = [o.tabdict for o in objs]
    mastertab = {}
    for tabdict in tabdicts:
        for item in tabdict.iteritems():
            (tabname, rowdict) = item
            if tabname not in mastertab:
                mastertab[tabname] = []
            mastertab[tabname].append(rowdict)
    return mastertab


def stringlike(o):
    """Return True if I can easily cast this into a string, False
otherwise."""
    return isinstance(o, str) or isinstance(o, unicode)
