from util import SaveableMetaclass, dictify_row, stringlike


class Effect:
    __metaclass__ = SaveableMetaclass
    """Curry a function name and a string argument.

    This is actually still good for function calls that don't have any
    effect. It's named this way because it's linked from the event
    table, which does in fact use these to describe effects.

    """
    tables = [
        ("effect",
         {"name": "text not null",
          "func": "text not null",
          "arg": "text not null"},
         ("name",),
         {},
         [])]

    def __init__(self, name, func, arg,  db=None):
        """Return an Effect of the given name, where the given function is
called with the given argument. If a database is supplied, register in
its effectdict."""
        if name is None:
            name = "{0}({1})".format(func, arg)
        self.name = name
        self.func = func
        self.arg = arg
        if db is not None:
            db.effectdict[name] = self

    def get_rowdict(self):
        return {
            "name": self.name,
            "func": self.func,
            "arg": self.arg}

    def get_tabdict(self):
        return {
            "effect": self.get_rowdict()}

    def unravel(self, db):
        if stringlike(self.func):
            self.func = db.func[self.func]

    def do(self):
        return self.func(self.arg)


NULL_EFFECT = Effect("null", "noop", "nope")


class PortalEntryEffect(Effect):
    """Effect to put an item in a portal when it wasn't before."""
    def __init__(self, item, portal, db=None):
        assert(item.dimension == portal.dimension)
        self.item = item
        self.portal = portal
        dimname = item.dimension.name
        arg = "{0}.{1}->{2}".format(dimname, item.name, portal.name)
        name = "thing_into_portal({0})".format(arg)
        Effect.__init__(self, name, "thing_into_portal", arg, db)


class PortalProgressEffect(Effect):
    """Effect to move a thing some distance along a portal, but not out of
it."""
    def __init__(self, item, db=None):
        self.item = item
        arg = "{0}.{1}".format(item.dimension.name, item.name)
        name = "thing_along_portal({0})".format(arg)
        Effect.__init__(self, name, "thing_along_portal", arg, db)


class PortalExitEffect(Effect):
    """Effect to put an item into the destination of a portal it's already
in, incidentally taking it out of the portal."""
    def __init__(self, item, db=None):
        self.item = item
        self.portal = item.location.getreal()
        arg = "{0}.{1}".format(item.dimension.name, item.name)
        name = "thing_out_of_portal({0})".format(arg)
        Effect.__init__(self, name, "thing_out_of_portal", arg, db)


class EffectDeck:
    __metaclass__ = SaveableMetaclass
    tables = [
        ("effect_deck_link",
         {"deck": "text not null",
          "idx": "integer not null",
          "effect": "text not null"},
         ("deck", "idx"),
         {"effect": ("effect", "name")},
         [])]

    def __init__(self, name, effects, db=None):
        self.name = name
        self.effects = effects
        if db is not None:
            db.effectdeckdict[self.name] = self

    def get_tabdict(self):
        rowdicts = []
        for i in xrange(0, len(self.effects)):
            rowdicts.append({
                "deck": self.name,
                "idx": i,
                "effect": self.effects[i].name})
        return {"effect_deck_link": rowdicts}

    def unravel(self, db):
        for effn in self.effects:
            if stringlike(effn):
                effn = db.effectdict[effn]

    def do(self):
        return [effect.do() for effect in self.effects]


class PortalEntryEffectDeck(EffectDeck):
    def __init__(self, item, portal, db=None):
        effect = PortalEntryEffect(item, portal, db)
        EffectDeck.__init__(self, effect.name, [effect], db)


class PortalProgressEffectDeck(EffectDeck):
    def __init__(self, item, amount, db=None):
        effect = PortalProgressEffect(item, amount, db)
        EffectDeck.__init__(self, effect.name, [effect], db)


class PortalExitEffectDeck(EffectDeck):
    def __init__(self, item, amount, db=None):
        effect = PortalExitEffect(item, amount, db)
        EffectDeck.__init__(self, effect.name, [effect], db)


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


def make_toggle_menu_effect(boardname, menuname, db):
    menuspec = boardname + "." + menuname
    return make_toggle_menu_effect_from_menuspec(menuspec, db)


def make_toggle_menu_effect_from_menuspec(menuspec, db):
    togglername = "toggle_menu_visibility({0})".format(menuspec)
    toggler = Effect(togglername, "toggle_menu_visibility", menuspec, db)
    toggler.unravel(db)
    return toggler


