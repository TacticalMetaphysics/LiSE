import database
import os
from dimension import Dimension
from item import Item, Thing, Place, Portal, Schedule, Journey
from effect import Effect, EffectDeck
from event import Event, EventDeck
from style import Color, Style
from menu import Menu, MenuItem
from img import Img
from calendar import CalendarCol
from spot import Spot
from pawn import Pawn
from board import Board

tabclasses = [
    Dimension,
    Schedule,
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
        db.c.execute(tab)

game_decl = """CREATE TABLE game
 (front_board TEXT DEFAULT 'Physical', age INTEGER DEFAULT 0,
 seed INTEGER DEFAULT 0);"""
strs_decl = """CREATE TABLE strings (stringname TEXT, language TEXT,
 string TEXT, PRIMARY KEY(stringname, language));"""
extratabs = [game_decl, strs_decl]

for extratab in extratabs:
    db.c.execute(extratab)

db.c.close()
db.conn.commit()
