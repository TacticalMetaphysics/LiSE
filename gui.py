import pyglet
from database import Database
from state import GameState
from widgets import Spot, Pawn
from menu import Menu, MenuItem


def point_is_in(x, y, listener):
    return x >= listener.getleft() and x <= listener.getright() \
        and y >= listener.getbot() and y <= listener.gettop()


def point_is_between(x, y, x1, y1, x2, y2):
    return x >= x1 and x <= x2 and y >= y1 and y <= y2


class GameWindow:
    # One window, batch, and WidgetFactory per board.
    def __init__(self, db, gamestate, boardname, batch=None):
        self.db = db
        self.db.xfunc(self.toggle_menu_visibility_by_name)
        self.gamestate = gamestate
        self.board = gamestate.boarddict[boardname]
        if self.board is None:
            raise Exception("No board by the name %s" % (boardname,))

        self.boardgroup = pyglet.graphics.OrderedGroup(0)
        self.edgegroup = pyglet.graphics.OrderedGroup(1)
        self.spotgroup = pyglet.graphics.OrderedGroup(2)
        self.pawngroup = pyglet.graphics.OrderedGroup(3)
        self.menugroup = pyglet.graphics.OrderedGroup(4)
        self.calendargroup = pyglet.graphics.OrderedGroup(4)
        self.brickgroup = pyglet.graphics.OrderedGroup(5)
        self.labelgroup = pyglet.graphics.OrderedGroup(6)

        self.pressed = None
        self.hovered = None
        self.grabbed = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_buttons = 0
        self.mouse_mods = 0
        self.view_left = 0
        self.view_bot = 0

        self.to_mouse = list(self.board.pawns) + list(self.board.spots)
        for menu in self.board.menus:
            self.to_mouse.extend(menu.items)

        window = pyglet.window.Window()
        if batch is None:
            batch = pyglet.graphics.Batch()

        @window.event
        def on_draw():
            self.add_stuff_to_batch()

        @window.event
        def on_key_press(sym, mods):
            self.on_key_press(sym, mods)

        @window.event
        def on_mouse_motion(x, y, dx, dy):
            self.on_mouse_motion(x, y, dx, dy)

        @window.event
        def on_mouse_press(x, y, button, modifiers):
            self.on_mouse_press(x, y, button, modifiers)

        @window.event
        def on_mouse_release(x, y, button, modifiers):
            self.on_mouse_release(x, y, button, modifiers)

        @window.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            self.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

        self.window = window
        self.batch = batch
        for menu in self.board.menus:
            menu.window = self.window
            if menu.main_for_window:
                self.mainmenu = menu

        self.drawn = {"edges": {}}

        self.menus_changed = [menu for menu in self.board.menus]
        self.pawns_changed = [pawn for pawn in self.board.pawns]
        self.spots_changed = [spot for spot in self.board.spots]

    def add_stuff_to_batch(self):
        self.window.clear()
        old = set()
        newmenus = []
        newmenuitems = []
        newpawns = []
        newspots = []
        newcal = None
        newbricks = []
        while len(self.menus_changed) > 0:
            menu = self.menus_changed.pop()
            if menu in self.drawn:
                old.add(self.drawn[menu])
            newmenus.append(menu)
            for item in menu.items:
                if item in self.drawn:
                    old.add(self.drawn[item])
                newmenuitems.append(item)
        if self.calendar_changed:
            cal = self.calendar
            if cal in self.drawn:
                old.add(self.drawn[cal])
            newcal = cal
            for brick in cal.bricks:
                if brick in self.drawn:
                    old.add(self.drawn[brick])
                    newbricks.append(brick)
        while len(self.pawns_changed) > 0:
            pawn = self.pawns_changed.pop()
            if pawn in self.drawn:
                old.add(self.drawn[pawn])
            newpawns.append(pawn)
        while len(self.spots_changed) > 0:
            spot = self.spots_changed.pop()
            if spot in self.drawn:
                old.add(self.drawn[spot])
            newspots.append(spot)

        if hasattr(self, 'boardsprite'):
            old.add(self.boardsprite)
        for trash in iter(old):
            try:
                trash.delete()
            except AttributeError:
                pass
        for vex in self.drawn["edges"].itervalues():
            vex.delete()

        if newcal is not None:
            self.add_calendar_wall_to_batch(newcal)
            for brick in newbricks:
                self.add_calendar_brick_to_batch(brick)
        for menu in newmenus:
            self.add_menu_to_batch(menu)
        for item in newmenuitems:
            self.add_menu_item_to_batch(item)
        for pawn in newpawns:
            self.add_pawn_to_batch(pawn)
        for spot in newspots:
            self.add_spot_to_batch(spot)
        for spot in self.board.spots:
            self.add_spot_edges_to_batch(spot)
        self.add_board_to_batch()
        self.batch.draw()

    def toggle_menu_visibility_by_name(self, name):
        self.db.toggle_menu_visibility(self.board.dimension + '.' + name)
        return self.db.boardmenudict[self.board.dimension][name]

    def on_key_press(self, key, mods):
        pass

    def change(self, it):
        if isinstance(it, MenuItem):
            self.menus_changed.append(it.menu)
        elif isinstance(it, Menu):
            self.menus_changed.append(it)
        elif isinstance(it, Spot):
            self.spots_changed.append(it)
            alsopawns = self.db.pawns_on_spot(it)
            self.pawns_changed.extend(alsopawns)
        elif isinstance(it, Pawn):
            self.pawns_changed.append(it)
        else:
            raise Exception("I don't know how to change this")

    def on_mouse_motion(self, x, y, dx, dy):
        if self.hovered is None:
            for moused in self.to_mouse:
                if moused is not None\
                   and moused.interactive\
                   and point_is_in(x, y, moused):
                    self.hovered = moused
                    self.change(moused)
                    break
        else:
            if not point_is_in(x, y, self.hovered):
                self.change(self.hovered)
                self.hovered = None

    def on_mouse_press(self, x, y, button, modifiers):
        if self.hovered is not None:
            self.change(self.hovered)
            self.hovered = None
        for moused in self.to_mouse:
            if point_is_in(x, y, moused):
                self.change(moused)
                self.pressed = moused
                break

    def on_mouse_release(self, x, y, button, modifiers):
        if self.grabbed is not None:
            self.change(self.grabbed)
            self.grabbed.dropped(x, y, button, modifiers)
            self.grabbed = None
        elif self.pressed is not None:
            if point_is_in(x, y, self.pressed)\
               and hasattr(self.pressed, 'onclick'):
                also = self.pressed.onclick(button, modifiers)
                self.change(self.pressed)
                self.change(also)
        if self.pressed is not None:
            self.change(self.pressed)
            self.pressed = None
        # I don't think it makes sense to consider it hovering if you
        # drag and drop something somewhere and then loiter. Hovering
        # is deliberate, this probably isn't

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.grabbed is not None:
            self.grabbed.move_with_mouse(x, y, dx, dy, buttons, modifiers)
            self.change(self.grabbed)
            if isinstance(self.grabbed, Spot):
                for pawn in self.pawns_on(self.grabbed):
                    if pawn is not None:
                        self.change(pawn)
        elif self.pressed is not None:
            if hasattr(self.pressed, 'move_with_mouse'):
                self.pressed.move_with_mouse(x, y, dx, dy, buttons, modifiers)
                self.grabbed = self.pressed
                self.change(self.grabbed)
                self.pressed = None
            elif not point_is_in(x, y, self.pressed):
                self.change(self.pressed)
                self.pressed = None

    def add_board_to_batch(self):
        x = -1 * self.view_left
        y = -1 * self.view_bot
        s = pyglet.sprite.Sprite(self.board.img, x, y,
                                 batch=self.batch, group=self.boardgroup)
        self.boardsprite = s

    def add_menu_to_batch(self, menu):
        if menu.visible:
            color = menu.style.bg_inactive
            w = menu.getwidth()
            h = menu.getheight()
            pattern = pyglet.image.SolidColorImagePattern(color.tup)
            image = pattern.create_image(w, h)
            s = pyglet.sprite.Sprite(image, menu.getleft(), menu.getbot(),
                                     batch=self.batch, group=self.menugroup)
            self.drawn[menu] = s

    def add_menu_item_to_batch(self, mi):
        if mi.visible and mi.menu.visible:
            sty = mi.menu.style
            if self.hovered is mi:
                color = sty.fg_active
            else:
                color = sty.fg_inactive
            left = mi.getleft()
            bot = mi.getbot()
            l = pyglet.text.Label(mi.text, sty.fontface, sty.fontsize,
                                  color=color.tup, x=left, y=bot,
                                  batch=self.batch, group=self.labelgroup)
            self.drawn[mi] = l

    def add_calendar_wall_to_batch(self, wall):
        if wall.visible:
            color = wall.style.bg_inactive
            w = wall.getwidth()
            h = wall.getheight()
            pattern = pyglet.image.SolidColorImagePattern(color.tup)
            image = pattern.create_image(w, h)
            s = pyglet.sprite.Sprite(image, wall.getleft(), wall.getbot(),
                                     batch=self.batch,
                                     group=self.calendargroup)
            self.drawn[wall] = s

    def add_calendar_brick_to_batch(self, brick):
        if brick.visible and brick.wall.visible:
            sty = brick.wall.style
            if self.hovered is brick:
                bgcolor = sty.bg_active
                fgcolor = sty.fg_active
            else:
                bgcolor = sty.bg_inactive
                fgcolor = sty.fg_inactive
            pattern = pyglet.image.SolidColorImagePattern(bgcolor.tup)
            w = brick.getwidth()
            h = brick.getheight()
            image = pattern.create_image(w, h)
            brickleft = brick.getleft()
            brickbot = brick.getbot()
            bricktop = brick.gettop()
            # Assuming one-line labels, and one label per brick.
            # Not a sturdy assumption, fix later.
            labelbot = bricktop - sty.fontsize - sty.spacing
            labelleft = brickleft + sty.spacing
            s = pyglet.sprite.Sprite(image, brickleft, brickbot,
                                     batch=self.batch, group=self.brickgroup)
            l = pyglet.text.Label(brick.text, sty.fontface, sty.fontsize,
                                  color=fgcolor.tup, x=labelleft, y=labelbot,
                                  batch=self.batch, group=self.labelgroup)
            self.drawn[brick] = (s, l)

    def add_spot_to_batch(self, spot):
        if spot.visible:
            s = pyglet.sprite.Sprite(spot.img, spot.x - spot.r, spot.y -
                                     spot.r, batch=self.batch,
                                     group=self.spotgroup)
            self.drawn[spot] = s

    def add_spot_edges_to_batch(self, spot):
        e = []
        for portal in spot.place.portals:
            otherspot = portal.dest.spot
            e.extend([spot.x, spot.y, otherspot.x, otherspot.y])
        if len(e) > 0:
            ee = self.batch.add(len(e) / 2, pyglet.graphics.GL_LINES,
                                self.edgegroup, ('v2i', e))
            self.drawn["edges"][spot] = ee

    def add_pawn_to_batch(self, pawn):
        # Getting the window coordinates whereupon to put the pawn
        # will not be simple.  I'll first need the two places the
        # thing stands between now; or, if it is not on a journey,
        # then just its location. That's an easy case: draw the pawn
        # on top of the spot for the location. But otherwise, I must
        # find the spots to represent the beginning and the end of the
        # portal in which the thing stands, and find the point the
        # correct proportion of the distance between them.
        if hasattr(pawn, 'journey'):
            port = pawn.thing.journey.getstep(0)
            prog = pawn.thing.progress
            whence = self.db.spotdict[port.orig.name]
            thence = self.db.spotdict[port.dest.name]
            # a line between them
            rise = thence.y - whence.y
            run = thence.x - whence.x
            # a point on the line, at prog * its length
            x = whence.x + prog * run
            y = whence.y + prog * rise
            # this may put it off the bounds of the screen
            s = pyglet.sprite.Sprite(pawn.img, x - pawn.r, y,
                                     batch=self.batch, group=self.pawngroup)
        else:
            dim = pawn.board.dimension
            locn = pawn.thing.location.name
            spot = self.db.spotdict[dim][locn]
            # Pawns are centered horizontally, but not vertically, on
            # the spot they stand.  This prevents them from covering
            # the spot overmuch while still making them look like
            # they're "on top" of the spot.
            x = spot.x
            y = spot.y
            s = pyglet.sprite.Sprite(pawn.img, x - pawn.r, y,
                                     batch=self.batch, group=self.pawngroup)
        self.drawn[pawn] = s

    def pawns_on(self, spot):
        return [thing.pawn
                for thing in self.db.things_in_place(spot.place)]
