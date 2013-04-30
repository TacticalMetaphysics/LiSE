from util import SaveableMetaclass, dictify_row


__metaclass__ = SaveableMetaclass


class Effect:
    """Curry a function name and a string argument.

    This is actually still good for function calls that don't have any
    effect. It's named this way because it's linked from the event
    table, which does in fact use these to describe effects.

    """
    tablenames = ["effect"]
    coldecls = {
        "effect":
        {"name": "text",
         "func": "text",
         "arg": "text"}}
    primarykeys = {
        "effect": ("name", "func", "arg")}



    def __init__(self, name, func, arg, db=None):
        self.name = name
        self.func = func
        self.arg = arg
        if db is not None:
            db.effectdict[name] = self

    def unravel(self, db):
        self.func = db.func[self.func]

    def do(self):
        return self.func(self.arg)


class EffectDeck:
    tablenames = ["effect_deck", "effect_deck_link"]
    coldecls = {
        "effect_deck":
        {"name": "text"},
        "effect_deck_link":
        {"deck": "text",
         "idx": "integer",
         "effect": "text"}}
    primarykeys = {
        "effect_deck": ("name",),
        "effect_deck_link": ("deck", "idx")}
    foreignkeys = {
        "effect_deck_link":
        {"deck": ("effect_deck", "name"),
         "effect": ("effect", "name")}}

    def pull(self, db, keydicts):
        names = [keydict["name"] for keydict in keydicts]
        return self.pull_named(db, names)

    def pull_named(self, db, names):
        qryfmt = (
            "SELECT {0} FROM effect_deck, effect_deck_link WHERE "
            "effect_deck.name=effect_deck_link.deck AND "
            "effect_deck.name IN ({1})")
        cols = self.colnames["effect_deck_link"]
        colns = ["effect_deck_link." + coln for coln in cols]
        qrystr = qryfmt.format(
            ", ".join(colns), ", ".join(["?"] * len(names)))
        db.c.execute(qrystr, names)
        return self.parse([
            dictify_row(cols, row) for row in db.c])

    def parse(self, rows):
        r = {}
        for row in rows:
            if row["deck"] not in r:
                r[row["deck"]] = {}
            r[row["deck"]][row["idx"]] = row
        return r

    def combine(self, effect_deck_dict, effect_dict):
        r = {}
        for item in effect_deck_dict.iteritems():
            (deck, cards) = item
            r[deck] = []
            i = 0
            while i < len(cards):
                card = cards[i]
                effect_name = card["effect"]
                effect = effect_dict[effect_name]
                r[deck].append(effect)
        return r

    def __init__(self, name, effects, db=None):
        self.name = name
        self.effects = effects
        if db is not None:
            db.effectdeckdict[name] = self

    def unravel(self, db):
        for effect in self.effects:
            effect = db.effectdict[effect]


effect_join_colns = [
    "effect_deck_link." + coln for coln in
    EffectDeck.colnames["effect_deck_link"]]
effect_join_colns += [
    "effect." + coln for coln in
    Effect.valnames["effect"]]
effect_join_cols = (
    EffectDeck.colnames["effect_deck_link"] +
    Effect.valnames["effect"])

efjoincolstr = ", ".join(effect_join_colns)


def pull_deck(db, name):
    return pull_decks(db, [name])


def pull_decks(db, names):
    qryfmt = (
        "SELECT {0} FROM effect, effect_deck_link WHERE "
        "effect.name=effect_deck_link.effect AND "
        "effect_deck_link.deck IN ({1})")
    qrystr = qryfmt.format(efjoincolstr, ", ".join(["?"] * len(names)))
    db.c.execute(qrystr, names)
    r = {}
    for row in db.c:
        rowdict = dictify_row(row, effect_join_cols)
        if rowdict["deck"] not in r:
            r[rowdict["deck"]] = {}
        r[rowdict["deck"]][rowdict["idx"]] = rowdict
    return r


def parse_decks(rows):
    r = {}
    for row in rows:
        if row["deck"] not in r:
            r[row["deck"]] = {}
        r[row["deck"]][row["effect"]] = row
    return r


def pull(self, db, keydicts):
    efnames = [keydict["name"] for keydict in keydicts]
    return pull_named(db, efnames)


def pull_named(db, efnames):
    qryfmt = "SELECT {0} FROM effect WHERE name IN ({1})"
    qrystr = qryfmt.format(
        Effect.colnamestr["effect"],
        ", ".join(["?"] * len(efnames)))
    db.c.execute(qrystr, efnames)
    r = {}
    for row in db.c:
        rowdict = dictify_row(row, Effect.colnames["effect"])
        r[rowdict["name"]] = rowdict
    return r
