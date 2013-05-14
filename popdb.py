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


class DefaultParameters:
    pass
parms = DefaultParameters()


dimname = 'Physical'

game_menu_items = {'New': 'start_new_map()',
                   'Open': 'open_map()',
                   'Save': 'save_map()',
                   'Quit': 'quit_map_editor()'}
editor_menu_items = {'Select': 'editor_select()',
                     'Copy': 'editor_copy()',
                     'Paste': 'editor_paste()',
                     'Delete': 'editor_delete()'}
place_menu_items = {'Custom Place': 'new_place(custom)',
                    'Workplace': 'new_place(workplace)',
                    'Commons': 'new_place(commons)',
                    'Lair': 'new_place(lair)'}
thing_menu_items = {'Custom Thing': 'new_thing(custom)',
                    'Decoration': 'new_thing(decoration)',
                    'Clothing': 'new_thing(clothing)',
                    'Tool': 'new_thing(tool)'}
main_menu_items = {'Game': 'toggle_menu(Game)',
                   'Editor': 'toggle_menu(Editor)',
                   'Place': 'toggle_menu(Place)',
                   'Thing': 'toggle_menu(Thing)'}

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
    ('Big',
     'DejaVu Sans', 16, 6,
     'solarized-base03',
     'solarized-base2',
     'solarized-base1',
     'solarized-base01'),
    ('Small',
     'DejaVu Sans', 12, 3,
     'solarized-base03',
     'solarized-base2',
     'solarized-base1',
     'solarized-base01')]

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
    {'dimension': row[0],
     'thing': row[1],
     'img': row[2],
     'visible': True,
     'interactive': False}
    for row in pawntups]
parms.pawns = pawns


menutups = [
    ('Game', 0.1, 0.3, 1.0, 0.2, 'Small', False, False),
    ('Editor', 0.1, 0.3, 1.0, 0.2, 'Small', False, False),
    ('Place', 0.1, 0.3, 1.0, 0.2, 'Small', False, False),
    ('Main', 0.0, 0.1, 1.0, 0.12, 'Big', True, True),
    ('Thing', 0.1, 0.3, 1.0, 0.2, 'Small', False, False)]
menus = [
    {
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


boards = [{
    'dimension': dimname,
    'width': 800,
    'height': 600,
    'wallpaper': 'wall'}]
parms.boards = boards

board_menu = [{'board': dimname, 'menu': menuname}
              for menuname in
              ['Thing', 'Place', 'Game', 'Editor', 'Main']]
parms.board_menu = board_menu


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


caltups = [
    (
        "Physical",
        "me",
        False,
        True,
        10,
        0,
        0.2,
        0.9,
        0.1,
        0.9,
        'Small')]


calendars = [
    dict(
        zip(
            ("dimension", "item", "visible", "interactive",
             "rows_on_screen", "scrolled_to", "left", "top",
             "bot", "right", "style"), row))
    for row in caltups]
parms.calendars = calendars


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


def populate_gfx(db, imgs, pawns, spots, boards, board_menus, calendars):
    img_td = {'img': imgs}
    pawn_td = {'pawn': pawns}
    spot_td = {'spot': spots}
    board_td = {'board': boards,
                'board_menu': board_menus}
    cal_td = {'calendar_col': calendars}
    Img.dbop['insert'](db, img_td)
    Pawn.dbop['insert'](db, pawn_td)
    Spot.dbop['insert'](db, spot_td)
    Board.dbop['insert'](db, board_td)
    CalendarCol.dbop['insert'](db, cal_td)


def populate_database(db, data):
    populate_menus(db, data.menus, data.menu_items)
    populate_styles(db, data.colors, data.styles)
    populate_items(db, data.things, data.places, data.portals)
    populate_effects(db, data.effects, data.effect_decks)
    populate_journey_steps(db, data.steps)
    populate_schedules(db, data.schedules)
    populate_gfx(db, data.imgs, data.pawns, data.spots, data.boards,
                 data.board_menu, data.calendars)


db = Database(TARGET_DB_FILE)
populate_database(db, parms)
db.c.close()
db.conn.commit()
