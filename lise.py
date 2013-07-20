import pyglet
import logging
from gui import GameWindow
from rumor import load_game
from state import GameState
from sys import argv
from sqlite3 import connect, DatabaseError

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


i = 0
lang = "English"
dbfn = "default.sqlite"
for arg in argv:
    if arg == "-l":
        try:
            lang = argv[i+1]
        except:
            raise Exception("Couldn't parse language")
    elif arg == "-d":
        DEBUG = True
    elif arg[-2:] != "py":
        try:
            connect(arg).cursor().execute("SELECT * FROM game;")
            dbfn = arg
        except DatabaseError:
            print "Couldn't connect to the database named {0}.".format(arg)
    i += 1

db = load_game(dbfn, lang)
s = GameState(db)
gw = GameWindow(s, "Physical")
pyglet.clock.schedule_interval(s.update, 1/30., 1/30.)
pyglet.app.run()

db.save_game()
db.conn.commit()