def make_toggle_calendar_effect(dimname, itname, db):
    calspec = dimname + "." + itname
    return make_calendar_toggle_effect_from_calspec(calspec, db)


def make_toggle_calendar_effect_from_calspec(calspec, db):
    togglername = "toggle_calendar_visibility({0})".format(calspec)
    toggler = Effect(togglername, "toggle_calendar_visibility", calspec, db)
    toggler.unravel(db)
    return toggler


def make_hide_menu_effect(boardname, menuname, db):
    menuspec = boardname + "." + menuname
    return make_hide_menu_effect_from_menuspec(menuspec, db)


def make_hide_menu_effect_from_menuspec(menuspec, db):
    hidername = "hide_menu({0})".format(menuspec)
    hider = Effect(hidername, "hide_menu", menuspec, db)
    hider.unravel(db)
    return hider


def make_show_menu_effect(boardname, menuname, db):
    menuspec = boardname + "." + menuname
    return make_show_menu_effect_from_menuspec(menuspec, db)


def make_show_menu_effect_from_menuspec(menuspec, db):
    showername = "show_menu({0})".format(menuspec)
    shower = Effect(showername, "show_menu", menuspec, db)
    shower.unravel(db)
    return shower


def make_hide_calendar_effect(dimname, itname, db):
    calspec = dimname + "." + itname
    return make_hide_calendar_effect_from_calspec(calspec, db)


def make_hide_calendar_effect_from_calspec(calspec, db):
    hidername = "hide_calendar({0})".format(calspec)
    hider = Effect(hidername, "hide_calendar", calspec, db)
    hider.unravel(db)
    return hider


def make_show_calendar_effect(dimname, itname, db):
    calspec = dimname + "." + itname
    return make_show_calendar_effect_from_calspec(calspec, db)


def make_show_calendar_effect_from_calspec(calspec, db):
    showername = "show_calendar({0})".format(calspec)
    shower = Effect(showername, "show_calendar", calspec, db)
    shower.unravel(db)
    return shower


def make_hide_all_menus_effect(boardname, db):
    # WON'T hide the main_for_window menu
    hidername = "hide_menus_in_board({0})".format(boardname)
    hider = Effect(hidername, "hide_menus_in_board", boardname, db)
    hider.unravel(db)
    return hider


def make_hide_other_menus_effect(boardn, menun, db):
    menuspec = boardn + "." + menun
    hidername = "hide_other_menus_in_board({0})".format(menuspec)
    hider = Effect(hidername, "hide_other_menus_in_board", menuspec, db)
    hider.unravel(db)
    return hider


def make_hide_all_calendars_effect(dimname, db):
    hidername = "hide_calendars_in_board({0})".format(dimname)
    hider = Effect(hidername, "hide_calendars_in_board", dimname, db)
    hider.unravel(db)
    return hider


def make_hide_other_calendars_effect(dimname, itname, db):
    calspec = dimname + "." + itname
    hidername = "hide_other_calendars_in_board({0})".format(calspec)
    hider = Effect(hidername, "hide_other_calendars_in_board", calspec, db)
    hider.unravel(db)
    return hider


def make_show_only_menu_effect_deck(boardname, menuname, db):
    hider = make_hide_all_menus_effect(boardname, db)
    shower = make_show_menu_effect(boardname, menuname, db)
    deckname = "show_only_menu({0}.{1})".format(boardname, menuname)
    deck = EffectDeck(deckname, [hider, shower], db)
    deck.unravel(db)
    return deck


def make_show_only_calendar_effect_deck(dimname, itname, db):
    hider = make_hide_all_calendars_effect(dimname, db)
    shower = make_show_calendar_effect(dimname, itname, db)
    deckname = "show_only_calendar({0}.{1})".format(dimname, itname)
    deck = EffectDeck(deckname, [hider, shower], db)
    deck.unravel(db)
    return deck


def make_menu_toggler(boardname, menuname, db):
    hide_effect = make_hide_other_menus_effect(boardname, menuname, db)
    toggle_effect = make_toggle_menu_effect(boardname, menuname, db)
    deckname = "toggle_menu_visibility({0}.{1})".format(boardname, menuname)
    deck = EffectDeck(deckname, [hide_effect, toggle_effect], db)
    deck.unravel(db)
    return deck


def make_calendar_toggler(dimname, itname, db):
    hide_effect = make_hide_all_calendars_effect(dimname, db)
    deckname = "toggle_calendar_visibility({0}.{1})".format(dimname, itname)
    deck = EffectDeck(deckname, [hide_effect, toggle_effect], db)
    deck.unravel(db)
    return deck
