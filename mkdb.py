import database
import os
from item import Item, Thing, Place, Portal, Schedule, Journey
from character import Character
from effect import Effect, EffectDeck
from event import Event, EventDeck
from style import Color, Style
from menu import Menu, MenuItem
from img import Img
from calendar import CalendarCol
from spot import Spot
from pawn import Pawn
from board import Board
from sqlite3 import OperationalError

tabclasses = [
    Schedule,
    Character,
    Item,
    Thing,
    Place,
    Portal,
    Journey,
    Effect,
    EffectDeck,
    Event,
    EventDeck,
    Img,
    Color,
    Style,
    Menu,
    MenuItem,
    CalendarCol,
    Spot,
    Pawn,
    Board]

DB_NAME = 'empty.sqlite'

try:
    os.remove(DB_NAME)
except OSError:
    pass

db = database.Database(DB_NAME)

for clas in tabclasses:
    for tab in clas.schemata:
        try:
            db.c.execute(tab)
        except OperationalError as oe:
            raise Exception(repr(oe) + "\n" + tab)

game_decl = """CREATE TABLE game
 (front_board TEXT DEFAULT 'Physical', age INTEGER DEFAULT 0,
 seed INTEGER DEFAULT 0);"""
strs_decl = """CREATE TABLE strings (stringname TEXT, language TEXT,
 string TEXT, PRIMARY KEY(stringname, language));"""
place_trig_ins = """CREATE TRIGGER name_place BEFORE INSERT ON place
BEGIN
INSERT INTO item (dimension, name) VALUES (NEW.dimension, NEW.name);
END"""
port_trig_ins = """CREATE TRIGGER name_portal BEFORE INSERT ON portal 
BEGIN
INSERT INTO item (dimension, name)
VALUES (NEW.dimension, 'Portal('||NEW.from_place||'->'||NEW.to_place||')');
END"""
thing_trig_ins = """CREATE TRIGGER name_thing BEFORE INSERT ON thing
BEGIN
INSERT INTO item (dimension, name) VALUES (NEW.dimension, NEW.name);
END"""
port_trig_upd = """CREATE TRIGGER move_portal BEFORE UPDATE OF
from_place, to_place ON portal
BEGIN
UPDATE item SET name='Portal('||NEW.from_place||'->'||NEW.to_place||')'
WHERE dimension=old.dimension AND name='Portal('||OLD.from_place||'->'||OLD.to_place||')';
END"""
place_trig_del = """CREATE TRIGGER del_place AFTER DELETE ON place
BEGIN
DELETE FROM item WHERE dimension=OLD.dimension AND name=OLD.name;
END"""
port_trig_del = """CREATE TRIGGER del_port AFTER DELETE ON portal
BEGIN
DELETE FROM item WHERE dimension=OLD.dimension AND
name='Portal('||OLD.from_place||'->'||OLD.to_place||')';
END"""
thing_trig_del = """CREATE TRIGGER del_thing AFTER DELETE ON thing
BEGIN
DELETE FROM item WHERE dimension=OLD.dimension AND name=OLD.name;
END"""

extratabs = (game_decl, strs_decl, port_trig_ins, port_trig_upd, place_trig_ins, thing_trig_ins, place_trig_del, port_trig_del, thing_trig_del)

for extratab in extratabs:
    try:
        db.c.execute(extratab)
    except OperationalError as ope:
        raise Exception(repr(ope) + "\n" + extratab)

db.c.close()
db.conn.commit()
