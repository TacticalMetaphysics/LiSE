from menu import Menu, MenuItem
from style import Color, Style
from dimension import Dimension
from item import Item, Thing, Place, Portal, Schedule, Journey
from calendar import CalendarCol
from img import Img
from pawn import Pawn
from spot import Spot
from board import Board
from effect import Effect, EffectDeck
from database import Database
from util import dictify_row


"""Put some default values I made up into a database called
default.sqlite, copied from empty.sqlite.

At some point this will compile csv files and maybe xml into a
database.

"""


class DefaultParameters:
    pass
parms = DefaultParameters()


dimname = 'Physical'
langname = 'English'

game_menu_items = {'@new_map': 'start_new_map()',
                   '@open_map': 'open_map()',
                   '@save_map': 'save_map()',
                   '@quit_maped': 'quit_map_editor()'}
editor_menu_items = {'@ed_select': 'editor_select()',
                     '@ed_copy': 'editor_copy()',
                     '@ed_paste': 'editor_paste()',
                     '@ed_delete': 'editor_delete()'}
place_menu_items = {'@custplace': 'new_place(custom)',
                    '@workplace': 'new_place(workplace)',
                    '@commonplace': 'new_place(commons)',
                    '@lairplace': 'new_place(lair)'}
thing_menu_items = {'@custthing': 'new_thing(custom)',
                    '@decorthing': 'new_thing(decoration)',
                    '@clothing': 'new_thing(clothing)',
                    '@toolthing': 'new_thing(tool)'}
main_menu_items = {'@game_menu': 'toggle_menu(Game)',
                   '@editor_menu': 'toggle_menu(Editor)',
                   '@place_menu': 'toggle_menu(Place)',
                   '@thing_menu': 'toggle_menu(Thing)'}

miproto = [('Game', game_menu_items), ('Editor', editor_menu_items),
           ('Place', place_menu_items),
           ('Thing', thing_menu_items), ('Main', main_menu_items)]

menu_items = []
for mip in miproto:
    i = 0
    (menu, items) = mip
    for item in items.iteritems():
        (txt, onclick) = item
        menu_items.append({
            'board': dimname,
            'menu': menu,
            'idx': i,
            'text': txt,
            'effect_deck': onclick,
            'closer': menu != 'Main',
            'interactive': True,
            'visible': True})
        i += 1
parms.menu_items = menu_items


