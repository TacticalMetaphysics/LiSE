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
except IOError:
    pass

db = database.Database(DB_NAME)

for clas in tabclasses:
    for tab in clas.schemata:
        print tab
        db.c.execute(tab)

db.c.execute("CREATE TABLE game (age INTEGER);")

db.c.close()
db.conn.commit()
