# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
"""The database backend, with dictionaries of loaded objects.

This is a caching database connector. There are dictionaries for all
objects that can be loaded from the database.

This module does not contain the code used to generate
SQL. That's in :class:`~LiSE.util.SaveableMetaclass`.

"""
import os
import re
import sqlite3

from gui.board import (
    Board,
    Spot,
    Pawn)
from gui.charsheet import CharSheet, CharSheetView
from gui.menu import Menu
from gui.img import Img
from model import (
    Character,
    Facade,
    Place,
    Portal,
    Timestream,
    Thing)
from model.event import Implicator
from util import (
    SaveableMetaclass,
    int2pytype,
    pytype2int,
    Bone,
    PlaceBone,
    schemata,
    saveables,
    saveable_classes,
    Skeleton)


def noop(*args, **kwargs):
    """Do nothing."""
    pass


###
# These regexes serve to parse certain database records that represent
# function calls.
#
# Mainly, that means menu items and Effects.
###
ONE_ARG_RE = re.compile("(.+)")
TWO_ARG_RE = re.compile("(.+), ?(.+)")
ITEM_ARG_RE = re.compile("(.+)\.(.+)")
MAKE_SPOT_ARG_RE = re.compile(
    "(.+)\."
    "(.+),([0-9]+),([0-9]+),?(.*)")
MAKE_PORTAL_ARG_RE = re.compile(
    "(.+)\.(.+)->"
    "(.+)\.(.+)")
MAKE_THING_ARG_RE = re.compile(
    "(.+)\.(.+)@(.+)")
PORTAL_NAME_RE = re.compile(
    "Portal\((.+)->(.+)\)")
NEW_THING_RE = re.compile(
    "new_thing\((.+)+\)")
NEW_PLACE_RE = re.compile(
    "new_place\((.+)\)")
CHARACTER_RE = re.compile(
    "character\((.+)\)")


