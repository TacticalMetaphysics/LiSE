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
