from util import SaveableMetaclass, dictify_row, stringlike


__metaclass__ = SaveableMetaclass


class Effect:
    """Curry a function name and a string argument.

    This is actually still good for function calls that don't have any
    effect. It's named this way because it's linked from the event
    table, which does in fact use these to describe effects.

    """
    tables = [
        ("effect",
         {"name": "text",
          "func": "text",
          "arg": "text"},
         ("name",),
         {},
         [])]

    def __init__(self, name, func, arg, db):
        self.name = name
        self.func = func
        self.arg = arg
        if db is not None:
            db.effectdict[name] = self

    def unravel(self, db):
        if stringlike(self.func):
            self.func = db.func[self.func]

    def do(self):
        return self.func(self.arg)


class EffectDeck:
    tables = [
        ("effect_deck_link",
         {"deck": "text",
          "idx": "integer",
          "effect": "text"},
         ("deck", "idx"),
         {"effect": ("effect", "name")},
         [])]

    def __init__(self, name, effects, db=None):
        self.name = name
        self.effects = effects
        if db is not None:
            db.effectdeckdict[self.name] = self

    def unravel(self, db):
        for effn in self.effects:
            if stringlike(effn):
                effn = db.effectdict[effn]

    def do(self):
        return [effect.do() for effect in self.effects]


load_effect_qryfmt = (
    "SELECT {0} FROM effect WHERE name IN ({1})".format(
        ", ".join(Effect.colnames["effect"]), "{0}"))


def read_effects(db, names):
    qryfmt = load_effect_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
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
    for row in db.c:
        rowdict = dictify_row(row, effect_join_cols)
        rowdict["db"] = db
        effectnames.add(rowdict["effect"])
        if rowdict["deck"] not in r:
            r[rowdict["deck"]] = []
        short = rowdict["idx"] + 1 - len(r[rowdict["deck"]])
        if short > 0:
            nothing = [None] * short
            r[rowdict["deck"]].extend(nothing)
        r[rowdict["deck"]][rowdict["idx"]] = rowdict["effect"]
    efs = load_effects(db, list(effectnames))
    for effect_deck in r.iteritems():
        (deckname, effects) = effect_deck
        i = 0
        while i < len(effects):
            effects[i] = efs[effects[i]]
            i += 1
        r[deckname] = EffectDeck(deckname, effects, db)
    return r


def unravel_effect_decks(db, efd):
    for deck in efd.itervalues():
        deck.unravel(db)
    return efd


def load_effect_decks(db, names):
    return unravel_effect_decks(db, read_effect_decks(db, names))
