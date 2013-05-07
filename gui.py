import pyglet


def point_is_in(x, y, listener):
    return x >= listener.getleft() and x <= listener.getright() \
        and y >= listener.getbot() and y <= listener.gettop()


def point_is_between(x, y, x1, y1, x2, y2):
    return x >= x1 and x <= x2 and y >= y1 and y <= y2


class GameWindow:
    arrowhead_angle = 45
    arrowhead_len = 10
    # One window, batch, and WidgetFactory per board.

    def __init__(self, db, gamestate, boardname, batch=None):
        self.db = db
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
        self.calendar_changed = False
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_buttons = 0
        self.mouse_mods = 0
        self.view_left = 0
        self.view_bot = 0

        self.to_mouse = (
            self.board.pawndict.values() +
            self.board.spotdict.values())
        for menu in self.board.menudict.itervalues():
            self.to_mouse.extend(menu.items)

        window = pyglet.window.Window()
        window.set_minimum_size(self.board.getviewwidth(),
                                self.board.getviewheight())
        if batch is None:
            batch = pyglet.graphics.Batch()

        self.window = window
        self.batch = batch
        self.drawn_menus = set()
        self.drawn_mis = set()
        self.drawn_spots = set()
        self.drawn_pawns = set()
        self.drawn_board = None
        self.drawn_edges = None

        for menu in self.board.menudict.itervalues():
            menu.window = self.window

        @window.event
        def on_draw():
            for menu in self.board.menudict.itervalues():
                if menu.visible:
                    if menu in self.drawn_menus:
                        self.update_menu_sprite(menu)
                    else:
                        self.create_menu_sprite(menu)
                elif menu in self.drawn_menus:
                    try:
                        menu.sprite.delete()
                        self.drawn_menus.discard(menu)
                    except AttributeError:
                        pass
                for item in menu.items:
                    if item.visible:
                        if item in self.drawn_mis:
                            self.update_mi_label(item)
                        else:
                            self.create_mi_label(item)
                    elif item in self.drawn_mis:
                        try:
                            item.label.delete()
                            self.drawn_mis.discard(item)
                        except AttributeError:
                            pass
            for pawn in self.board.pawndict.itervalues():
                if pawn.visible:
                    if pawn in self.drawn_pawns:
                        self.update_pawn_sprite(pawn)
                    else:
                        self.create_pawn_sprite(pawn)
                elif pawn in self.drawn_pawns:
                    try:
                        pawn.sprite.delete()
                        self.drawn_pawns.discard(pawn)
                    except AttributeError:
                        pass
            for spot in self.board.spotdict.itervalues():
                if spot.visible:
                    if spot in self.drawn_spots:
                        self.update_spot_sprite(spot)
                    else:
                        self.create_spot_sprite(spot)
                elif spot in self.drawn_spots:
                    try:
                        spot.sprite.delete()
                        self.drawn_spots.discard(spot)
                    except AttributeError:
                        pass
            try:
                self.drawn_board.delete()
            except AttributeError:
                pass
            try:
                self.drawn_edges.delete()
            except AttributeError:
                pass
            # draw the background image
            x = -1 * self.view_left
            y = -1 * self.view_bot
            s = pyglet.sprite.Sprite(
                self.board.wallpaper, x, y,
                batch=self.batch, group=self.boardgroup)
            self.drawn_board = s
            # draw the edges, representing portals
            e = []
            for portal in self.board.dimension.portaldict.itervalues():
                origspot = portal.orig.spot
                destspot = portal.dest.spot
                edge = (origspot.x, origspot.y, destspot.x, destspot.y)
                e.extend(edge)
            self.drawn_edges = self.batch.add(
                len(e) / 2, pyglet.graphics.GL_LINES,
                self.edgegroup, ('v2i', e))
            self.batch.draw()

        @window.event
        def on_key_press(sym, mods):
            self.on_key_press(sym, mods)

        @window.event
        def on_mouse_motion(x, y, dx, dy):
            if self.hovered is None:
                for moused in self.to_mouse:
                    if (
                            moused is not None
                            and moused.interactive
                            and point_is_in(x, y, moused)):
                        self.hovered = moused
                        moused.hovered = True
                        break
            else:
                if not point_is_in(x, y, self.hovered):
                    self.hovered.hovered = False
                    self.hovered = None

        @window.event
        def on_mouse_press(x, y, button, modifiers):
            if self.hovered is None:
                return
            else:
                self.pressed = self.hovered
                self.pressed.pressed = True

        @window.event
        def on_mouse_release(x, y, button, modifiers):
            if self.grabbed is not None:
                self.grabbed.dropped(x, y, button, modifiers)
                self.grabbed = None
            elif self.pressed is not None:
                if (
                        point_is_in(x, y, self.pressed) and
                        hasattr(self.pressed, 'onclick')):
                    self.pressed.onclick(button, modifiers)
            if self.pressed is not None:
                self.pressed.pressed = False
                self.pressed = None

        @window.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            if self.grabbed is not None:
                self.grabbed.move_with_mouse(x, y, dx, dy, buttons, modifiers)
            elif self.pressed is not None and point_is_in(x, y, self.pressed):
                if hasattr(self.pressed, 'move_with_mouse'):
                    self.grabbed = self.pressed
            else:
                if self.pressed is not None:
                    self.pressed.pressed = False
                    self.pressed = None
                self.grabbed = None

    def on_key_press(self, key, mods):
        pass

    def create_menu_sprite(self, menu):
        w = menu.getwidth()
        h = menu.getheight()
        x = menu.getleft() - self.board.getviewx()
        y = menu.getheight() - self.board.getviewy()
        image = menu.pattern.create_image(w, h)
        menu.sprite = pyglet.sprite.Sprite(
            image, x, y,
            batch=self.batch, group=self.menugroup)
        self.drawn_menus.add(menu)

    def update_menu_sprite(self, menu):
        w = menu.getwidth()
        h = menu.getheight()
        if menu.sprite.width != w or menu.sprite.height != h:
            menu.sprite.image = menu.pattern.create_image(w, h)
        menu.sprite.x = menu.getleft() - self.board.getviewx()
        menu.sprite.y = menu.getheight() - self.board.getviewy()

    def create_mi_label(self, mi):
        sty = mi.menu.style
        color = None
        if self.hovered == mi:
            color = sty.fg_active
        else:
            color = sty.fg_inactive
        x = mi.getleft()
        y = mi.getbot()
        mi.label = pyglet.text.Label(
            mi.text, sty.fontface, sty.fontsize,
            color=color.tup, x=x, y=y,
            batch=self.batch, group=self.labelgroup)
        self.drawn_mis.add(mi)

    def update_mi_label(self, mi):
        sty = mi.menu.style
        color = None
        if self.hovered == mi:
            color = sty.fg_active
        else:
            color = sty.fg_inactive
        x = mi.getleft()
        y = mi.getbot()
        mi.label.x = x
        mi.label.y = y
        mi.label.color = color.tup

    def create_spot_sprite(self, spot):
        (x, y) = spot.getcoords()
        spot.sprite = pyglet.sprite.Sprite(
            spot.img, x, y, batch=self.batch,
            group=self.spotgroup)
        self.drawn_spots.add(spot)

    def update_spot_sprite(self, spot):
        (x, y) = spot.getcoords()
        spot.sprite.x = x
        spot.sprite.y = y
        spot.sprite.image = spot.img.tex

    def create_pawn_sprite(self, pawn):
        (x, y) = pawn.getcoords()
        pawn.sprite = pyglet.sprite.Sprite(
            pawn.img, x, y, batch=self.batch,
            group=self.pawngroup)
        self.drawn_pawns.add(pawn)

    def update_pawn_sprite(self, pawn):
        (x, y) = pawn.getcoords()
        pawn.sprite.x = x
        pawn.sprite.y = y
        pawn.sprite.image = pawn.img.tex
