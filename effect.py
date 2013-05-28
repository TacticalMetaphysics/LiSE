from util import SaveableMetaclass, dictify_row, stringlike


class Effect:
    __metaclass__ = SaveableMetaclass
    """Curry a function name and a string argument.

An effect is a function with a preselected string argument. These are
stored together under a name describing the both of them. The effect
may be fired by calling the do() method.

    """
    tables = [
        ("effect",
         {"name": "text not null",
          "func": "text not null",
          "arg": "text not null default ''"},
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
        """If the function was supplied as a string, look up what it refers
to."""
        if stringlike(self.func):
            self.func = db.func[self.func]

    def do(self):
        """Call the function with the argument."""
        if stringlike(self.func):
            funname = self.func
        else:
            funname = self.func.__name__
        print "Doing effect {0} by calling function {1} on argument {2}".format(self.name, funname, self.arg)
        return self.func(self.arg)


NULL_EFFECT = Effect("null", "noop", "nope")


class PortalEntryEffect(Effect):
    """Effect to put an item in a portal when it wasn't before."""
    def __init__(self, item, portal, db=None):
        self.item = item
        self.portal = portal
        dimname = item.dimension.name
        arg = "{0}.{1}->Portal({2}->{3})".format(dimname, item.name, portal.orig.name, portal.dest.name)
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
        self.portal = item.location.real
        arg = "{0}.{1}".format(item.dimension.name, item.name)
        name = "thing_out_of_portal({0})".format(arg)
        Effect.__init__(self, name, "thing_out_of_portal", arg, db)


class EffectDeck:
    """An ordered collection of Effects that may be executed in a
batch."""
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
        """Return an EffectDeck with the given name, containing the effects in
the given list.

If db is supplied, register with it.

        """
        self.name = name
        self.effects = effects
        if db is not None:
            db.effectdeckdict[self.name] = self

    def __getitem__(self, i):
        return self.effects[i]

    def __setitem__(self, i, to):
        self.effects[i] = to

    def __iter__(self):
        return iter(self.effects)

    def __contains__(self, that):
        return that in self.effects

    def append(self, that):
        self.effects.append(that)

    def insert(self, i, that):
        self.effects.insert(i, that)

    def remove(self, that):
        self.effects.remove(that)

    def pop(self, i=None):
        if i is None:
            return self.effects.pop()
        else:
            return self.effects.pop(i)

    def get_tabdict(self):
        rowdicts = []
        for i in xrange(0, len(self.effects)):
            rowdicts.append({
                "deck": self.name,
                "idx": i,
                "effect": self.effects[i].name})
        return {"effect_deck_link": rowdicts}

    def unravel(self, db):
        """For all the effects I contain, if the effect is actually the *name*
of an effect, look up the real effect object. Then unravel it."""
        i = 0
        while i < len(self.effects):
            eff = self.effects[i]
            if stringlike(eff):
                eff = db.effectdict[eff]
                self.effects[i] = eff
            eff.unravel(db)
            i += 1

    def do(self):
        """Fire all the effects in order."""
        print "Doing EffectDeck " + self.name
        return [effect.do() for effect in self.effects]


class PortalEntryEffectDeck(EffectDeck):
    def __init__(self, item, portal, db=None):
        effect = PortalEntryEffect(item, portal, db)
        EffectDeck.__init__(self, effect.name, [effect], db)


class PortalProgressEffectDeck(EffectDeck):
    def __init__(self, item, db=None):
        effect = PortalProgressEffect(item, db)
        EffectDeck.__init__(self, effect.name, [effect], db)


class PortalExitEffectDeck(EffectDeck):
    def __init__(self, item, db=None):
        effect = PortalExitEffect(item, db)
        EffectDeck.__init__(self, effect.name, [effect], db)


load_effect_qryfmt = (
    "SELECT {0} FROM effect WHERE name IN ({1})".format(
        ", ".join(Effect.colnames["effect"]), "{0}"))


def read_effects(db, names):
    """Read the effects of the given names from disk and construct their
Effect objects, but don't unravel them just yet.

Return a dictionary keyed by name.

    """
    qryfmt = load_effect_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, tuple(names))
    r = {}
    for row in db.c:
        rowdict = dictify_row(row, Effect.colnames["effect"])
        rowdict["db"] = db
        eff = Effect(**rowdict)
        eff.unravel(db)
        r[rowdict["name"]] = eff
    return r


def unravel_effects(db, effd):
    """Unravel the Effect objects output by read_effects."""
    for eff in effd.itervalues():
        eff.unravel(db)
    return effd


def load_effects(db, names):
    """Load the effects by the given names.

Return a dictionary keyed by name.

    """
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
    """Read the effect decks by the given names, including all effects
therein, but don't unravel anything just yet.

Return a dictionary of EffectDeck keyed by name.

    """
    qryfmt = load_deck_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, tuple(names))
    r = {}
    effectnames = set()
    for row in db.c:
        rowdict = dictify_row(row, effect_join_cols)
        rowdict["db"] = db
        effectnames.add(rowdict["effect"])
        if rowdict["name"] not in r:
            r[rowdict["name"]] = EffectDeck(rowdict["name"], [], db)
        ed = r[rowdict["name"]]
        eff = rowdict["effect"]
        idx = rowdict["idx"]
        while len(ed) <= idx:
            ed.append(None)
        ed[idx] = eff
    read_effects(db, effectnames)
    return r


