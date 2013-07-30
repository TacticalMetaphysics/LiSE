import pyglet
import logging
from rumor import load_game
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
gw = db.load_window('Main')
def incdb(ticky):
    db.tick += 1
pyglet.clock.schedule_interval(incdb, 1/10.)
pyglet.app.run()
