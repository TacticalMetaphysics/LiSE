from database import Database
from gui import GameWindow
from state import GameState
import pyglet

db = Database("default.sqlite")
db.load_board("Physical")
stat = GameState(db.boarddict)
bat = pyglet.graphics.Batch()
gw = GameWindow(db, stat, "Physical", bat)
