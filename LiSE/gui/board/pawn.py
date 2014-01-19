# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) 2013 Zachary Spector,  zacharyspector@gmail.com
from gamepiece import GamePiece
from kivy.properties import (
    AliasProperty,
    ObjectProperty)


"""Widget representing things that move about from place to place."""


class Pawn(GamePiece):
    """A token to represent something that moves about between places.

Pawns are graphical widgets made of one or more textures layered atop
one another. The textures are assumed to be 32x32 pixels.

Pawns represent Things in those cases where a Thing is located
directly in a Place or a Portal. The corresponding Pawn will appear
atop the Place's Spot or the Portal's Arrow.

If a Pawn is currently interactive, it may be dragged to a new Spot,
which has the effect of ordering its Thing to travel there. This takes
some amount of game time. Whenever the game-time changes, the Pawn
will update its position appropriately.

    """
    demands = ["board"]
    tables = [
        ("pawn", {
            "columns": {
                "observer": "text not null default 'Omniscient'",
                "observed": "text not null default 'Physical'",
                "host": "text not null default 'Physical'",
                "thing": "text not null",
                "branch": "integer not null default 0",
                "tick": "integer not null default 0",
                "graphic": "text not null",
                "interactive": "boolean default 1"},
            "primary_key": (
                "observer", "observed", "host", "thing",
                "branch", "tick"),
            "foreign_keys": {
                "observer, observed, host": (
                    "board", "observer, observed, host"),
                "observed, host, thing": (
                    "thing", "character, host, name"),
                "graphic": ("graphic", "name")}})]
    board = ObjectProperty()
    thing = ObjectProperty()
    bone = ObjectProperty()
    _touch = ObjectProperty(None, allownone=True)
    where_upon = ObjectProperty()
    name = AliasProperty(
        lambda self: self.bone.graphic if self.bone else '',
        lambda self, v: None,
        bind=('bone',))

    def __init__(self, **kwargs):
        """Arrange to update my textures and my position whenever the relevant
        data change.

        """
        def reposskel(*args):
            self.repos()
        if 'board' in kwargs and 'closet' not in kwargs:
            kwargs['closet'] = kwargs['board'].host.closet
        kwargs['bone'] = kwargs['closet'].skeleton[u'pawn'][
            unicode(kwargs['board'].facade.observer)][
            unicode(kwargs['thing'].character)][
            unicode(kwargs['thing'].host)][
            unicode(kwargs['thing'])][
            kwargs['closet'].branch].value_during(
            kwargs['closet'].tick)
        kwargs['graphic_name'] = kwargs['bone'].graphic
        super(Pawn, self).__init__(**kwargs)
        skel = self.closet.skeleton[u"thing_loc"][
            unicode(self.thing.character)][unicode(self.thing)]
        skel.register_set_listener(reposskel)
        skel.register_del_listener(reposskel)
        self.closet.register_time_listener(self.handle_time)
        self.board.pawndict[unicode(self.thing)] = self

    def __str__(self):
        return str(self.thing)

    def __unicode__(self):
        return unicode(self.thing)

    def handle_time(self, b, t):
        self.bone = self.get_pawn_bone(b, t)
        self.repos(b, t)

    def on_board(self, *args):
        self.repos()

    def get_loc_bone(self, branch=None, tick=None):
        return self.thing.get_bone(branch, tick)

    def get_pawn_bone(self, branch=None, tick=None):
        (branch, tick) = self.board.host.sanetime(branch, tick)
        return self.board.host.closet.skeleton[u"pawn"][
            unicode(self.board.facade.observer)][
            unicode(self.board.facade.observed)][
            unicode(self.thing.host)][
            unicode(self.thing)][branch].value_during(tick)

    def new_branch(self, parent, branch, tick):
        """Update my part of the :class:`Skeleton` to have this new branch in
        it. Where there is room, fill it with data from the parent branch."""
        prev = None
        started = False
        imagery = self.board.host.closet.skeleton[u"pawn"][
            unicode(self.board.facade.observer)][
            unicode(self.thing.character)][
            unicode(self.board.host)][
            unicode(self.thing)]
        for tick_from in imagery[parent]:
            if tick_from >= tick:
                bone2 = imagery[parent][tick_from]._replace(
                    branch=branch)
                yield bone2
                if (
                        not started and prev is not None and
                        tick_from > tick and prev < tick):
                    bone3 = imagery[parent][prev]._replace(
                        branch=branch, tick_from=tick_from)
                    yield bone3
                    started = True
                prev = tick_from

    def dropped(self, x, y, button, modifiers):
        """When dropped on a spot, if my :class:`Thing` doesn't have anything
        else to do, make it journey there.

        If it DOES have anything else to do, make the journey in
        another branch.

        """
        spotto = None
        for spot in self.board.spots:
            if (
                    self.window_left < spot.x and
                    spot.x < self.window_right and
                    self.window_bot < spot.y and
                    spot.y < self.window_top):
                spotto = spot
                break
        if spotto is not None:
            self.thing.journey_to(spotto.place)
        self.drag_offset_x = 0
        self.drag_offset_y = 0

    def repos(self, b=None, t=None):
        """Recalculate and reassign my position, based on the apparent
        position of whatever widget I am located on--a :class:`Spot`
        or an :class:`Arrow`.

        """
        thingloc = self.thing.get_location(self.board.facade.observer, b, t)
        if thingloc is None:
            return
        try:
            new_where_upon = self.board.arrowdict[unicode(thingloc)]
        except KeyError:
            new_where_upon = self.board.spotdict[unicode(thingloc)]
        if self.where_upon is not None:
            self.where_upon.pawns_here.remove(self)
        self.where_upon = new_where_upon
        self.where_upon.pawns_here.append(self)

    def check_spot_collision(self):
        for spot in self.board.spotlayout.children:
            if self.collide_widget(spot):
                return spot

    def on_touch_down(self, touch):
        if self.collide_point(touch.x, touch.y):
            touch.ud["pawn"] = self
            touch.grab(self)
            return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.center = touch.pos
            return True

    def on_touch_up(self, touch):
        if 'pawn' in touch.ud:
            del touch.ud['pawn']
        if touch.grab_current is self:
            touch.ungrab(self)
            new_spot = self.check_spot_collision()

            if new_spot:
                myplace = self.thing.location
                theirplace = new_spot.place
                if myplace != theirplace:
                    self.thing.journey_to(new_spot.place)
            self.repos()
            return True
        return super(Pawn, self).on_touch_up(touch)
