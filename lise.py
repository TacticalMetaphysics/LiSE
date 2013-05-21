import pyglet
from gui import GameWindow
from database import load_game
from state import GameState
from board import load_board
import logging
from sys import argv

"""Run the map editor.

On the command line, supply the database file name and the
language.

"""

DEBUG = "--debug" in argv

db = load_game("default.sqlite", "English")
b = load_board(db, "Physical")
s = GameState(db)
gw = GameWindow(s, "Physical")
if DEBUG:
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(s.logfmt)
    ch.setFormatter(formatter)
    statelogger = logging.getLogger('state.update')
    statelogger.setLevel(logging.DEBUG)
    statelogger.addHandler(ch)
pyglet.clock.schedule_interval(s.update, 1/60., 1/60.)
pyglet.app.run()
