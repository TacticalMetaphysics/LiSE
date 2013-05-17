import pyglet
from gui import GameWindow
from database import load_game
from state import GameState
from board import load_board


db = load_game("default.sqlite", "English")
b = load_board(db, "Physical")
s = GameState(db)
gw = GameWindow(s, "Physical")
pyglet.clock.schedule_interval(s.update, 1/60., 1/60.)
pyglet.app.run()