def unravel_effect_decks(db, efd):
    """Unravel the EffectDeck in the dictionary returned by
read_effect_decks.

This incidentally unravels all Effect therein.

    """
    for deck in efd.itervalues():
        deck.unravel(db)
    return efd


def load_effect_decks(db, names):
    """Load all EffectDeck by the given names from disk.

Return a dictionary of EffectDeck, keyed by name."""
    return unravel_effect_decks(db, read_effect_decks(db, names))


def make_toggle_menu_effect(boardname, menuname, db):
    """Return an Effect that toggles the menu in the given board of the
given name."""
    menuspec = boardname + "." + menuname
    return make_toggle_menu_effect_from_menuspec(menuspec, db)


def make_toggle_menu_effect_from_menuspec(menuspec, db):
    """Given a string consisting of a board dimension name, a dot, and a
menu name, return an Effect that toggles the menu of that name in that
board."""
    togglername = "toggle_menu_visibility({0})".format(menuspec)
    toggler = Effect(togglername, "toggle_menu_visibility", menuspec, db)
    toggler.unravel(db)
    return toggler


def make_toggle_calendar_effect(dimname, itname, db):
    """Return an effect that toggles the calendar representing the
schedule of the given item in the given dimension."""
    calspec = dimname + "." + itname
    return make_calendar_toggle_effect_from_calspec(calspec, db)


def make_toggle_calendar_effect_from_calspec(calspec, db):
    """Given a string consisting of a dimension name, a dot, and an item name, return an Effect that toggles the calendar representing the schedule of that item in that dimension."""
    togglername = "toggle_calendar_visibility({0})".format(calspec)
    toggler = Effect(togglername, "toggle_calendar_visibility", calspec, db)
    toggler.unravel(db)
    return toggler


def make_hide_menu_effect(boardname, menuname, db):
    """Return an effect that hides this menu in this board."""
    menuspec = boardname + "." + menuname
    return make_hide_menu_effect_from_menuspec(menuspec, db)


def make_hide_menu_effect_from_menuspec(menuspec, db):
    """Given a string consisting of a board dimension name, a dot, and a
menu name, return an effect that hides that menu in that board."""
    hidername = "hide_menu({0})".format(menuspec)
    hider = Effect(hidername, "hide_menu", menuspec, db)
    hider.unravel(db)
    return hider


def make_show_menu_effect(boardname, menuname, db):
    """Return an effect that shows this menu in this board."""
    menuspec = boardname + "." + menuname
    return make_show_menu_effect_from_menuspec(menuspec, db)


def make_show_menu_effect_from_menuspec(menuspec, db):
    """Given a string consisting of a board dimension name, a dot, and a
menu name, return an effect that shows that menu in that board."""
    showername = "show_menu({0})".format(menuspec)
    shower = Effect(showername, "show_menu", menuspec, db)
    shower.unravel(db)
    return shower


def make_hide_calendar_effect(dimname, itname, db):
    """Return an effect that hides the calendar column representing this
item in this dimension."""
    calspec = dimname + "." + itname
    return make_hide_calendar_effect_from_calspec(calspec, db)


