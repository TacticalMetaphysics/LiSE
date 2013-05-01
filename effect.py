from util import SaveableMetaclass, dictify_row, stringlike


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

    def __init__(self, name, effects, db=None):
        self.name = name
        self.effects = effects
        if db is not None:
            db.effectdeckdict[self.name] = self

    def unravel(self, db):
        for effn in self.effects:
            if stringlike(effn):
                effn = db.effectdict[effn]

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


load_effect_qryfmt = (
    "SELECT {0} FROM effect WHERE name IN ({1})".format(
        ", ".join(Effect.colnames["effect"]), "{0}"))


def read_effects(db, names):
    qryfmt = load_effect_qryfmt
    qrystr = qryfmt.format(["?"] * len(names))
    db.c.execute(qrystr, names)
    r = {}
    for row in db.c:
        rowdict = dictify_row(row, Effect.colnames["effect"])
        rowdict["db"] = db
        eff = Effect(**rowdict)
        eff.unravel(db)
        r[rowdict["name"]] = eff
    return r


def unravel_effects(db, effd):
    for eff in effd.itervalues():
        eff.unravel(db)
    return effd


def load_effects(db, names):
    return unravel_effects(db, read_effects(db, names))


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

load_deck_qryfmt = (
    "SELECT {0} FROM effect, effect_deck_link WHERE "
    "effect.name=effect_deck_link.effect AND "
    "effect_deck_link.deck IN ({1})".format(efjoincolstr, "{0}"))


def read_effect_decks(db, names):
    qryfmt = load_deck_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, names)
    r = {}
    effectnames = set()
    if db.c.rowcount > 0:
        for row in db.c:
            rowdict = dictify_row(row, effect_join_cols)
            if rowdict["deck"] not in r:
                r[rowdict["deck"]] = []
            while len(r[rowdict["deck"]]) < rowdict["idx"]:
                r[rowdict["deck"]].append(None)
            r[rowdict["deck"]][rowdict["idx"]] = rowdict["effect"]
            effectnames.add(rowdict["effect"])
        load_effects(db, list(effectnames))
    for deck in r.iteritems():
        (name, cards) = deck
        deck = EffectDeck(name, cards, db)
    return r


def unravel_effect_decks(db, efd):
    for deck in efd.itervalues():
        deck.unravel()
    return efd


def load_effect_decks(db, names):
    return unravel_effect_decks(db, read_effect_decks(db, names))
