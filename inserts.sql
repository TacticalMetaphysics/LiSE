INSERT INTO game DEFAULT VALUES;
INSERT INTO board DEFAULT VALUES;
INSERT INTO color (name, red, green, blue) VALUES
('solarized-blue', 210, 139, 38),
('solarized-base01', 117, 110, 88),
('solarized-base00', 131, 123, 101),
('solarized-base03', 54, 43, 0),
('solarized-base02', 66, 54, 7),
('solarized-yellow', 0, 137, 181),
('solarized-base0', 150, 148, 131),
('solarized-base1', 161, 161, 147),
('solarized-base2', 213, 232, 238),
('solarized-base3', 227, 246, 253),
('solarized-green', 0, 153, 133),
('solarized-violet', 196, 113, 108),
('solarized-orange', 22, 75, 203),
('solarized-cyan', 152, 161, 42),
('solarized-magenta', 130, 54, 211),
('solarized-red', 47, 50, 220);
INSERT INTO style
(name, fontface, fontsize, spacing,
bg_inactive, bg_active, fg_inactive, fg_active) VALUES
    ('BigDark',
     'DejaVu Sans', 16, 6,
     'solarized-base03',
     'solarized-base2',
     'solarized-base1',
     'solarized-base01'),
    ('SmallDark',
     'DejaVu Sans', 8, 3,
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
     'DejaVu Serif', 8, 3,
     'solarized-base3',
     'solarized-base02',
     'solarized-base01',
     'solarized-base1');
INSERT INTO place (name) VALUES
('myroom'),
('guestroom'),
('mybathroom'),
('livingroom'),
('diningoffice'),
('outside'),
('kitchen'),
('longhall'),
('momsroom'),
('momsbathroom');
INSERT INTO thing (name, location) VALUES
('me', 'myroom'),
('diningtable', 'diningoffice'),
('mydesk', 'myroom'),
('mybed', 'myroom'),
('bustedchair', 'myroom'),
('sofas', 'livingroom'),
('fridge', 'kitchen'),
('momsbed', 'momsroom'),
('mom', 'momsroom');
INSERT INTO portal (from_place, to_place) VALUES
('myroom', 'guestroom'),
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
        ('longhall', 'momsroom');
INSERT INTO portal (to_place, from_place) SELECT from_place, to_place FROM portal;
INSERT INTO portal (from_place, to_place) VALUES
('guestroom', 'outside'),
         ('diningoffice', 'outside'),
         ('momsroom', 'outside'),
         ('myroom', 'outside');
INSERT INTO journey_step (thing, idx, from_place, to_place) VALUES
('me', 0, 'myroom', 'diningoffice'),
('me', 1, 'diningoffice', 'kitchen'),
('mom', 0, 'momsroom', 'longhall'),
('mom', 1, 'longhall', 'livingroom'),
('mom', 2, 'livingroom', 'diningoffice'),
('mom', 3, 'diningoffice', 'outside');
INSERT INTO calendar_col (item) VALUES 
('me'),
('mom');
INSERT INTO effect (name, func) VALUES
('start_new_map()', 'start_new_map'),
('open_map()', 'open_map'),
('quit_map_editor()', 'quit_map_editor'),
('save_map()', 'save_map'),
('editor_select()', 'editor_select'),
('editor_copy()', 'editor_copy'),
('editor_paste()', 'editor_paste'),
('editor_delete()', 'editor_delete');
INSERT INTO easy_effect VALUES
('new_place', 'commons'),
('new_place', 'lair'),
('new_place', 'custom'),
('new_place', 'workplace'),
('new_thing', 'custom'),
('new_thing', 'tool'),
('new_thing', 'clothing'),
('new_thing', 'decoration'),
('toggle_menu', 'Thing'),
('toggle_menu', 'Game'),
('toggle_menu', 'Editor'),
('toggle_menu', 'Place');
INSERT INTO effect_deck_link (deck, idx, effect)
SELECT name, 0, name FROM effect;
INSERT INTO menu (name, bottom, left, right, top, main_for_window, style, visible) VALUES
('Main', 0.12, 0.0, 0.1, 1.0, 1, 'BigLight', 1);
INSERT INTO menu (name) VALUES ('Game'), ('Editor'), ('Place'), ('Thing');
INSERT INTO menu_item (idx, menu, closer, effect_deck, text) VALUES
(0, 'Game', 1, 'start_new_map()', '@new_map'),
(1, 'Game', 1, 'open_map()', '@open_map'),
(2, 'Game', 1, 'quit_map_editor()', '@quit_maped'),
(3, 'Game', 1, 'save_map()', '@save_map'),
(0, 'Editor', 1, 'editor_select()', '@ed_select'),
(1, 'Editor', 1, 'editor_copy()', '@ed_copy'),
(2, 'Editor', 1, 'editor_paste()', '@ed_paste'),
(3, 'Editor', 1, 'editor_delete()', '@ed_delete'),
(0, 'Place', 1, 'new_place(commons)', '@commonplace'),
(1, 'Place', 1, 'new_place(lair)', '@lairplace'),
(2, 'Place', 1, 'new_place(custom)', '@custplace'),
(3, 'Place', 1, 'new_place(workplace)', '@workplace'),
(0, 'Thing', 1, 'new_thing(custom)', '@custthing'),
(1, 'Thing', 1, 'new_thing(tool)', '@toolthing'),
(2, 'Thing', 1, 'new_thing(clothing)', '@clothing'),
(3, 'Thing', 1, 'new_thing(decoration)', '@decorthing'),
(0, 'Main', 0, 'toggle_menu(Thing)', '@thing_menu'),
(1, 'Main', 0, 'toggle_menu(Game)', '@game_menu'),
(2, 'Main', 0, 'toggle_menu(Editor)', '@editor_menu'),
(3, 'Main', 0, 'toggle_menu(Place)', '@place_menu');
INSERT INTO spot (place, x, y) VALUES
('myroom', 400, 100),
('mybathroom', 450, 150),
('guestroom', 400, 200),
('livingroom', 300, 150),
('diningoffice', 350, 200),
('kitchen', 350, 150),
('longhall', 250, 150),
('momsroom', 250, 100),
('momsbathroom', 250, 200),
('outside', 300, 100);
INSERT INTO pawn (thing) VALUES ('me'), ('mom');
INSERT INTO img (name, path) VALUES 
('default_wallpaper', 'wallpape.jpg'),
('default_spot', 'orb.png');
INSERT INTO strings (stringname, string) VALUES
('game_menu', 'Game'),
('editor_menu', 'Editor'),
('place_menu', 'Place'),
('thing_menu', 'Thing'),
('new_map', 'New world'),
('open_map', 'Open world...'),
('save_map', 'Save'),
('quit_maped', 'Quit'),
('ed_select', 'Select...'),
('ed_copy', 'Copy'),
('ed_paste', 'Paste'),
('ed_delete', 'Delete...'),
('custplace', 'New place...'),
('workplace', 'New workplace...'),
('commonplace', 'New commons...'),
('lairplace', 'New lair...'),
('custthing', 'New thing...'),
('decorthing', 'New decoration...'),
('clothing', 'New clothing...'),
('toolthing', 'New tool...');
