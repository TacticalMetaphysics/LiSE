class Schedule:
    def __init__(self, dimension, item, age, events, db=None):
        self.dimension = dimension
        self.item = item
        self.age = age
        self.events = events
        if db is not None:
            if dimension not in db.scheduledict:
                db.scheduledict[dimension] = {}
            db.scheduledict[dimension][item] = self

    def unravel(self, db):
        self.dimension = db.dimensiondict[self.dimension]
        self.item = db.itemdict[self.dimension.name][self.item]
        for event in self.events:
            start = event["start"]
            length = event["length"]
            event = db.eventdict[event]
            event.start = start
            event.length = length

    def __getitem__(self, n):
        return self.startevs[n]

    def advance(self, n):
        # advance time by n ticks
        prior_age = self.age
        new_age = prior_age + n
        starts = [self.startevs[i] for i in xrange(prior_age, new_age)]
        for start in starts:
            start.start()
        ends = [self.endevs[i] for i in xrange(prior_age, new_age)]
        for end in ends:
            end.end()
        self.age = new_age
