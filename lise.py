import pyglet
from gui import GameWindow
from database import Database
from state import GameState
from board import load_board


db = Database("default.sqlite")
b = load_board(db, "Physical")
s = GameState(db)
gw = GameWindow(s, "Physical")
pyglet.clock.schedule_interval(s.update, 1/60., 1/60.)
pyglet.app.run()