solarized_colors = {
    'base03': (0x00, 0x2b, 0x36),
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

colors = [{
    'name': 'solarized-' + it[0],
    'red': it[1][0],
    'green': it[1][1],
    'blue': it[1][2],
    'alpha': 255}
for it in solarized_colors.iteritems()]
parms.colors = colors

styletups = [
    ('BigDark',
     'DejaVu Sans', 16, 6,
     'solarized-base03',
     'solarized-base2',
     'solarized-base1',
     'solarized-base01'),
    ('SmallDark',
     'DejaVu Sans', 12, 3,
     'solarized-base03',
     'solarized-base2',
     'solarized-base1',
     'solarized-base01'),
    ('BigLight',
     'DejaVu Serif', 16, 6,
     'solarized-base3',
     'solarized-base02',
     'solarized-base01',
     'solarized-base1'),
    ('SmallLight',
     'DejaVu Serif', 12, 3,
     'solarized-base3',
     'solarized-base02',
     'solarized-base01',
     'solarized-base1')]

styles = [
    {'name': style[0],
     'fontface': style[1],
     'fontsize': style[2],
     'spacing': style[3],
     'bg_inactive': style[4],
     'bg_active': style[5],
     'fg_inactive': style[6],
     'fg_active': style[7]}
    for style in styletups]
parms.styles = styles

rpos = [('myroom', 'guestroom'),
        ('myroom', 'mybathroom'),
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
         ('momsroom', 'outside'),
         ('myroom', 'outside')]


def mkportald(o, d):
    return {
        'dimension': dimname,
        'name': 'portal[{0}->{1}]'.format(o, d),
        'from_place': o,
        'to_place': d}


def tup2port(t):
    return mkportald(*t)


def invtup2port(t):
    (o, d) = t
    return mkportald(d, o)


portals = (
    [tup2port(t) for t in rpos] +
    [invtup2port(t) for t in rpos] +
    [tup2port(t) for t in nrpos])
parms.portals = portals


ths = [('me', 'myroom'),
       ('diningtable', 'diningoffice'),
       ('mydesk', 'myroom'),
       ('mybed', 'myroom'),
       ('bustedchair', 'myroom'),
       ('sofas', 'livingroom'),
       ('fridge', 'kitchen'),
       ('momsbed', 'momsroom'),
       ('mom', 'momsroom')]


things = [
    {
        "dimension": dimname,
        "name": tup[0],
        "location": tup[1],
	"container": None,
        "portal": None,
        "journey_step": 0,
        "journey_progress": 0.0,
        "age": 0}
    for tup in ths]
parms.things = things


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


places = [{'dimension': dimname, 'name': n} for n in placenames]
parms.places = places


def portnamer(f, t):
    return "portal[{0}->{1}]".format(f, t)


def journeystepd(dim, th, idx, pn):
    return {
        "dimension": dim,
        "thing": th,
        "idx": idx,
        "portal": pn}


def portlist2journey(dim, th, pl):
    r = []
    i = 0
    for port in pl:
        r.append(journeystepd(dim, th, i, port))
        i += 1
    return r


def fmtports(pl):
    return ['portal[{0}->{1}]'.format(*pair) for pair in pl]


def mkjourney(dim, th, pl):
    return portlist2journey(dim, th, fmtports(pl))


moms_journey_outside = mkjourney(
    dimname, 'mom',
    [('momsroom', 'longhall'),
     ('longhall', 'livingroom'),
     ('livingroom', 'diningoffice'),
     ('diningoffice', 'outside')])
my_journey_to_kitchen = mkjourney(
    dimname, 'me',
    [('myroom', 'diningoffice'),
     ('diningoffice', 'kitchen')])

steps = my_journey_to_kitchen + moms_journey_outside
parms.steps = steps


journeys = [
    (dimname, 'mom', moms_journey_outside),
    (dimname, 'me', my_journey_to_kitchen)]
parms.journeys = journeys


schedules = []
parms.schedules = schedules

calcols = [
    (dimname,
     "me",
     True,
     True),
    (dimname,
     "mom",
     True,
     True)]
parms.calcols = [
    {"board": tup[0],
     "item": tup[1],
     "visible": tup[2],
     "interactive": tup[3]}
    for tup in calcols]


imgtups = [("troll_m", "rltiles/player/base/troll_m.bmp", True),
           ("zruty", "rltiles/nh-mon0/z/zruty.bmp", True),
           ("orb", "orb.png", False),
           ("wall", "wallpape.jpg", False)]
imgs = [dictify_row(row, Img.colns) for row in imgtups]
parms.imgs = imgs


spottups = [
    ('Physical', 'myroom', "orb", 400, 100, True, True),
    ('Physical', 'mybathroom', 'orb', 450, 150, True, True),
    ('Physical', 'guestroom', 'orb', 400, 200, True, True),
    ('Physical', 'livingroom', 'orb', 300, 150, True, True),
    ('Physical', 'diningoffice', 'orb', 350, 200, True, True),
    ('Physical', 'kitchen', 'orb', 350, 150, True, True),
    ('Physical', 'longhall', 'orb', 250, 150, True, True),
    ('Physical', 'momsroom', 'orb', 250, 100, True, True),
    ('Physical', 'momsbathroom', 'orb', 250, 200, True, True),
    ('Physical', 'outside', 'orb', 300, 100, True, True)]
spots = [
    {"dimension": tup[0],
     "place": tup[1],
     "img": tup[2],
     "x": tup[3],
     "y": tup[4],
     "visible": tup[5],
     "interactive": tup[6]}
    for tup in spottups]
parms.spots = spots


pawntups = [
    (dimname, 'me', 'troll_m'),
    (dimname, 'mom', 'zruty')]
pawns = [
    {'board': row[0],
     'thing': row[1],
     'img': row[2],
     'visible': True,
     'interactive': False}
    for row in pawntups]
parms.pawns = pawns


menutups = [
    ('Game', 0.1, 0.3, 1.0, 0.2, 'SmallDark', False, False),
    ('Editor', 0.1, 0.3, 1.0, 0.2, 'SmallDark', False, False),
    ('Place', 0.1, 0.3, 1.0, 0.2, 'SmallDark', False, False),
    ('Main', 0.0, 0.1, 1.0, 0.12, 'BigDark', True, True),
    ('Thing', 0.1, 0.3, 1.0, 0.2, 'SmallDark', False, False)]
menus = [
    {
        "board": dimname,
        "name": tup[0],
        "left": tup[1],
        "right": tup[2],
        "top": tup[3],
        "bottom": tup[4],
        "style": tup[5],
        "visible": tup[6],
        "main_for_window": tup[7]}
    for tup in menutups]
parms.menus = menus

boards = [
    (dimname,
     'wall')]
     
parms.boards = [
    {"dimension": tup[0],
     "wallpaper": tup[1],
     "calendar_visible": True}
    for tup in boards]


def mkefd2(fun, arg):
    return {
        "name": "{0}({1})".format(fun, arg),
        "func": fun,
        "arg": arg}

effects = (
    [mkefd2("new_place", a) for a in [
        'custom', 'workplace', 'commons', 'lair']] +
    [mkefd2("new_thing", a) for a in [
        'custom', 'decoration', 'clothing', 'tool']] +
    [mkefd2("editor_copy", ""),
     mkefd2("editor_select", ""),
     mkefd2("editor_paste", ""),
     mkefd2("editor_delete", ""),
     mkefd2("start_new_map", ""),
     mkefd2("open_map", ""),
     mkefd2("save_map", ""),
     mkefd2("quit_map_editor", "")])
parms.effects = effects


effect_decks = [
    {"deck": effectdict["name"],
     "idx": 0,
     "effect": effectdict["name"]}
    for effectdict in effects]
parms.effect_decks = effect_decks

strtups = [
    ("@game_menu", "Game"),
    ("@editor_menu", "Editor"),
    ("@place_menu", "Place"),
    ("@thing_menu", "Thing"),
    ("@new_map", "New world"),
    ("@open_map", "Open world..."),
    ("@save_map", "Save..."),
    ("@quit_maped", "Quit"),
    ("@ed_select", "Select..."),
    ("@ed_copy", "Copy"),
    ("@ed_paste", "Paste"),
    ("@ed_delete", "Delete..."),
    ("@custplace", "New place..."),
    ("@workplace", "New workplace..."),
    ("@commonplace", "New commons..."),
    ("@lairplace", "New lair..."),
    ("@custthing", "New thing..."),
    ("@decorthing", "New decoration..."),
    ("@clothing", "New clothing..."),
    ("@toolthing", "New tool...")]

strings = [(tup[0], langname, tup[1]) for tup in strtups]
parms.strings = strings


EMPTY_DB_FILE = 'empty.sqlite'

TARGET_DB_FILE = 'default.sqlite'

infile = open(EMPTY_DB_FILE, 'rb')
outfile = open(TARGET_DB_FILE, 'wb')

outfile.write(infile.read())

infile.close()
outfile.close()


def populate_menus(db, menus, menu_items):
    menutd = {"menu": menus}
    mitd = {"menu_item": menu_items}
    Menu.dbop['insert'](db, menutd)
    MenuItem.dbop['insert'](db, mitd)


def populate_styles(db, colors, styles):
    colortd = {"color": colors}
    styletd = {"style": styles}
    Color.dbop['insert'](db, colortd)
    Style.dbop['insert'](db, styletd)


def populate_items(db, things, places, portals):
    combined = things + places + portals
    dimensions = []
    for row in combined:
        dim = {'name': row['dimension']}
        if dim not in dimensions:
            dimensions.append(dim)
    items = []
    for row in combined:
        it = {'dimension': row['dimension'], 'name': row['name']}
        if it not in items:
            items.append(it)
    dimension_td = {'dimension': dimensions}
    item_td = {'item': items}
    thing_td = {'thing': things}
    place_td = {'place': places}
    portal_td = {'portal': portals}
    Dimension.dbop['insert'](db, dimension_td)
    Item.dbop['insert'](db, item_td)
    Thing.dbop['insert'](db, thing_td)
    Place.dbop['insert'](db, place_td)
    Portal.dbop['insert'](db, portal_td)


def populate_journey_steps(db, steps):
    jtd = {"journey_step": steps}
    Journey.dbop['insert'](db, jtd)


def populate_schedules(db, scheds):
    if scheds != []:
        schedtd = {"schedule": scheds}
        Schedule.dbop['insert'](db, schedtd)
    for item in db.journeydict.iteritems():
        (dimname, itdict) = item
        for item in itdict.iteritems():
            (itname, j) = item
            s = j.schedule()
            if dimname not in db.scheduledict:
                db.scheduledict[dimname] = {}
            db.scheduledict[dimname][itname] = s


def populate_effects(db, effects, decks):
    eftd = {"effect": effects}
    decktd = {"effect_deck_link": decks}
    Effect.dbop['insert'](db, eftd)
    EffectDeck.dbop['insert'](db, decktd)


def populate_gfx(db, imgs, pawns, spots, boards, calendars):
    img_td = {'img': imgs}
    pawn_td = {'pawn': pawns}
    spot_td = {'spot': spots}
    board_td = {'board': boards}
    cal_td = {'calendar_col': calendars}
    Img.dbop['insert'](db, img_td)
    Pawn.dbop['insert'](db, pawn_td)
    Spot.dbop['insert'](db, spot_td)
    Board.dbop['insert'](db, board_td)
    CalendarCol.dbop['insert'](db, cal_td)


def populate_strs(db, strs):
    for s in strs:
        db.c.execute("INSERT INTO strings VALUES (?, ?, ?);", s)


def populate_database(db, data):
    populate_menus(db, data.menus, data.menu_items)
    populate_styles(db, data.colors, data.styles)
    populate_items(db, data.things, data.places, data.portals)
    populate_effects(db, data.effects, data.effect_decks)
    populate_journey_steps(db, data.steps)
    populate_schedules(db, data.schedules)
    populate_gfx(db, data.imgs, data.pawns, data.spots, data.boards,
                 data.calcols)
    populate_strs(db, data.strings)
    db.c.execute("INSERT INTO game DEFAULT VALUES;")


db = Database(TARGET_DB_FILE)
populate_database(db, parms)
db.c.close()
db.conn.commit()
