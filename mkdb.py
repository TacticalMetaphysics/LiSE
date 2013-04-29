import database
from dimension import Dimension
from schedule import Schedule
from item import Item, Thing, Place, Portal
from journey import Journey
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

db = database.Database('empty.sqlite')

for clas in tabclasses:
    for tab in clas.schemata:
        print tab
        db.c.execute(tab)

del db
