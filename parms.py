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

menu_items = [game_menu_items, editor_menu_items, place_menu_items,
              thing_menu_items, main_menu_items]


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

styles = [
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

ths = [('me', 'myroom'),
       ('diningtable', 'diningoffice'),
       ('mydesk', 'myroom'),
       ('mybed', 'myroom'),
       ('bustedchair', 'myroom'),
       ('sofas', 'livingroom'),
       ('fridge', 'kitchen'),
       ('momsbed', 'momsroom'),
       ('mom', 'momsroom')]
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

steps = steps_to_kitchen + steps_outside

imgtups = [("troll_m", "rltiles/player/base/troll_m.bmp", True),
           ("zruty", "rltiles/nh-mon0/z/zruty.bmp", True),
           ("orb", "orb.png", False),
           ("wall", "wallpape.jpg", False)]


spots = [
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


nrpos = [('guestroom', 'outside'),
         ('diningoffice', 'outside'),
         ('momsroom', 'outside')]


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


menus = [(gamemenu, game_menu_items),
         (editormenu, editor_menu_items),
         (placemenu, place_menu_items),
         (thingmenu, thing_menu_items),
         (mainmenu, main_menu_items)]