class Closet(object):
    """This is where you should get all your LiSE objects from, generally.

A RumorMill is a database connector that can load and generate LiSE
objects. When loaded or generated, the object will be kept in the
RumorMill, even if nowhere else.

There are some special facilities here for the convenience of
particular LiSE objects: Things look up their location here; Items
(including Things) look up their contents here; and Effects look up
their functions here. That means you need to register functions here
when you want Effects to use them. Supply callback
functions for Effects in a list in the keyword argument "effect_cbs".

Supply boolean callback functions for Causes and the like in the
keyword argument "test_cbs".

You need to create a SQLite database file with the appropriate schema
before RumorMill will work. For that, run mkdb.sh.

    """
    __metaclass__ = SaveableMetaclass
    tables = [
        ("globals", {
            "columns": {
                "key": "text not null",
                "type": "integer not null default 3",
                "value": "text"},
            "primary_key": ("key",),
            "checks": ["type in ({})".format(", ".join([
                str(typ) for typ in int2pytype]))]
        }),
        ("strings", {
            "columns": {
                "stringname": "text not null",
                "language": "text not null default 'eng'",
                "string": "text not null"},
            "primary_key": ("stringname", "language")})]
    globs = ("branch", "tick", "observer", "observed", "host")
    working_dicts = [
        "boardhand_d",
        "calendar_d",
        "cause_d",
        "color_d",
        "board_d",
        "effect_d",
        "img_d",
        "texture_d",
        "textag_d",
        "menu_d",
        "menuitem_d",
        "style_d",
        "event_d",
        "character_d",
        "facade_d"]
    """The names of dictionaries where I keep objects after
    instantiation.

    """

    def __setattr__(self, attrn, val):
        if attrn == "branch" and hasattr(self, 'branch'):
            self.upd_branch(val)
        elif attrn == "tick" and hasattr(self, 'tick'):
            self.upd_tick(val)
        elif attrn == "language" and hasattr(self, 'language'):
            self.upd_lang(val)
        else:
            super(Closet, self).__setattr__(attrn, val)

    def __init__(self, connector, lisepath, USE_KIVY=False, **kwargs):
        """Initialize a Closet for the given connector and path.

        With USE_KIVY, I will use the kivybits module to load images.

        """
        self.connector = connector
        self.skeleton = Skeleton({"place": {}})

        self.c = self.connector.cursor()
        self.lang_listeners = []
        self.branch_listeners = []
        self.tick_listeners = []
        self.time_listeners = []
        if "language" in kwargs:
            self.language = kwargs["language"]
        else:
            self.language = self.get_global("language")

        for glob in self.globs:
            setattr(self, glob, self.get_global(glob))

        self.lisepath = lisepath

        for wd in self.working_dicts:
            setattr(self, wd, dict())

        if USE_KIVY:
            from gui.kivybits import (
                load_textures,
                load_textures_tagged,
                load_all_textures)
            self.load_textures = lambda names: load_textures(
                self.c, self.skeleton, self.texture_d,
                self.textag_d, names)
            self.load_all_textures = lambda: load_all_textures(
                self.c, self.skeleton, self.texture_d, self.textag_d)
            self.load_textures_tagged = lambda tags: load_textures_tagged(
                self.c, self.skeleton, self.texture_d, self.textag_d,
                tags)
            self.USE_KIVY = True

        self.timestream = Timestream(self)
        self.time_travel_history = []
        self.game_speed = 1
        self.updating = False
        placeholder = (noop, ITEM_ARG_RE)
        self.menu_cbs = {
            'play_speed':
            (self.play_speed, ONE_ARG_RE),
            'back_to_start':
            (self.back_to_start, ''),
            'noop': placeholder,
            'make_generic_place':
            (self.make_generic_place, ''),
            'increment_branch':
            (self.increment_branch, ONE_ARG_RE),
            'time_travel_inc_tick':
            (lambda mi, ticks:
             self.time_travel_inc_tick(int(ticks)), ONE_ARG_RE),
            'time_travel':
            (self.time_travel_menu_item, TWO_ARG_RE),
            'time_travel_inc_branch':
            (lambda mi, branches: self.time_travel_inc_branch(int(branches)),
             ONE_ARG_RE),
            'go':
            (self.go, ""),
            'stop':
            (self.stop, ""),
            'start_new_map': placeholder,
            'open_map': placeholder,
            'save_map': placeholder,
            'quit_map_editor': placeholder,
            'editor_select': placeholder,
            'editor_copy': placeholder,
            'editor_paste': placeholder,
            'editor_delete': placeholder,
            'mi_connect_portal':
            (self.mi_connect_portal, ""),
            'mi_show_popup':
            (self.mi_show_popup, ONE_ARG_RE)}

    def __del__(self):
        """Try to write changes to disk before dying.

        """
        self.c.close()
        self.connector.commit()
        self.connector.close()

    def select_class_all(self, cls):
        """Return a Skeleton with all records for all tables defined in the
        class."""
        td = {}
        for tabn in cls.tablenames:
            bonetype = cls.bonetypes[tabn]
            bone = bonetype._null()
            td[tabn] = [bone]
        return cls._select_skeleton(self.c, td)

    def upd_branch(self, b):
        """Set the active branch, alerting any branch_listeners"""
        super(Closet, self).__setattr__('branch', b)
        self.upd_time(b, self.tick)
        for listener in self.branch_listeners:
            listener(b)

    def upd_tick(self, t):
        """Set the current tick, alerting any tick_listeners"""
        super(Closet, self).__setattr__('tick', t)
        self.upd_time(self.branch, t)
        for listener in self.tick_listeners:
            listener(t)

    def upd_time(self, b, t):
        """Set the current branch and tick, alerting any time_listeners"""
        for listener in self.time_listeners:
            listener(b, t)

    def upd_lang(self, l):
        """Set the current language, alerting any lang_listeners"""
        for listener in self.lang_listeners:
            listener(self, l)
        super(Closet, self).__setattr__('language', l)

    def get_global(self, key):
        self.c.execute("SELECT type, value FROM globals WHERE key=?;", (key,))
        (typ_i, val_s) = self.c.fetchone()
        return int2pytype[typ_i](val_s)

    def set_global(self, key, value):
        self.c.execute("DELETE FROM globals WHERE key=?;", (key,))
        self.c.execute(
            "INSERT INTO globals (key, type, value) VALUES (?, ?, ?);",
            (key, pytype2int[type(value)], unicode(value)))

    def get_text(self, strname):
        """Get the string of the given name in the language set at startup."""
        if strname is None:
            return ""
        elif strname[0] == "@":
            if strname[1:] == "branch":
                return str(self.branch)
            elif strname[1:] == "tick":
                return str(self.tick)
            else:
                if strname[1:] not in self.skeleton[u"strings"]:
                    self.skeleton.update(self._select_skeleton(
                        self.c, {"strings": [
                            self.bonetypes["strings"]._null()._replace(
                                stringname=strname[1:],
                                language=self.language)]}))
                return self.skeleton[u"strings"][
                    strname[1:]][self.language].string
        else:
            return strname

    def save_game(self):
        """Save all pending changes to disc."""
        # save globals first
        for glob in self.globs:
            self.set_global(glob, getattr(self, glob))
        # find out what's changed since last checkpoint
        to_save = self.skeleton - self.old_skeleton
        to_delete = self.old_skeleton - self.skeleton
        # save each class in turn
        for clas in saveable_classes:
            assert(len(clas.tablenames) > 0)
            for tabname in clas.tablenames:
                if tabname in to_delete:
                    clas._delete_keybones_table(
                        self.c, to_delete[tabname].iterbones(), tabname)
                if tabname in to_save:
                    clas._delete_keybones_table(
                        self.c, to_save[tabname].iterbones(), tabname)
                    try:
                        clas._insert_bones_table(
                            self.c, to_save[tabname].iterbones(), tabname)
                    except ValueError:
                        pass
        # remember how things are now
        self.checkpoint()

    def load_strings(self):
        """Load all strings available."""
        self.skeleton.update(self._select_skeleton(self.c, {
            "strings": [self.bonetypes["strings"]._null()]}))

    def make_generic_place(self, character):
        """Make a place hosted by the given character, and give it a boring
        name.

        """
        character = self.get_character(character)
        placen = "generic_place_{0}".format(len(character.graph.vs))
        return character.make_place(placen)

    def make_generic_thing(self, character, host, location,
                           branch=None, tick=None):
        if branch is None:
            branch = self.branch
        if tick is None:
            tick = self.tick
        character = self.get_character(character)
        charn = unicode(character)
        hostn = unicode(host)
        locn = unicode(location)
        if charn not in self.skeleton[u"thing"]:
            self.skeleton[u"thing"][charn] = {}
        thingn = u"generic_thing_{}".format(
            len(self.skeleton[u"thing"][charn]))
        thing_core_bone = Thing.bonetypes["thing"](
            character=charn,
            name=thingn,
            host=hostn)
        self.set_bone(thing_core_bone)
        thing_loc_bone = Thing.bonetypes["thing_loc"](
            character=charn,
            name=thingn,
            branch=branch,
            tick=tick,
            location=locn)
        self.set_bone(thing_loc_bone)
        return character.make_thing(thingn)

    def load_charsheet(self, character):
        """Return a CharSheetView displaying the CharSheet for the character
        specified, perhaps loading it if necessary."""
        # if the character is not loaded yet, make it so
        character = unicode(self.get_character(character))
        bd = {
            "charsheet": [
                CharSheet.bonetypes["charsheet"]._null()._replace(
                    character=character)],
            "charsheet_item": [
                CharSheet.bonetypes["charsheet_item"]._null()._replace
                (character=character)]}
        self.skeleton.update(
            CharSheet._select_skeleton(self.c, bd))
        return CharSheetView(character=self.get_character(character))

    def load_characters(self, names):
        """Load all the named characters and return them in a dict."""
        charstats = Character._select_skeleton(self.c, {
            "character_stat": [
                Character.bonetypes["character_stat"]._null()._replace(
                    character=name)
                for name in names]})
        portalstuff = Portal._select_skeleton(self.c, {
                "portal": [
                    Portal.bonetypes["portal"]._null()._replace(character=name)
                    for name in names],
                "portal_loc": [
                    Portal.bonetypes["portal_loc"]._null()._replace(
                        character=name)
                    for name in names],
                "portal_stat": [
                    Portal.bonetypes["portal_stat"]._null()._replace(
                        character=name)
                    for name in names]})
        thingstuff = Thing._select_skeleton(self.c, {
            "thing": [
                Thing.bonetypes["thing"]._null()._replace(
                    character=name)
                for name in names],
            "thing_loc": [
                Thing.bonetypes["thing_loc"]._null()._replace(
                    character=name)
                for name in names],
            "thing_stat": [
                Thing.bonetypes["thing_stat"]._null()._replace(
                    character=name)
                for name in names]})
        placestuff = Place._select_skeleton(self.c, {
            "place_stat": [
                Place.bonetypes["place_stat"]._null()._replace(
                    character=name)
                for name in names]})
        for stuff in (charstats, portalstuff, thingstuff, placestuff):
            self.skeleton.update(stuff)
        r = {}
        for name in names:
            char = Character(self, name)
            r[name] = char
            self.character_d[name] = char
        return r

    def get_characters(self, names):
        """Return the named characters in a dict. Load them as needed."""
        r = {}
        unhad = set()
        for name in names:
            if isinstance(name, Character):
                r[str(name)] = name
            elif name in self.character_d:
                r[name] = self.character_d[name]
            else:
                unhad.add(name)
        if len(unhad) > 0:
            r.update(self.load_characters(names))
        return r

    def get_character(self, name):
        """Return the named character. Load it if needed.

        When supplied with a Character object, this will simply return
        it, so you may use it to *ensure* that an object is a
        Character.

        """
        if isinstance(name, Character):
            return name
        return self.get_characters([str(name)])[str(name)]

    def get_effects(self, names):
        """Return the named effects in a dict"""
        r = {}
        for name in names:
            r[name] = Implicator.make_effect(name)
        return r

    def get_effect(self, name):
        """Return the named effect in a dict"""
        return self.get_effects([name])[name]

    def get_causes(self, names):
        """Return the named causes in a dict"""
        r = {}
        for name in names:
            r[name] = Implicator.make_cause(name)
        return r

    def get_cause(self, cause):
        """Return the named cause in a dict"""
        return self.get_causes([cause])[cause]

    def load_board(self, observer, observed, host):
        """Load and return a graphical board widget displaying the contents of
        the host that are parts of the observed character, as seen by
        the observer character.

        """
        observer = unicode(observer)
        observed = unicode(observed)
        self.skeleton.update(Board._select_skeleton(self.c, {
            "board": [Board.bonetype._null()._replace(
                observer=observer, observed=observed, host=host)]}))
        self.skeleton.update(Spot._select_skeleton(self.c, {
            "spot": [Spot.bonetypes["spot"]._null()._replace(
                host=host)],
            "spot_coords": [Spot.bonetypes["spot_coords"]._null()._replace(
                host=host)]}))
        self.skeleton.update(Pawn._select_skeleton(self.c, {
            "pawn": [Pawn.bonetypes["pawn"]._null()._replace(host=host)]}))
        return self.get_board(observer, observed, host)

    def get_board(self, observer, observed, host):
        """Return a graphical board widget displaying the contents of the host
        that are parts of the observed character, as seen by the
        observer character. Load it if needed.

        """
        observer = self.get_character(observer)
        observed = self.get_character(observed)
        host = self.get_character(host)
        facade = observed.get_facade(observer)
        return Board(facade=facade, host=host)

    def get_place(self, char, placen):
        return self.get_character(char).get_place(placen)

    def get_portal(self, char, name):
        return self.get_character(char).get_portal(name)

    def get_thing(self, char, name):
        return self.get_character(char).get_thing(name)

    def get_textures(self, imgnames):
        r = {}
        unloaded = set()
        for imgn in imgnames:
            if imgn in self.texture_d:
                r[imgn] = self.texture_d[imgn]
            else:
                unloaded.add(imgn)
        if len(unloaded) > 0:
            r.update(self.load_textures(unloaded))
        return r

    def get_texture(self, imgn):
        return self.get_textures([imgn])[imgn]

    def load_menus(self, names):
        r = {}
        for name in names:
            r[name] = self.load_menu(name)
        return r

    def load_menu(self, name):
        self.load_menu_items(name)
        return Menu(closet=self, name=name)

    def load_menu_items(self, menu):
        bd = {"menu_item": [Menu.bonetypes[
            "menu_item"]._null()._replace(menu=menu)]}
        r = Menu._select_skeleton(self.c, bd)
        self.skeleton.update(r)
        return r

    def load_timestream(self):
        self.skeleton.update(self.select_class_all(Timestream))
        self.timestream = Timestream(self)

    def time_travel_menu_item(self, mi, branch, tick):
        return self.time_travel(branch, tick)

    def time_travel(self, branch, tick):
        assert branch <= self.timestream.hi_branch + 1, (
            "Tried to travel to too high a branch")
        if branch == self.timestream.hi_branch + 1:
            self.new_branch(self.branch, branch, tick)
        # will need to take other games-stuff into account than the
        # thing_location
        if tick < 0:
            tick = 0
            self.updating = False
        # make it more general
        mintick = self.timestream.min_tick(branch, "thing_loc")
        if tick < mintick:
            tick = mintick
        self.time_travel_history.append((self.branch, self.tick))
        if tick > self.timestream.hi_tick:
            self.timestream.hi_tick = tick
        self.branch = branch
        self.tick = tick

    def increment_branch(self, branches=1):
        b = self.branch + int(branches)
        mb = self.timestream.max_branch()
        if b > mb:
            # I dunno where you THOUGHT you were going
            self.new_branch(self.branch, self.branch+1, self.tick)
            return self.branch + 1
        else:
            return b

    def new_branch(self, parent, branch, tick):
        assert(parent != branch)
        print("making new branch {} from parent branch {} "
              "starting at tick {}".format(branch, parent, tick))
        new_bones = set()
        for character in self.character_d.itervalues():
            for bone in character.new_branch(parent, branch, tick):
                new_bones.add(bone)
        for observer in self.board_d:
            for observed in self.board_d[observer]:
                for host in self.board_d[observer][observed]:
                    for bone in self.board_d[observer][observed][
                            host].new_branch(parent, branch, tick):
                        new_bones.add(bone)
        self.skeleton["timestream"][branch] = Timestream.bonetype(
            branch=branch, parent=parent, tick=tick)
        self.timestream.hi_branch += 1
        assert(self.timestream.hi_branch == branch)
        for bone in new_bones:
            self.set_bone(bone)

    def time_travel_inc_tick(self, ticks=1):
        self.time_travel(self.branch, self.tick+ticks)

    def time_travel_inc_branch(self, branches=1):
        self.increment_branch(branches)
        self.time_travel(self.branch+branches, self.tick)

    def go(self, nope=None):
        self.updating = True

    def stop(self, nope=None):
        self.updating = False

    def set_speed(self, newspeed):
        self.game_speed = newspeed

    def play_speed(self, mi, n):
        self.game_speed = int(n)
        self.updating = True

    def back_to_start(self, nope):
        self.stop()
        self.time_travel(self.branch, 0)

    def update(self, *args):
        if self.updating:
            self.time_travel_inc_tick(ticks=self.game_speed)

    def end_game(self):
        self.c.close()
        self.connector.commit()
        self.connector.close()

    def checkpoint(self):
        self.old_skeleton = self.skeleton.deepcopy()

    def uptick_bone(self, bone):
        if hasattr(bone, "branch") and bone.branch > self.timestream.hi_branch:
            self.timestream.hi_branch = bone.branch
        if (
                hasattr(bone, "tick_from") and
                bone.tick_from > self.timestream.hi_tick):
            self.timestream.hi_tick = bone.tick_from
        if hasattr(bone, "tick_to") and bone.tick_to > self.timestream.hi_tick:
            self.timestream.hi_tick = bone.tick_to

    def uptick_skel(self):
        for bone in self.skeleton.iterbones():
            self.uptick_bone(bone)

    def get_present_bone(self, skel):
        return skel[self.branch].value_during(self.tick)

    def mi_show_popup(self, mi, name):
        root = mi.get_root_window().children[0]
        new_thing_match = re.match(NEW_THING_RE, name)
        if new_thing_match:
            return root.show_pawn_picker(
                new_thing_match.groups()[0].split(", "))
        new_place_match = re.match(NEW_PLACE_RE, name)
        if new_place_match:
            return root.show_spot_picker(
                new_place_match.groups()[0].split(", "))
        character_match = re.match(CHARACTER_RE, name)
        if character_match:
            argstr = character_match.groups()[0]
            if len(argstr) == 0:
                return root.show_charsheet_maker()

    def mi_connect_portal(self, mi):
        mi.get_root_window().children[0].make_arrow()

    def register_text_listener(self, stringn, listener):
        if stringn == "@branch":
            self.branch_listeners.append(listener)
        elif stringn == "@tick":
            self.tick_listeners.append(listener)
        if stringn[0] == "@" and stringn[1:] in self.skeleton["strings"]:
            self.skeleton["strings"][stringn[1:]].register_set_listener(
                listener)

    def register_time_listener(self, listener):
        self.time_listeners.append(listener)

    def register_branch_listener(self, listener):
        self.branch_listeners.append(listener)

    def register_tick_listener(self, listener):
        self.tick_listeners.append(listener)

    def load_img_metadata(self):
        self.skeleton.update(self.select_class_all(Img))

    def query_place(self):
        """Query the 'place' view, resulting in an up-to-date record of what
        places exist in the gameworld as it exists in the
        database. Expensive.

        """
        self.c.execute("SELECT host, place, branch, tick FROM place;")
        if u"place" not in self.skeleton:
            self.skeleton[u"place"] = {}
        for (host, place, branch, tick) in self.c:
            if host not in self.skeleton[u"place"]:
                self.skeleton[u"place"][host] = {}
            if place not in self.skeleton[u"place"][host]:
                self.skeleton[u"place"][host][place] = []
            if branch not in self.skeleton[u"place"][host][place]:
                self.skeleton[u"place"][host][place][branch] = []
            self.skeleton[u"place"][host][place][branch][tick] = PlaceBone(
                host=host, place=place, branch=branch, tick=tick)

    def set_bone(self, bone):
        """Take a bone of arbitrary type and put it in the right place in the
        skeleton.

        Additionally, if the bone is of a kind that may implicitly
        define a place, see if the place is a new one. If so, insert a
        PlaceBone to describe it.

        """
        def init_keys(skel, keylst):
            for key in keylst:
                if key not in skel:
                    skel[key] = {}
                skel = skel[key]
            return skel

        def have_place_bone(host, place, branch, tick):
            try:
                return self.skeleton[u"place"][host][place][
                    branch].value_during(tick) is not None
            except (KeyError, IndexError):
                return False

        def set_place_maybe(host, place, branch, tick):
            if not have_place_bone(host, place, branch, tick):
                self.set_bone(PlaceBone(
                    host=host, place=place, branch=branch, tick=tick))

        if isinstance(bone, PlaceBone):
            skel = init_keys(
                self.skeleton[u"place"],
                [bone.host, bone.place, bone.branch])
            skel[bone.tick] = bone
            return

        # Some bones implicitly declare a new place
        if isinstance(bone, Thing.bonetypes[u"thing_loc"]):
            core = self.skeleton[u"thing"][bone.character][bone.name]
            set_place_maybe(core.host, bone.location, bone.branch, bone.tick)
        elif isinstance(bone, Thing.bonetypes[u"thing_loc_facade"]):
            core = self.skeleton[u"thing"][bone.observed][bone.name]
            set_place_maybe(core.host, bone.location, bone.branch, bone.tick)
        elif isinstance(bone, Portal.bonetypes[u"portal_loc"]):
            core = self.skeleton[u"portal"][bone.character][bone.name]
            for loc in (bone.origin, bone.destination):
                set_place_maybe(core.host, loc, bone.branch, bone.tick)
        elif isinstance(bone, Portal.bonetypes[u"portal_stat_facade"]):
            core = self.skeleton[u"portal"][bone.observed][bone.name]
            for loc in (bone.origin, bone.destination):
                set_place_maybe(core.host, loc, bone.branch, bone.tick)
        elif isinstance(bone, Place.bonetypes[u"place_stat"]):
            set_place_maybe(bone.host, bone.name, bone.branch, bone.tick)
        elif isinstance(bone, Spot.bonetypes[u"spot"]):
            set_place_maybe(bone.host, bone.place, bone.branch, bone.tick)
        elif isinstance(bone, Spot.bonetypes[u"spot_coords"]):
            set_place_maybe(bone.host, bone.place, bone.branch, bone.tick)

        keynames = bone.cls.keynames[bone._name]
        keys = [getattr(bone, keyn) for keyn in keynames[:-1]]
        skel = init_keys(self.skeleton[bone._name], keys)
        final_key = getattr(bone, keynames[-1])
        skel[final_key] = bone


