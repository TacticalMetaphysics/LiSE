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
from rltileins import ins_rltiles


"""Make an empty database of LiSE's schema. By default it will be
called default.sqlite and include the RLTiles (in folder
./rltiles). Put sql files in the folder ./init and they'll be executed
in their sort order, after the schema is defined.

"""


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

DB_NAME = 'default.sqlite'


def read_sql(db, filen):
    sqlfile = open(filen, "r")
    sql = sqlfile.read()
    sqlfile.close()
    db.c.executescript(sql)


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

oldhome = os.getcwd()
os.chdir('init')
for initfile in sorted(os.listdir('.')):
    if initfile[:-3] == "sql":  # weed out automatic backups and so forth
        read_sql(db, initfile)
os.chdir(oldhome)

ins_rltiles(db.c, 'rltiles')

db.c.close()
db.conn.commit()
