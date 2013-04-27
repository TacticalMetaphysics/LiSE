from database import Database
from unittest import TestCase
from world import Place, Portal, Thing
from widgets import Color, Style
from util import default

db = Database(":memory:")
db.mkschema(default)
db.insert_defaults(default)
