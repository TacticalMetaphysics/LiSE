from util import stringlike

class Contents:
    """A set-like object that contains things in a given place (not necessarily a Place object)."""
    def __init__(self, here, db):
        self.here = here
        if stringlike(self.here.dimension):
            dimname = self.here.dimension
        else:
            dimname = self.here.dimension.name
        if dimname not in db.locdict:
            db.locdict[dimname] = {}
        self.locationdict = db.locdict[dimname]
        self.itemdict = db.itemdict[dimname]

    def __contains__(self, that):
        if stringlike(that):
            thatname = that
        else:
            thatname = that.name
        return self.locationdict[thatname] == self.here

    def __len__(self):
        i = 0
        for item in self.locationdict.iteritems():
            if item[1] == self.here:
                i += 1
        return i

    def __iter__(self):
        r = []
        for pair in self.locationdict.iteritems():
            if pair[1] == self.here:
                r.append(self.itemdict[pair[0]])
        return iter(r)

    def __repr__(self):
        return "{0}.Contents({1})".format(
            repr(self.here),
            ", ".join([repr(it) for it in iter(self)]))

    def add(self, that):
        # incidentally removes that from its present location
        if stringlike(that):
            thatname = that
        else:
            thatname = that.name
        self.locationdict[thatname] = self.here
        
