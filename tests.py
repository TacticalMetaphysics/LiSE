from database import Database
from unittest import TestCase
from parms import DefaultParameters
from graph import Place, Portal
from widgets import Color, Style
from attrcheck import AttrCheck
from thing import Thing


default = DefaultParameters()


class Attribution:
    def __init__(self, typ, perm, lo, hi):
        self.typ = typ
        self.perm = perm
        self.lo = lo
        self.hi = hi

    def __eq__(self, other):
        return self.typ == other.typ and\
            self.perm == other.perm and\
            self.lo == other.lo and\
            self.hi == other.hi


class DatabaseTestCase(TestCase):
    def testSomething(self, db, suf, clas, keytup, valtup, testname):
        # clas is the class of object to test.  keytup is a tuple
        # of the primary key to use. valtup is a tuple of the rest
        # of the record to use. testSomething will make the record
        # for that key and those values and test that stuff done
        # with the record is correct. I've assumed that keytup
        # concatenated with valtup
        mkargs = list(keytup)+list(valtup)
        print "mkargs = " + str(mkargs)
        knower = getattr(db, 'know'+suf)
        writer = getattr(db, 'write'+suf)
        saver = getattr(db, 'save'+suf)
        killer = getattr(db, 'del'+suf)
        loader = getattr(db, 'load'+suf)
        if testname == 'make':
            writer(*mkargs)
            self.assertTrue(knower(*keytup))
        elif testname == 'save':
            obj = loader(*keytup)
            killer(*keytup)
            saver(obj)
            self.assertTrue(knower(*keytup))
        elif testname == 'get':
            obj = loader(*keytup)
            getter = getattr(db, 'get' + suf)
            writer(*mkargs)
            jbo = getter(*keytup)
            self.assertEqual(obj, jbo)
        elif testname == 'del':
            killer = getattr(db, 'del' + suf)
            writer(*mkargs)
            self.assertTrue(knower(*keytup))
            killer(*keytup)
            self.assertFalse(knower(*keytup))

    def runTest(self):
        testl = ['make', 'save', 'get', 'del', 'make']
        db = Database(":memory:", default.stubs)
        db.mkschema()
        tabkey = [('place', default.places, Place),
                  ('portal', default.portals, Portal),
                  ('thing', default.things, Thing),
                  ('color', default.colors, Color),
                  ('style', default.styles, Style),
                  ('attribute', default.attributes, AttrCheck),
                  ('attribution', default.attributions, Attribution)]
        for pair in tabkey:
            suf = pair[0]
            for val in pair[1]:
                for test in testl:
                    print "Testing %s%s" % (test, suf)
                    self.testSomething(db, suf, pair[2],
                                       val[0], val[1], test)

db = Database(":memory:")
db.mkschema()
db.insert_defaults(default)