def mkdb(DB_NAME, lisepath):
    def recurse_rltiles(d):
        """Return a list of all bitmaps in the directory, and all levels of
subdirectory therein."""
        bmps = [d + os.sep + bmp
                for bmp in os.listdir(d)
                if bmp[0] != '.' and
                bmp[-4:] == ".bmp"]
        for subdir in os.listdir(d):
            try:
                bmps.extend(recurse_rltiles(d + os.sep + subdir))
            except:
                continue
        return bmps

    def ins_rltiles(curs, dirname):
        """Recurse into the directory, and for each bitmap I find, add records
        to the database describing it.

        Also tag the bitmaps with the names of the folders they are
        in, up to (but not including) the 'rltiles' folder.

        """
        for bmp in recurse_rltiles(dirname):
            qrystr = "insert into img (name, path, rltile, " \
                     "off_x, off_y) values (?, ?, ?, ?, ?)"
            name = bmp.replace(dirname, '').strip(os.sep)
            curs.execute(qrystr, (name, bmp, True, 4, 8))
            tags = name.split(os.sep)[:-1]
            qrystr = "insert into img_tag (img, tag) values (?, ?)"
            for tag in tags:
                curs.execute(qrystr, (name, tag))

    def read_sql(filen):
        """Read all text from the file, and execute it as SQL commands."""
        sqlfile = open(filen, "r")
        sql = sqlfile.read()
        sqlfile.close()
        c.executescript(sql)

    try:
        os.remove(DB_NAME)
    except OSError:
        pass
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    done = set()
    while saveables != []:
        (demands, provides, prelude,
         tablenames, postlude) = saveables.pop(0)
        print(tablenames)
        breakout = False
        for demand in iter(demands):
            if demand not in done:
                saveables.append(
                    (demands, provides, prelude,
                     tablenames, postlude))
                breakout = True
                break
        if breakout:
            continue
        prelude_todo = list(prelude)
        while prelude_todo != []:
            pre = prelude_todo.pop()
            if isinstance(pre, tuple):
                c.execute(*pre)
            else:
                c.execute(pre)
        if len(tablenames) == 0:
            for post in postlude:
                if isinstance(post, tuple):
                    c.execute(*post)
                else:
                    c.execute(post)
            continue
        prelude_todo = list(prelude)
        try:
            while prelude_todo != []:
                pre = prelude_todo.pop()
                if isinstance(pre, tuple):
                    c.execute(*pre)
                else:
                    c.execute(pre)
        except sqlite3.OperationalError as e:
            saveables.append(
                (demands, provides, prelude_todo, tablenames, postlude))
            continue
        breakout = False
        tables_todo = list(tablenames)
        while tables_todo != []:
            tn = tables_todo.pop(0)
            c.execute(schemata[tn])
            done.add(tn)
        if breakout:
            saveables.append(
                (demands, provides, prelude_todo, tables_todo, postlude))
            continue
        postlude_todo = list(postlude)
        try:
            while postlude_todo != []:
                post = postlude_todo.pop()
                if isinstance(post, tuple):
                    c.execute(*post)
                else:
                    c.execute(post)
        except sqlite3.OperationalError as e:
            print("OperationalError during postlude from {0}:".format(tn))
            print(e)
            import pdb
            pdb.set_trace()
            saveables.append(
                (demands, provides, prelude_todo, tables_todo, postlude_todo))
            continue
        done.update(provides)

    oldhome = os.path.abspath(os.getcwd())
    os.chdir(lisepath + os.sep + 'sql')
    initfiles = sorted(os.listdir(os.getcwd()))
    for initfile in initfiles:
        if initfile[-3:] == "sql":  # weed out automatic backups and so forth
            print("reading SQL from file " + initfile)
            read_sql(initfile)

    os.chdir(oldhome)

    print("indexing the RLTiles")
    ins_rltiles(c, os.path.abspath(lisepath)
                + os.sep + 'gui' + os.sep + 'assets'
                + os.sep + 'rltiles')

    conn.commit()
    return conn


def load_closet(dbfn, lisepath, lang="eng", kivy=False):
    """Construct a ``Closet`` connected to the given database file. Use
the LiSE library in the path given.

If ``kivy`` == True, the closet will be able to load textures using
Kivy's Image widget.

Strings will be loaded for the language ``lang``. Use language codes
from ISO 639-2.

    """
    conn = sqlite3.connect(dbfn)
    r = Closet(connector=conn, lisepath=lisepath, lang=lang, USE_KIVY=kivy)
    r.load_strings()
    r.load_timestream()
    return r
