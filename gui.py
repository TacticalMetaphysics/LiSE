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
        if batch is None:
            batch = pyglet.graphics.Batch()

        self.window = window
        self.batch = batch
        self.menus = self.board.menudict.values()
        self.spots = self.board.spotdict.values()
        self.pawns = self.board.pawndict.values()
        self.portals = self.board.dimension.portaldict.values()
        self.drawn_menus = dict()
        self.drawn_mis = dict()
        self.drawn_spots = dict()
        self.drawn_pawns = dict()
        self.drawn_board = None
        self.drawn_edges = None
        for menu in self.menus:
            menu.window = self.window
            if menu.main_for_window:
                self.mainmenu = menu
            self.drawn_menus[menu.name] = None
            self.drawn_mis[menu.name] = [None] * len(menu.items)
        for spot in self.spots:
            self.drawn_spots[spot.place.name] = None
        for pawn in self.pawns:
            self.drawn_pawns[pawn.thing.name] = None

        self.onscreen = set()

        @window.event
        def on_draw():
            menus_todo = [
                menu for menu in self.menus if
                menu.get_state_tup() not in self.onscreen]
            mi_todo = []
            for menu in menus_todo:
                mi_todo.extend(
                    [item for item in menu.items if
                     item.get_state_tup() not in self.onscreen])
            pawn_todo = [
                pawn for pawn in self.pawns if
                pawn.get_state_tup() not in self.onscreen]
            spot_todo = [
                spot for spot in self.spots if
                spot.get_state_tup() not in self.onscreen]
            portal_todo = self.portals
            # delete stuff not being drawn anymore
            try:
                self.drawn_board.delete()
            except AttributeError:
                pass
            try:
                self.drawn_edges.delete()
            except AttributeError:
                pass
            for menu in menus_todo:
                try:
                    menu.sprite.delete()
                except AttributeError:
                    pass
            for menuitem in mi_todo:
                try:
                    menuitem.label.delete()
                except AttributeError:
                    pass
            for pawn in pawn_todo:
                try:
                    pawn.sprite.delete()
                except AttributeError:
                    pass
            for spot in spot_todo:
                try:
                    spot.sprite.delete()
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
            for portal in portal_todo:
                origspot = portal.orig.spot
                destspot = portal.dest.spot
                edge = (origspot.x, origspot.y, destspot.x, destspot.y)
                e.extend(edge)
            self.drawn_edges = self.batch.add(
                len(e) / 2, pyglet.graphics.GL_LINES,
                self.edgegroup, ('v2i', e))
            # draw the spots, representing places
            for spot in spot_todo:
                if spot.visible:
                    (x, y) = spot.getcoords()
                    spot.sprite = pyglet.sprite.Sprite(
                        spot.img, x, y, batch=self.batch,
                        group=self.spotgroup)
                    self.onscreen.discard(spot.oldstate)
                    newstate = spot.get_state_tup()
                    self.onscreen.add(newstate)
                    spot.oldstate = newstate
            # draw the pawns, representing things
            for pawn in pawn_todo:
                if pawn.visible:
                    (x, y) = pawn.getcoords()
                    pawn.sprite = pyglet.sprite.Sprite(
                        pawn.img, x, y, batch=self.batch,
                        group=self.pawngroup)
                    self.onscreen.discard(pawn.oldstate)
                    newstate = pawn.get_state_tup()
                    self.onscreen.add(newstate)
                    pawn.oldstate = newstate
            # draw the menus, really just their backgrounds for the moment
            for menu in menus_todo:
                if menu.visible:
                    w = menu.getwidth()
                    h = menu.getheight()
                    image = menu.pattern.create_image(w, h)
                    menu.sprite = pyglet.sprite.Sprite(
                        image, menu.getleft(), menu.getbot(),
                        batch=self.batch, group=self.menugroup)
                    self.onscreen.discard(menu.oldstate)
                    newstate = menu.get_state_tup()
                    self.onscreen.add(newstate)
                    menu.oldstate = newstate
            # draw the menu items proper
            for mitem in mi_todo:
                if mitem.visible and mitem.menu.visible:
                    sty = mitem.menu.style
                    if self.hovered == mitem:
                        color = sty.fg_active
                    else:
                        color = sty.fg_inactive
                    left = mitem.getleft()
                    bot = mitem.getbot()
                    mitem.label = pyglet.text.Label(
                        mitem.text, sty.fontface, sty.fontsize,
                        color=color.tup, x=left, y=bot,
                        batch=self.batch, group=self.labelgroup)
                    self.onscreen.discard(mitem.oldstate)
                    newstate = mitem.get_state_tup()
                    self.onscreen.add(newstate)
                    mitem.oldstate = newstate
            # well, I lied. I was really only adding those things to the batch.
            # NOW I'll draw them.
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

    def dumb_m2b(self):
        for menu in self.menus:
            if not menu.visible:
                print "Not drawing invisible menu {0}".format(menu.name)
                return
            old = self.drawn_menus[menu.name]
            self.drawn_menus[menu.name] = self.add_menu_to_batch(menu)
            try:
                old.delete()
            except AttributeError:
                pass

    def add_menus_to_batch(self, dumb=False):
        if dumb:
            return self.dumb_m2b()
        for menu in self.menus:
            state = menu.get_state_tup()
            statehash = hash(state)
            if not menu.visible:
                return
            (mtup, sprite) = self.drawn_menus[menu.name]
            # mtup holds the menu's state last time it was drawn.
            # if the menu's state now is not the same,
            # delete the old sprite, draw anew.
            if mtup != statehash:
                try:
                    sprite.delete()
                except AttributeError:
                    pass
                self.drawn_menus[menu.name] = (
                    statehash, self.add_menu_to_batch(menu))

    def add_menu_item_to_batch(self, mi):
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
        return l

    def dumb_mis2b(self):
        for menu in self.menus:
            for item in menu.items:
                if not item.visible:
                    return
                old = self.drawn_mis[menu.name][item.idx]
                self.drawn_mis[menu.name][item.idx] = (
                    self.add_menu_item_to_batch(item))
                try:
                    old.delete()
                except AttributeError:
                    pass

    def add_menu_items_to_batch(self, dumb=False):
        if dumb:
            return self.dumb_mis2b()
        for menu in self.menus:
            for item in menu.items:
                state = item.get_state_tup()
                statehash = hash(state)
                if not item.visible or not item.menu.visible:
                    return
                (itup, sprite) = self.drawn_mis[menu.name][item.idx]
                if itup != statehash:
                    try:
                        sprite.delete()
                    except AttributeError:
                        pass
                    self.drawn_mis[menu.name][item.idx] = (
                        statehash, self.add_menu_item_to_batch(item))

    def dumbpawns2b(self):
        for pawn in self.pawns:
            if not pawn.visible:
                return
            old = self.drawn_pawns[pawn.thing.name]
            self.drawn_pawns[pawn.thing.name] = self.add_pawn_to_batch(pawn)
            try:
                old.delete()
            except AttributeError:
                pass

    def add_pawns_to_batch(self, dumb=False):
        if dumb:
            return self.dumbpawns2b()
        for pawn in self.pawns:
            state = pawn.get_state_tup()
            statehash = hash(state)
            (ptup, sprite) = self.drawn_pawns[pawn.thing.name]
            if ptup != statehash:
                try:
                    sprite.delete()
                except AttributeError:
                    pass
                self.drawn_pawns[pawn.thing.name] = (
                    statehash, self.add_pawn_to_batch(pawn))
