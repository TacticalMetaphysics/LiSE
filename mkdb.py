import rumor
import os
from sqlite3 import OperationalError
from rltileins import ins_rltiles
from util import schemata


"""Make an empty database of LiSE's schema. By default it will be
called default.sqlite and include the RLTiles (in folder
./rltiles). Put sql files in the folder ./init and they'll be executed
in their sort order, after the schema is defined.

"""


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

db = rumor.RumorMill(DB_NAME)


done = set()

while schemata != []:
    (tabn, reqs, schema) = schemata.pop()
    if tabn in done:
        continue
    for req in reqs:
        if req not in done:
            schemata.insert(0, (tabn, reqs, schema))
            continue
    print "creating " + tabn
    try:
        db.c.execute(schema)
        done.add(tabn)
    except OperationalError as oe:
        raise OperationalError(
            str(oe) + " while trying to execute: \n" + schema)

oldhome = os.getcwd()
os.chdir('sql')
initfiles = sorted(os.listdir('.'))
for initfile in initfiles:
    if initfile[-3:] == "sql":  # weed out automatic backups and so forth
        print "reading SQL from file " + initfile
        read_sql(db, initfile)

os.chdir(oldhome)

ins_rltiles(db.c, 'rltiles')

db.c.close()
db.conn.commit()
