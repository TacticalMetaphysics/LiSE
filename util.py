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


game_menu_items = {'New': ('start_new_map', None),
                   'Open': ('open_map', None),
                   'Save': ('save_map', None),
                   'Quit': ('quit_map_editor', None)}
editor_menu_items = {'Select': ('editor_select', None),
                     'Copy': ('editor_copy', None),
                     'Paste': ('editor_paste', None),
                     'Delete': ('editor_delete', None)}
place_menu_items = {'Custom Place': ('new_place', 'custom'),
                    'Workplace': ('new_place', 'workplace'),
                    'Commons': ('new_place', 'commons'),
                    'Lair': ('new_place', 'lair')}
thing_menu_items = {'Custom Thing': ('new_thing', 'custom'),
                    'Decoration': ('new_thing', 'decoration'),
                    'Clothing': ('new_thing', 'clothing'),
                    'Tool': ('new_thing', 'tool')}
main_menu_items = {'Game': ('toggle_menu_visibility', 'Game'),
                   'Editor': ('toggle_menu_visibility', 'Editor'),
                   'Place': ('toggle_menu_visibility', 'Place'),
                   'Thing': ('toggle_menu_visibility', 'Thing')}


solarized_colors = {'base03': (0x00, 0x2b, 0x36),
                    'base02': (0x07, 0x36, 0x42),
                    'base01': (0x58, 0x6e, 0x75),
                    'base00': (0x65, 0x7b, 0x83),
                    'base0': (0x83, 0x94, 0x96),
                    'base1': (0x93, 0xa1, 0xa1),
                    'base2': (0xee, 0xe8, 0xd5),
                    'base3': (0xfd, 0xf6, 0xe3),
                    'yellow': (0xb5, 0x89, 0x00),
                    'orange': (0xcb, 0x4b, 0x16),
                    'red': (0xdc, 0x32, 0x2f),
                    'magenta': (0xd3, 0x36, 0x82),
                    'violet': (0x6c, 0x71, 0xc4),
                    'blue': (0x26, 0x8b, 0xd2),
                    'cyan': (0x2a, 0xa1, 0x98),
                    'green': (0x85, 0x99, 0x00)}


placenames = ['myroom',
              'guestroom',
              'mybathroom',
              'diningoffice',
              'kitchen',
              'livingroom',
              'longhall',
              'momsbathroom',
              'momsroom',
              'outside']


atts = [('life', 'bool'),
        ('bulk', 'int', [], 0),
        ('grams', 'float', [], 0.0),
        ('stickiness', 'int', [], -10, 10),
        ('grade level', 'int',
         ['Preschool', 'Kindergarten', 'Post-secondary'],
         1, 12)]


def reciprocate(porttup):
    return (porttup[1], porttup[0])


def reciprocate_all(porttups):
    return [reciprocate(port) for port in porttups]


def reciprocal_pairs(pairs):
    return pairs + [reciprocate(pair) for pair in pairs]


