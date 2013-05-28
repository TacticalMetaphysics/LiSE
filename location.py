class LocationException(Exception):
    pass


class ContainmentException(Exception):
    """Exception raised when a Thing tried to go into or out of another
Thing, and it made no sense.

    """
    pass


class PortalException(Exception):
    """Exception raised when a Thing tried to move into or out of or along
a Portal, and it made no sense."""
    pass


class Location:
    """Behaves just like the place (or thing, or portal) where a given
thing is presently located.

real is an attribute that exposes the underlying simulation object.

    """
    def __init__(self, db, dimname, itemname):
        if dimname not in db.locdict:
            db.locdict[dimname] = {}
        if itemname not in db.locdict[dimname]:
            db.locdict[dimname][itemname] = None
        self.db = db
        self.dimname = dimname
        self.itemname = itemname
        self.__setattr__ = lambda self, attr, val: setattr(self.db.locdict[self.dimname][self.itemname], attr, val)

    def __getattr__(self, attr):
        if attr == 'real':
            return self.db.locdict[self.dimname][self.itemname]
        else:
            return getattr(self.db.locdict[self.dimname][self.itemname], attr)

class LocationWiseDict(dict):
    """Behaves just like a regular dictionary, but when you try to assign
a Location object it will take the underlying place or thing or portal
instead."""
    def __setitem__(self, key, val):
        print "setting {0} to {1}".format(key, val)
        if isinstance(val, Location):
            val = val.real
        dict.__setitem__(self, key, val)
