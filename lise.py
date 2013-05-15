import pyglet
from gui import GameWindow
from database import Database
from state import GameState
from board import load_board


db = Database("default.sqlite")
b = load_board(db, "Physical")
s = GameState([b.dimension])
gw = GameWindow(db, s, "Physical")
pyglet.app.run()