class DefaultParameters:
    commit = True

    def __init__(self):
        self.dimensions = [{"name": "Physical"}]
        self.funcs = funcs
        # I'm going to have the menu bar on the left of the
        # screen. For convenience.
        gamemenu = {'name': 'Game',
                    'left': 0.1,
                    'bottom': 0.3,
                    'top': 1.0,
                    'right': 0.2,
                    'style': 'Small',
                    'visible': False,
                    'main_for_window': False}
        editormenu = {'name': 'Editor',
                      'left': 0.1,
                      'bottom': 0.3,
                      'top': 1.0,
                      'right': 0.2,
                      'style': 'Small',
                      'visible': False,
                      'main_for_window': False}
        placemenu = {'name': 'Place',
                     'left': 0.1,
                     'bottom': 0.3,
                     'top': 1.0,
                     'right': 0.2,
                     'style': 'Small',
                     'visible': False,
                     'main_for_window': False}
        thingmenu = {'name': 'Thing',
                     'left': 0.1,
                     'bottom': 0.3,
                     'top': 1.0,
                     'right': 0.2,
                     'style': 'Small',
                     'visible': False,
                     'main_for_window': False}
        mainmenu = {'name': 'Main',
                    'left': 0.0,
                    'bottom': 0.0,
                    'top': 1.0,
                    'right': 0.12,
                    'style': 'Big',
                    'visible': True,
                    'main_for_window': True}
        self.menus = [gamemenu, editormenu, placemenu, thingmenu, mainmenu]
        menunames = [menud["name"] for menud in self.menus]

        def mkmenuitemd(menu, idx, text, onclick, onclick_arg,
                        closer, visible, interactive):
            return {'menu': menu,
                    'idx': idx,
                    'text': text,
                    'onclick': onclick,
                    'onclick_arg': onclick_arg,
                    'closer': closer,
                    'visible': visible,
                    'interactive': interactive}
        self.menuitems = []
        i = 0
        for item in game_menu_items.iteritems():
            self.menuitems.append(
                mkmenuitemd('Game', i,
                            item[0], item[1][0], item[1][1],
                            True, True, True))
            i += 1
        i = 0
        for item in editor_menu_items.iteritems():
            self.menuitems.append(
                mkmenuitemd('Editor', i, item[0],
                            item[1][0], item[1][1],
                            True, True, True))
            i += 1
        i = 0
        for item in place_menu_items.iteritems():
            self.menuitems.append(
                mkmenuitemd('Place', i,
                            item[0], item[1][0], item[1][1],
                            True, True, True))
            i += 1
        i = 0
        for item in thing_menu_items.iteritems():
            self.menuitems.append(
                mkmenuitemd('Thing', i,
                            item[0], item[1][0], item[1][1],
                            True, True, True))
            i += 1
        i = 0
        for item in main_menu_items.iteritems():
            self.menuitems.append(
                mkmenuitemd('Main', i,
                            item[0], item[1][0], item[1][1],
                            False, True, True))
            i += 1

        def mkcolord(name, red, green, blue, alpha):
            return {'name': name,
                    'red': red,
                    'green': green,
                    'blue': blue,
                    'alpha': alpha}

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

        self.colors = [
            mkcolord(
                'solarized-' + color[0],
                color[1][0], color[1][1],
                color[1][2], 255)
            for color in solarized_colors.iteritems()]
        self.styles = [
            mkstyled(
                'Big',
                'DejaVu Sans', 16, 6,
                'solarized-base03',
                'solarized-base2',
                'solarized-base1',
                'solarized-base01'),
            mkstyled(
                'Small',
                'DejaVu Sans', 12, 3,
                'solarized-base03',
                'solarized-base2',
                'solarized-base1',
                'solarized-base01')]

        def mkitemd(dimension, name):
            return {'dimension': dimension,
                    'name': name}

        self.places = [mkitemd('Physical', p) for p in placenames]

        rpos = [('myroom', 'guestroom'),
                ('myroom', 'mybathroom'),
                ('myroom', 'outside'),
                ('myroom', 'diningoffice'),
                ('myroom', 'livingroom'),
                ('guestroom', 'diningoffice'),
                ('guestroom', 'livingroom'),
                ('guestroom', 'mybathroom'),
                ('livingroom', 'diningoffice'),
                ('diningoffice', 'kitchen'),
                ('livingroom', 'longhall'),
                ('longhall', 'momsbathroom'),
                ('longhall', 'momsroom')]
        nrpos = [('guestroom', 'outside'),
                 ('diningoffice', 'outside'),
                 ('momsroom', 'outside')]
        pos = reciprocal_pairs(rpos) + nrpos

        def mkportald(dimension, orig, dest):
            return {'dimension': dimension,
                    'name': "portal[%s->%s]" % (orig, dest),
                    'from_place': orig,
                    'to_place': dest}

        self.portals = [mkportald('Physical', po[0], po[1]) for po in pos]
        ths = [('me', 'myroom'),
               ('diningtable', 'diningoffice'),
               ('mydesk', 'myroom'),
               ('mybed', 'myroom'),
               ('bustedchair', 'myroom'),
               ('sofas', 'livingroom'),
               ('fridge', 'kitchen'),
               ('momsbed', 'momsroom'),
               ('mom', 'momsroom')]
        self.things = [mkitemd('Physical', th[0]) for th in ths]

        def mklocd(dimension, thing, place):
            return {'dimension': dimension,
                    'thing': thing,
                    'place': place}

        self.locations = [mklocd('Physical', th[0], th[1]) for th in ths]
        mjos = ["portal[momsroom->longhall]",
                "portal[longhall->livingroom]",
                "portal[livingroom->diningoffice]",
                "portal[diningoffice->outside]"]
        steps_to_kitchen = [('Physical', 'me',  0,
                             'portal[myroom->diningoffice]'),
                            ('Physical', 'me', 1,
                             'portal[diningoffice->kitchen]')]
        steps_outside = []
        i = 0
        while i < len(mjos):
            steps_outside.append(('Physical', 'mom', i, mjos[i]))
            i += 1

        def mkstepd(dimension, thing, idx, portal):
            return {"dimension": dimension,
                    "thing": thing,
                    "idx": idx,
                    "portal": portal}

        def mkjourneyd(dimension, thing, step, progress):
            return {"dimension": dimension,
                    "thing": thing,
                    "curstep": step,
                    "progress": progress}

        self.steps = [mkstepd(*step)
                      for step in steps_to_kitchen + steps_outside]

        self.journeys = [
            {"dimension": "Physical",
             "thing": "me",
             "curstep": 0,
             "progress": 0.0},
            {"dimension": "Physical",
             "thing": "mom",
             "curstep": 0,
             "progress": 0.0}]

        def mkcontd(dimension, contained, container):
            # I have not made any containments yet
            return {"dimension": dimension,
                    "contained": contained,
                    "container": container}

        self.containment = []

        def mkboardd(dimension, width, height, wallpaper):
            return {"dimension": dimension,
                    "width": width,
                    "height": height,
                    "wallpaper": wallpaper}

        self.boards = [mkboardd('Physical', 800, 600, 'wall')]

        def mkboardmenud(board, menu):
            return {"board": board,
                    "menu": menu}

        self.boardmenu = [mkboardmenud('Physical', menuname)
                          for menuname in menunames]

        def mkimgd(name, path, rltile):
            return {"name": name,
                    "path": path,
                    "rltile": rltile}

        imgtups = [("troll_m", "rltiles/player/base/troll_m.bmp", True),
                   ("zruty", "rltiles/nh-mon0/z/zruty.bmp", True),
                   ("orb", "orb.png", False),
                   ("wall", "wallpape.jpg", False)]
        self.imgs = [mkimgd(*tup) for tup in imgtups]

        def mkspotd(dimension, place, img, x, y, visible, interactive):
            return {"dimension": dimension,
                    "place": place,
                    "img": img,
                    "x": x,
                    "y": y,
                    "visible": visible,
                    "interactive": interactive}

        self.spots = [
            mkspotd('Physical', 'myroom', "orb", 400, 100, True, True),
            mkspotd('Physical', 'mybathroom', 'orb', 450, 150, True, True),
            mkspotd('Physical', 'guestroom', 'orb', 400, 200, True, True),
            mkspotd('Physical', 'livingroom', 'orb', 300, 150, True, True),
            mkspotd('Physical', 'diningoffice', 'orb', 350, 200, True, True),
            mkspotd('Physical', 'kitchen', 'orb', 350, 150, True, True),
            mkspotd('Physical', 'longhall', 'orb', 250, 150, True, True),
            mkspotd('Physical', 'momsroom', 'orb', 250, 100, True, True),
            mkspotd('Physical', 'momsbathroom', 'orb', 250, 200, True, True),
            mkspotd('Physical', 'outside', 'orb', 300, 100, True, True)]

        def mkpawnd(dimension, thing, img, visible, interactive):
            return {"dimension": dimension,
                    "thing": thing,
                    "img": img,
                    "visible": visible,
                    "interactive": interactive}

        pawntups = [('Physical', 'me', "troll_m", True, True),
                    ('Physical', 'mom', 'zruty', True, True)]
        self.pawns = [mkpawnd(*tup) for tup in pawntups]

        portitem = []
        for port in self.portals:
            rd = {}
            rd["name"] = port["name"]
            rd["dimension"] = port["dimension"]
            portitem.append(rd)

        self.items = self.places + self.things + portitem

        self.tabdicts = {
            Dimension: {"dimension": self.dimensions},
            Item: {"item": self.items},
            Place: {"place": self.places},
            Portal: {"portal": self.portals},
            Thing: {"thing": self.things,
                    "location": self.locations,
                    "containment": self.containment},
            Menu: {"menu": self.menus},
            MenuItem: {"menuitem": self.menuitems},
            Color: {"color": self.colors},
            Style: {"style": self.styles},
            Img: {"img": self.imgs},
            Spot: {"spot": self.spots},
            Pawn: {"pawn": self.pawns},
            Journey: {"journey": self.journeys,
                      "journeystep": self.steps},
            Board: {"board": self.boards}}

