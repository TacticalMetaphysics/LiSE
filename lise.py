import pyglet
from gui import GameWindow
from database import load_game
from state import GameState
from board import load_board
from sys import argv, setrecursionlimit
from sqlite3 import connect, DatabaseError

DEBUG = False

i = 0
lang = "English"
dbfn = "default.sqlite"
for arg in argv:
    if arg == "-l":
        try:
            lang = argv[i+1]
        except:
            raise Exception("Couldn't parse language")
    else:
        try:
            connect(arg).cursor().execute("SHOW TABLES")
            dbfn = arg
        except DatabaseError:
            pass
    i += 1

db = load_game(dbfn, lang)
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