def make_hide_calendar_effect_from_calspec(calspec, db):
    """Given a string consisting of a dimension name, a dot, and an item
name, return an effect that hides the calendar representing the
schedule for that item in that dimension."""
    hidername = "hide_calendar({0})".format(calspec)
    hider = Effect(hidername, "hide_calendar", calspec, db)
    hider.unravel(db)
    return hider


def make_show_calendar_effect(dimname, itname, db):
    """Return an effect that shows the calendar representing the schedule
of this item in this dimension."""
    calspec = dimname + "." + itname
    return make_show_calendar_effect_from_calspec(calspec, db)


def make_show_calendar_effect_from_calspec(calspec, db):
    """Given a string consisting of a dimension name, a dot, and an item
name, return an effect that shows the calendar representing the
schedule of that item in that dimension."""
    showername = "show_calendar({0})".format(calspec)
    shower = Effect(showername, "show_calendar", calspec, db)
    shower.unravel(db)
    return shower


def make_hide_all_menus_effect(boardname, db):
    """Return an effect that will hide all menus in the given board,
*unless* they are marked main_for_window."""
    hidername = "hide_menus_in_board({0})".format(boardname)
    hider = Effect(hidername, "hide_menus_in_board", boardname, db)
    hider.unravel(db)
    return hider


def make_hide_other_menus_effect(boardn, menun, db):
    """Return an effect that will hide all menus in the given board, save
the one given, as well as any marked main_for_window."""
    menuspec = boardn + "." + menun
    hidername = "hide_other_menus_in_board({0})".format(menuspec)
    hider = Effect(hidername, "hide_other_menus_in_board", menuspec, db)
    hider.unravel(db)
    return hider


def make_hide_all_calendars_effect(dimname, db):
    """Return an effect that will hide all the calendars in the given board."""
    hidername = "hide_calendars_in_board({0})".format(dimname)
    hider = Effect(hidername, "hide_calendars_in_board", dimname, db)
    hider.unravel(db)
    return hider


def make_hide_other_calendars_effect(dimname, itname, db):
    """Return an effect that will hide all calendars in this board, apart
from this one."""
    calspec = dimname + "." + itname
    hidername = "hide_other_calendars_in_board({0})".format(calspec)
    hider = Effect(hidername, "hide_other_calendars_in_board", calspec, db)
    hider.unravel(db)
    return hider


def make_show_only_menu_effect_deck(boardname, menuname, db):
    """Return an effect that will show the given menu in the given board,
but hide all the others (apart from main_for_window)."""
    hider = make_hide_all_menus_effect(boardname, db)
    shower = make_show_menu_effect(boardname, menuname, db)
    deckname = "show_only_menu({0}.{1})".format(boardname, menuname)
    deck = EffectDeck(deckname, [hider, shower], db)
    deck.unravel(db)
    return deck


def make_show_only_calendar_effect_deck(dimname, itname, db):
    """Return an effect that will hide all calendars in the given board,
except for the one for this item."""
    hider = make_hide_all_calendars_effect(dimname, db)
    shower = make_show_calendar_effect(dimname, itname, db)
    deckname = "show_only_calendar({0}.{1})".format(dimname, itname)
    deck = EffectDeck(deckname, [hider, shower], db)
    deck.unravel(db)
    return deck


def make_menu_toggler(boardname, menuname, db):
    """Return an effect that will hide all non-main menus in the board,
except for this one, which will be hidden if visible, or shown if
invisible."""
    hide_effect = make_hide_other_menus_effect(boardname, menuname, db)
    toggle_effect = make_toggle_menu_effect(boardname, menuname, db)
    deckname = "toggle_menu_visibility({0}.{1})".format(boardname, menuname)
    deck = EffectDeck(deckname, [hide_effect, toggle_effect], db)
    deck.unravel(db)
    return deck


def make_calendar_toggler(dimname, itname, db):
    """Return an effect that will hide all calendar columns in the board,
except for this one, which will be hidden if visible, or shown if
invisible."""
    hide_effect = make_hide_all_calendars_effect(dimname, db)
    deckname = "toggle_calendar_visibility({0}.{1})".format(dimname, itname)
    deck = EffectDeck(deckname, [hide_effect, toggle_effect], db)
    deck.unravel(db)
    return deck