### These classes are just here to give a nice place to look up column
### names. Don't use them


class Item:
    coldecls = {"item":
                {"dimension": "text",
                 "name": "text"}}
    primarykeys = {"item": ("dimension", "name")}
    __metaclass__ = SaveableMetaclass


class Img:
    coldecls = {"img":
                {"name": "text",
                 "path": "text",
                 "rltile": "boolean"}}
    primarykeys = {"img": ("name",)}
    __metaclass__ = SaveableMetaclass


table_classes = [Dimension,
                 Img,
                 Item,
                 Thing,
                 Place,
                 Portal,
                 Journey,
                 Color,
                 Style,
                 MenuItem,
                 Menu,
                 Spot,
                 Pawn,
                 Board]


default = DefaultParameters()


sys.path.append(os.curdir)


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


def deep_lookup(dic, keylst):
    key = keylst.pop()
    ptr = dic
    while keylst != []:
        ptr = ptr[key]
        key = keylst.pop()
    return ptr[key]


class SaveableMetaclass(type):
    def __new__(metaclass, clas, parents, attrs):
        if('coldecls' not in attrs or
           'primarykeys' not in attrs or
           'maintab' not in attrs):
            return type(clas, parents, attrs)
        maintab = attrs['maintab']
        coldecls = attrs['coldecls']
        keynames = [key for key in coldecls]
        primarykeys = attrs['primarykeys']
        tablenames = [key for key in coldecls]

        if 'foreignkeys' in attrs:
            foreignkeys = attrs['foreignkeys']
        else:
            foreignkeys = {}
        if 'checks' in attrs:
            checks = attrs['checks']
        else:
            checks = {}
        for d in foreignkeys, checks:
            for tablename in tablenames:
                if tablename not in d:
                    d[tablename] = {}
        schemata = []
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
            pkeydecs = [keyname + " " + typ.upper()
                        for (keyname, typ) in coldecl.iteritems()
                        if keyname in pkey]
            valdecs = [valname + " " + typ.upper()
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
            table_decl_data = [coldecstr, pkeystr]
            if len(fkeystrs) > 0:
                table_decl_data.append(fkeystr)
            if len(cks) > 0:
                table_decl_data.append(chkstr)
            table_decl = ", ".join(table_decl_data)
            create_stmt = "CREATE TABLE %s (%s);" % (tablename, table_decl)
            insert_stmt_start = "INSERT INTO %s VALUES " % (
                tablename,)
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
            schemata.append(create_stmt)

        def dictify_rows(cols, rows):
            r = []
            for row in rows:
                assert len(cols) == len(row)
                d = {}
                i = 0
                while i < len(row):
                    col = cols[i]
                    val = row[i]
                    d[col] = val
                    i += 1
                r.append(d)
            return r

        def insert_rowdicts_table(db, rowdicts, tabname):
            rowstr = rowstrs[tabname]
            qrystr = inserts[tabname] + ", ".join([rowstr] * len(rowdicts))
            qrylst = []
            for rowdict in rowdicts:
                qrylst.extend([rowdict[col] for col in colnames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)

        def delete_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = deletes[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)

        def detect_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = detects[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return db.c.fetchall()

        def missing_keydicts_table(db, keydicts, tabname):
            keystr = keystrs[tabname]
            qrystr = missings[tabname] + ", ".join([keystr] * len(keydicts))
            qrylst = []
            for keydict in keydicts:
                qrylst.extend([keydict[col] for col in keynames[tabname]])
            qrytup = tuple(qrylst)
            db.c.execute(qrystr, qrytup)
            return db.c.fetchall()

        def build(self):
            pass

        def pull(self, db, tabdict):
            return tabdict

        def setup(self):
            if not self.built:
                self.build()
                self.built = True

        dbop = {'insert': insert_rowdicts_table,
                'delete': delete_keydicts_table,
                'detect': detect_keydicts_table,
                'missing': missing_keydicts_table}
        atrdic = {'coldecls': coldecls,
                  'colnames': colnames,
                  'colnamestr': colnamestr,
                  'cols': colnames[maintab],
                  'primarykeys': primarykeys,
                  'foreignkeys': foreignkeys,
                  'checks': checks,
                  'schemata': schemata,
                  'keylen': keylen,
                  'rowlen': rowlen,
                  'keyqms': keyqms,
                  'rowqms': rowqms,
                  'dbop': dbop,
                  'build': build,
                  'built': False,
                  'pull': pull}
        atrdic.update(attrs)

        return type.__new__(metaclass, clas, parents, atrdic)
