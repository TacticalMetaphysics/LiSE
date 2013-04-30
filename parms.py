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
main_menu_items = {'Game': 'toggle_menu_visibility(Game)',
                   'Editor': 'toggle_menu_visibility(Editor)',
                   'Place': 'toggle_menu_visibility(Place)',
                   'Thing': 'toggle_menu_visibility(Thing)'}


miproto = [('Game', game_menu_items), ('Editor', editor_menu_items),
           ('Place', place_menu_items),
           ('Thing', thing_menu_items), ('Main', main_menu_items)]


def mkmids(proto):
    r = []
    for mip in proto:
        i = 0
        (menu, items) = mip
        for item in items.iteritems():
            (txt, onclick) = item
            r.append({
                'menu': menu,
                'idx': i,
                'text': txt,
                'onclick': onclick,
                'closer': menu != 'Main',
                'interactive': menu == 'Main',
                'visible': menu == 'Main'})
            i += 1
    return r

menu_items = mkmids(miproto)

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


def mkcolord(c):
    d = c[1]
    return {
        'name': 'solarized-' + c[0],
        'red': d[0],
        'green': d[1],
        'blue': d[2],
        'alpha': 255}

colors = [mkcolord(c) for c in solarized_colors.iteritems()]

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


def mkstyled(st):
    return {
        'name': st[0],
        'fontface': st[1],
        'fontsize': st[2],
        'spacing': st[3],
        'bg_inactive': st[4],
        'bg_active': st[5],
        'fg_inactive': st[6],
        'fg_active': st[7]}


styles = [mkstyled(st) for st in styletups]

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


ths = [('me', 'myroom', None),
       ('diningtable', 'diningoffice', None),
       ('mydesk', 'myroom', None),
       ('mybed', 'myroom', None),
       ('bustedchair', 'myroom', None),
       ('sofas', 'livingroom', None),
       ('fridge', 'kitchen', None),
       ('momsbed', 'momsroom', None),
       ('mom', 'momsroom', None)]


def mkthingd(t):
    (name, loc, contr) = t
    return {
        'dimension': dimname,
        'name': name,
        'location': loc,
        'container': contr}


things = [mkthingd(th) for th in ths]


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


mjos = ["portal[momsroom->longhall]",
        "portal[longhall->livingroom]",
        "portal[livingroom->diningoffice]",
        "portal[diningoffice->outside]"]


def mkstepd(dim, it, i, port):
    return {
        'dimension': dim,
        'thing': it,
        'idx': i,
        'portal': port}

steps_to_kitchen = [mkstepd('Physical', 'me',  0,
                            'portal[myroom->diningoffice]'),
                    mkstepd('Physical', 'me', 1,
                            'portal[diningoffice->kitchen]')]

steps_outside = []
i = 0
while i < len(mjos):
    steps_outside.append(mkstepd('Physical', 'mom', i, mjos[i]))
    i += 1

steps = steps_to_kitchen + steps_outside

imgtups = [("troll_m", "rltiles/player/base/troll_m.bmp", True),
           ("zruty", "rltiles/nh-mon0/z/zruty.bmp", True),
           ("orb", "orb.png", False),
           ("wall", "wallpape.jpg", False)]


def mkimgd(name, path, rltile):
    return {
        'name': name,
        'path': path,
        'rltile': rltile}

imgs = [mkimgd(*tup) for tup in imgtups]

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


def mkspotd(dim, name, sprite, x, y, visible, interactive):
    return {
        'dimension': dim,
        'place': name,
        'img': sprite,
        'x': x,
        'y': y,
        'visible': visible,
        'interactive': interactive}


spots = [mkspotd(*stup) for stup in spottups]


def mkpawnd(dim, thing, img, vis=True, intr=True):
    return {
        'dimension': dim,
        'thing': thing,
        'img': img,
        'visible': vis,
        'interactive': intr}


pawntups = [
    (dimname, 'me', 'troll_m'),
    (dimname, 'mom', 'zruty')]


pawns = [mkpawnd(*tup) for tup in pawntups]


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
menus = [gamemenu, editormenu, placemenu, thingmenu, mainmenu]

boards = {
    'dimension': dimname,
    'width': 800,
    'height': 600,
    'wallpaper': 'wallpape'}

board_menu = [
    (dimname, 'Main'),
    (dimname, 'Thing'),
    (dimname, 'Place'),
    (dimname, 'Editor'),
    (dimname, 'Thing')]
