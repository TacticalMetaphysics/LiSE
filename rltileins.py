import os
import sqlite3
import sys

home = os.getcwd()
def isdir(p):
	try:
		os.chdir(p)
		return True
	except:
		return False
def allsubdirs_core(doing, done):
	if len(doing) == 0:
		return done
	here = doing.pop()
	if isdir(here):
		print "recursing into " + here
		done.add(here + '/')
		inside = [here + '/' + there for there in os.listdir(here) if there[0] != '.']
		doing.update(set(inside))
def allsubdirs(path):
	inpath = os.path.realpath(path)
	indoing = set()
	indoing.add(inpath)
	indone = set()
	result = None
	print "starting with " + str(indoing)
	while result is None:
		result = allsubdirs_core(indoing, indone)
	return iter(result)
db = sqlite3.connect(sys.argv[-2])
curs = db.cursor()
dirs = allsubdirs(sys.argv[-1])
for dir in dirs:
	print "in " + dir
	for bmp in os.listdir(dir):
		if bmp[-4:] != ".bmp":
			print "skipping non-bmp"
			print bmp[-4:]
			continue
		curs.execute('insert or replace into img (name, path, rltile) values (?, ?, ?)', (bmp.replace('.bmp', ""), dir.replace(home, '.') + bmp, True))
curs.close()
db.commit()
