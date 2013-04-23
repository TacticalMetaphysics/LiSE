import sqlite3
from widgets import Color, MenuItem, Menu, Spot, Pawn, Board, Style
from world import Journey, Place, Portal, Thing
from pyglet.resource import image
from util import Img, table_classes, default


class Database:
    def __init__(self, dbfile):
        self.conn = sqlite3.connect(dbfile)
        self.c = self.conn.cursor()
        self.altered = set()
        self.removed = set()
        self.placedict = {}
        self.portaldict = {}
        self.thingdict = {}
        self.spotdict = {}
        self.imgdict = {}
        self.boarddict = {}
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
        self.dictdict = {Place: self.placedict,
                         Portal: self.portaldict,
                         Thing: self.thingdict,
                         Spot: self.spotdict,
                         Img: self.imgdict,
                         Board: self.boarddict,
                         Pawn: self.pawndict,
                         Style: self.styledict,
                         Color: self.colordict,
                         Journey: self.journeydict}
        self.tabdict = {"place": self.placedict,
                        "portal": self.portaldict,
                        "thing": self.thingdict,
                        "spot": self.spotdict,
                        "img": self.imgdict,
                        "board": self.boarddict,
                        # fuck i can't do menus this way i need to
                        # bring back the menudict but i won't be --
                        # you know what? I'm not going to sync menus
                        # at all. fuck 'em
                        "pawn": self.pawndict,
                        "style": self.styledict,
                        "color": self.colordict,
                        "journey": self.journeydict}
        self.func = {'toggle_menu_visibility': self.toggle_menu_visibility}

    def __del__(self):
        self.c.close()
        self.conn.commit()
        self.conn.close()

    def insert_defaults(self):
        for clas in table_classes:
            tabdict = default.tabdicts[clas]
            for item in tabdict.iteritems():
                (tabname, rowdicts) = item
                self.insert_rowdict_table(rowdicts, clas, tabname)
        for func in default.funcs:
            self.xfunc(func)

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

    def mkschema(self):
        for clas in table_classes:
            for tab in clas.schemata:
                self.c.execute(tab)
        self.conn.commit()

    def initialized(self):
        try:
            for tab in ["thing", "place", "attribute", "img"]:
                self.c.execute("select count(*) from %s limit 1"
                               % (tab,))
            return True
        except sqlite3.OperationalError:
            return False

    def xfunc(self, func):
        self.func[func.__name__] = func

    def call_func(self, fname, farg):
        return self.func[fname](farg)

    def load_board(self, dimension):
        # I'll be fetching all the *rows* I need, then turning them
        # into Python objects, starting with the ones that don't have
        # foreign keys.
        def genselect(clas, tab):
            tabcol = clas.colnames[tab]
            return ("SELECT " + ", ".join(tabcol) +
                    " FROM " + tab + " WHERE dimension=?")
        # fetch all the place rows
        qrystr = genselect(Place, "place")
        qrytup = (dimension,)
        self.c.execute(qrystr, qrytup)
        place_rows = self.c.fetchall()
        place_rowdicts = [
            dictify_row(row, Place.colnames["place"])
            for row in place_rows]
        # fetch all the thing rows
        qrystr = genselect(Thing, "thing")
        self.c.execute(qrystr, qrytup)
        thing_rows = self.c.fetchall()
        thing_rowdicts = [
            dictify_row(row, Thing.colnames["thing"])
            for row in thing_rows]
        # fetch all the portal rows
        qrystr = genselect(Portal, "portal")
        self.c.execute(qrystr, qrytup)
        portal_rows = self.c.fetchall()
        portal_rowdicts = [
            dictify_row(row, Portal.colnames["portal"])
            for row in portal_rows]
        # fetch all containment rows
        qrystr = genselect(Thing, "containment")
        self.c.execute(qrystr, qrytup)
        containment_rows = self.c.fetchall()
        containment_rowdicts = [
            dictify_row(row, Thing.colnames["containment"])
            for row in containment_rows]
        # fetch all location rows
        qrystr = genselect(Thing, "location")
        self.c.execute(qrystr, qrytup)
        location_rows = self.c.fetchall()
        location_rowdicts = [
            dictify_row(row, Thing.colnames["location"])
            for row in location_rows]
        # fetch all journey step rows
        qrystr = genselect(Journey, "journeystep")
        self.c.execute(qrystr, qrytup)
        journey_step_rows = self.c.fetchall()
        journey_step_rowdicts = [
            dictify_row(row, Journey.colnames["journeystep"])
            for row in journey_step_rows]
        # fetch all journey rows
        qrystr = genselect(Journey, "journey")
        self.c.execute(qrystr, qrytup)
        journey_rows = self.c.fetchall()
        journey_rowdicts = [
            dictify_row(row, Journey.colnames["journey"])
            for row in journey_rows]
        # fetch all spot rows
        qrystr = genselect(Spot, "spot")
        self.c.execute(qrystr, qrytup)
        spot_rows = self.c.fetchall()
        spot_rowdicts = [dictify_row(row, Spot.colnames["spot"])
                         for row in spot_rows]
        # fetch all pawn rows
        qrystr = genselect(Pawn, "pawn")
        self.c.execute(qrystr, qrytup)
        pawn_rows = self.c.fetchall()
        pawn_rowdicts = [dictify_row(row, Pawn.colnames["pawn"])
                         for row in pawn_rows]
        # Dimension is no longer an adequate key; stop using genselect

        # find out what menus this board has
        qrystr = "SELECT menu FROM boardmenu WHERE board=?"
        self.c.execute(qrystr, qrytup)
        menutups = self.c.fetchall()
        menunames = [tup[0] for tup in menutups]
        # load them
        qrystr = ("SELECT " + ", ".join(Menu.colnames["menu"]) +
                  " FROM menu WHERE name IN (" +
                  ", ".join(["?"] * len(menunames)) + ")")
        qrytup = tuple(menunames)
        self.c.execute(qrystr, qrytup)
        menu_rows = self.c.fetchall()
        menu_rowdicts = [dictify_row(row, Menu.colnames["menu"])
                         for row in menu_rows]
        # load the menus' items
        qrystr = ("SELECT " + ", ".join(MenuItem.colnames["menuitem"]) +
                  " FROM menuitem WHERE menu IN (" +
                  ", ".join(["?"] * len(menunames)) + ")")
        self.c.execute(qrystr, qrytup)
        menu_item_rows = self.c.fetchall()
        menu_item_rowdicts = [dictify_row(row, MenuItem.colnames["menuitem"])
                              for row in menu_item_rows]
        stylenames = [rowdict["style"] for rowdict in menu_rowdicts]
        # load the styles in the menus
        qrystr = ("SELECT " + ", ".join(Style.colnames["style"]) +
                  " FROM style WHERE name IN (" +
                  ", ".join(["?"] * len(stylenames)) + ")")
        qrytup = tuple(stylenames)
        self.c.execute(qrystr, qrytup)
        style_rows = self.c.fetchall()
        # load the colors in the styles
        style_rowdicts = [dictify_row(row, Style.colnames["style"])
                          for row in style_rows]
        colornames = []
        for rowdict in style_rowdicts:
            colornames.extend([rowdict["bg_inactive"], rowdict["bg_active"],
                               rowdict["fg_inactive"], rowdict["fg_active"]])
        # load the colors
        qrystr = ("SELECT " + ", ".join(Color.colnames["color"]) +
                  " FROM color WHERE name IN (" +
                  ", ".join(["?"] * len(colornames)) + ")")
        qrytup = tuple(colornames)
        self.c.execute(qrystr, qrytup)
        color_rows = self.c.fetchall()
        color_rowdicts = [
            dictify_row(row, Color.colnames["color"])
            for row in color_rows]
        # load the imgs
        imgs2load = set()
        qrystr = genselect(Board, "board")
        self.c.execute(qrystr, (dimension,))
        board_rowdict = dictify_row(self.c.fetchone(), Board.colnames["board"])
        imgs2load.add(board_rowdict["wallpaper"])
        for row in spot_rowdicts:
            imgs2load.add(row["img"])
        for row in pawn_rowdicts:
            imgs2load.add(row["img"])
        imgnames = list(imgs2load)
        qrystr = ("SELECT " + ", ".join(Img.colnames["img"]) +
                  " FROM img WHERE name IN (" +
                  ", ".join(["?"] * len(imgnames)) + ")")
        qrytup = tuple(imgnames)
        self.c.execute(qrystr, qrytup)
        img_rows = self.c.fetchall()
        img_rowdicts = [dictify_row(row, Img.colnames["img"])
                        for row in img_rows]
        for row in img_rowdicts:
            if row["rltile"]:
                self.load_rltile(row["name"], row["path"])
            else:
                self.load_regular_img(row["name"], row["path"])
        # OK, all the data is loaded. Now construct Python objects of it all.

        for row in color_rowdicts:
            color = Color(self, row)
            self.colordict[row["name"]] = color
        for row in style_rowdicts:
            style = Style(self, row)
            self.styledict[row["name"]] = style
        if dimension not in self.boardmenudict:
            self.boardmenudict[dimension] = {}
        for row in menu_rowdicts:
            menu = Menu(self, row)
            self.boardmenudict[dimension][row["name"]] = menu
        for row in menu_item_rowdicts:
            menuitem = MenuItem(self, row, dimension)
            menu = self.boardmenudict[dimension][row["menu"]]
            while row["idx"] >= len(menu.items):
                menu.items.append(None)
            menu.items[row["idx"]] = menuitem
        if dimension not in self.placedict:
            self.placedict[dimension] = {}
        for row in place_rowdicts:
            pl = Place(self, row)
            self.placedict[dimension][row["name"]] = pl
        if dimension not in self.thingdict:
            self.thingdict[dimension] = {}
        for row in thing_rowdicts:
            th = Thing(self, row)
            self.thingdict[dimension][row["name"]] = th
        # Places and things depend on one another. Only now I've
        # loaded them both may I link them to one another.
        for row in location_rowdicts:
            thing = self.thingdict[dimension][row["thing"]]
            place = self.placedict[dimension][row["place"]]
            thing.location = place
            place.contents.append(thing)
        if dimension not in self.containerdict:
            self.containerdict[dimension] = {}
        if dimension not in self.contentsdict:
            self.contentsdict[dimension] = {}
        for row in containment_rowdicts:
            inner = self.thingdict[dimension][row["contained"]]
            outer = self.thingdict[dimension][row["container"]]
            outer.contents.append(inner)
        if dimension not in self.portaldict:
            self.portaldict[dimension] = {}
        for row in portal_rowdicts:
            portal = Portal(self, row)
            self.portaldict[dimension][row["name"]] = portal
            self.placedict[dimension][row["from_place"]].portals.append(portal)
        if dimension not in self.journeydict:
            self.journeydict[dimension] = {}
        for row in journey_rowdicts:
            journey = Journey(self, row)
            self.journeydict[dimension][row["thing"]] = journey
        for row in journey_step_rowdicts:
            journey = self.journeydict[dimension][row["thing"]]
            portal = self.portaldict[dimension][row["portal"]]
            journey.set_step(portal, row["idx"])
        if dimension not in self.spotdict:
            self.spotdict[dimension] = {}
        for row in spot_rowdicts:
            spot = Spot(self, row)
            self.spotdict[dimension][row["place"]] = spot
            self.placedict[dimension][row["place"]].spot = spot
        if dimension not in self.pawndict:
            self.pawndict[dimension] = {}
        for row in pawn_rowdicts:
            pawn = Pawn(self, row)
            self.pawndict[dimension][row["thing"]] = pawn
            self.thingdict[dimension][row["thing"]].pawn = pawn
        board = Board(self, board_rowdict)
        for pawn in board.pawns:
            pawn.board = board
        for spot in board.spots:
            spot.board = board
        for menu in board.menus:
            menu.board = board
        self.boarddict[dimension] = board
        return board

    def load_rltile(self, name, path):
        badimg = image(path)
        badimgd = badimg.get_image_data()
        bad_rgba = badimgd.get_data('RGBA', badimgd.pitch)
        good_data = bad_rgba.replace('\xffGll', '\x00Gll')
        good_data = good_data.replace('\xff.', '\x00.')
        badimgd.set_data('RGBA', badimgd.pitch, good_data)
        rtex = badimgd.get_texture()
        rtex.name = name
        self.imgdict[name] = rtex
        return rtex

    def load_regular_img(self, name, path):
        tex = image(path).get_image_data().get_texture()
        tex.name = name
        self.imgdict[name] = tex
        return tex

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
        return [self.thingdict[dim][name] for name in thingnames]

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
