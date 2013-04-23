import sqlite3
import sys
import os
from widgets import Color, MenuItem, Menu, Spot, Pawn, Board, Style
from thing import Thing
from graph import Dimension, Journey, Place, Portal
from pyglet.resource import image
from util import SaveableMetaclass, Item, Img


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
