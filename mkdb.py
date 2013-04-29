import database
from dimension import Dimension
from schedule import Schedule
from item import Item, Thing, Place, Portal
from journey import Journey
from effect import Effect, EffectDeck
from event import Event
from style import Color, Style
from menu import Menu, MenuItem

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
