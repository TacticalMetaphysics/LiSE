import pyglet


class GameWindow:
    arrowhead_angle = 45
    arrowhead_len = 10

    def __init__(self, gamestate, boardname, batch=None):
        self.db = gamestate.db
        self.gamestate = gamestate
        self.board = self.db.boarddict[boardname]

        self.boardgroup = pyglet.graphics.OrderedGroup(0)
        self.edgegroup = pyglet.graphics.OrderedGroup(1)
        self.spotgroup = pyglet.graphics.OrderedGroup(2)
        self.pawngroup = pyglet.graphics.OrderedGroup(3)
        self.menugroup = pyglet.graphics.OrderedGroup(4)
        self.calendargroup = pyglet.graphics.OrderedGroup(4)
        self.cellgroup = pyglet.graphics.OrderedGroup(5)
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
        self.prev_view_left = 0
        self.prev_view_bot = 0
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
        self.width = self.window.width
        self.height = self.window.height
        self.batch = batch
        self.menus = self.board.menudict.values()
        self.spots = self.board.spotdict.values()
        self.pawns = self.board.pawndict.values()
        self.portals = self.board.dimension.portaldict.values()
        self.calendars = self.board.calendardict.values()
        for menu in self.menus:
            menu.set_gw(self)
        for calendar in self.calendars:
            calendar.set_gw(self)
        self.drawn_board = None
        self.drawn_edges = None
        self.cels_drawn = {}

        self.onscreen = set()

        @window.event
        def on_draw():
            # draw the background image
            x = -1 * self.view_left
            y = -1 * self.view_bot
            s = pyglet.sprite.Sprite(
                self.board.wallpaper, x, y,
                batch=self.batch, group=self.boardgroup)
            try:
                self.drawn_board.delete()
            except AttributeError:
                pass
            self.drawn_board = s
            # if the background image has moved since last frame, then
            # so has everything else
            redraw_all = (self.view_left != self.prev_view_left or
                          self.view_bot != self.prev_view_bot)
            self.view_left = self.prev_view_left
            self.view_bot = self.prev_view_bot
            portal_todo = self.portals
            if redraw_all:
                menus_todo = self.menus
                mi_todo = []
                for menu in menus_todo:
                    mi_todo.extend(menu.items)
                pawn_todo = self.pawns
                spot_todo = self.spots
                col_todo = self.calendars
                cel_todo = []
                for col in col_todo:
                    cel_todo.extend(col.cells)
            else:
                menus_todo = [
                    menu for menu in self.menus if
                    menu.get_state_tup() not in self.onscreen]
                mi_todo = []
                for menu in self.menus:
                    mi_todo.extend([
                        it for it in menu.items if
                        it.get_state_tup() not in self.onscreen])
                pawn_todo = [
                    pawn for pawn in self.pawns if
                    pawn.get_state_tup() not in self.onscreen]
                spot_todo = [
                    spot for spot in self.spots if
                    spot.get_state_tup() not in self.onscreen]
                col_todo = [
                    calcol for calcol in self.calendars if
                    calcol.get_state_tup() not in self.onscreen]
                cel_todo = []
                for col in self.calendars:
                    cel_todo.extend([
                        cel for cel in col.cells if
                        cel.get_state_tup() not in self.onscreen])
            # draw the edges, representing portals
            e = []
            for portal in portal_todo:
                origspot = portal.orig.spot
                destspot = portal.dest.spot
                edge = (origspot.x, origspot.y, destspot.x, destspot.y)
                e.extend(edge)
            try:
                self.drawn_edges.delete()
            except AttributeError:
                pass
            self.drawn_edges = self.batch.add(
                len(e) / 2, pyglet.graphics.GL_LINES,
                self.edgegroup, ('v2i', e))
            # draw the spots, representing places
            for spot in spot_todo:
                self.onscreen.discard(spot.oldstate)
                newstate = spot.get_state_tup()
                self.onscreen.add(newstate)
                spot.oldstate = newstate
                try:
                    spot.sprite.delete()
                except AttributeError:
                    pass
                if spot.visible:
                    (x, y) = spot.getcoords()
                    spot.sprite = pyglet.sprite.Sprite(
                        spot.img, x, y, batch=self.batch,
                        group=self.spotgroup)
            # draw the pawns, representing things
            for pawn in pawn_todo:
                newstate = pawn.get_state_tup()
                self.onscreen.discard(pawn.oldstate)
                self.onscreen.add(newstate)
                pawn.oldstate = newstate
                try:
                    pawn.sprite.delete()
                except AttributeError:
                    pass
                if pawn.visible:
                    (x, y) = pawn.getcoords()
                    pawn.sprite = pyglet.sprite.Sprite(
                        pawn.img, x, y, batch=self.batch,
                        group=self.pawngroup)
            # draw the menus, really just their backgrounds for the moment
            for menu in menus_todo:
                newstate = menu.get_state_tup()
                self.onscreen.discard(menu.oldstate)
                self.onscreen.add(newstate)
                menu.oldstate = newstate
                try:
                    menu.sprite.delete()
                except AttributeError:
                    pass
                if menu.visible:
                    image = (
                        menu.inactive_pattern.create_image(
                            menu.getwidth(),
                            menu.getheight()))
                    menu.sprite = pyglet.sprite.Sprite(
                        image, menu.getleft(), menu.getbot(),
                        batch=self.batch, group=self.menugroup)
            for mi in mi_todo:
                newstate = mi.get_state_tup()
                self.onscreen.discard(mi.oldstate)
                self.onscreen.add(newstate)
                mi.oldstate = newstate
                try:
                    mi.label.delete()
                except AttributeError:
                    pass
                if mi.menu.visible and mi.visible:
                    sty = mi.menu.style
                    if mi.hovered:
                        color = sty.fg_active.tup
                    else:
                        color = sty.fg_inactive.tup
                    mi.label = pyglet.text.Label(
                        mi.text,
                        sty.fontface,
                        sty.fontsize,
                        color=color,
                        x=mi.getleft(),
                        y=mi.getbot(),
                        batch=self.batch,
                        group=self.labelgroup)
            # draw the calendars
            for col in col_todo:
                col.adjust()
                newstate = col.get_state_tup()
                self.onscreen.discard(col.oldstate)
                self.onscreen.add(newstate)
                col.oldstate = newstate
                if hasattr(col, 'sprite') and col.sprite is not None:
                    try:
                        col.sprite.delete()
                    except AttributeError:
                        pass
                image = col.inactive_pattern.create_image(
                    col.getwidth(), col.getheight())
                if col.visible:
                    col.sprite = pyglet.sprite.Sprite(
                        image, col.getleft(), col.getbot(),
                        batch=self.batch, group=self.calendargroup)
            # draw the cells in the calendars
            for cel in cel_todo:
                newstate = cel.get_state_tup()
                self.onscreen.discard(cel.oldstate)
                self.onscreen.add(newstate)
                cel.oldstate = newstate
                try:
                    ptr = self.cels_drawn[hash(cel)]
                    ptr[0].delete()
                    ptr[1].delete()
                except KeyError:
                    pass
                except AttributeError:
                    pass
                if cel.visible and cel.calendar.visible:
                    print "Cel and col are visible. Drawing."
                    if self.hovered == cel:
                        pat = cel.active_pattern
                        color = cel.style.fg_active.tup
                    else:
                        pat = cel.inactive_pattern
                        color = cel.style.fg_inactive.tup
                    image = pat.create_image(
                        cel.getwidth(), cel.getheight())
                    sprite = pyglet.sprite.Sprite(
                        image, cel.getleft(), cel.getbot(),
                        batch=self.batch, group=self.cellgroup)
                    label = pyglet.text.Label(
                        cel.text,
                        cel.style.fontface,
                        cel.style.fontsize,
                        color=color,
                        x=cel.getleft(),
                        y=cel.label_bot(),
                        batch=self.batch,
                        group=self.labelgroup)
                    self.cels_drawn[hash(cel)] = (sprite, label)
            # well, I lied. I was really only adding those things to the batch.
            # NOW I'll draw them.
            self.batch.draw()
            self.resized = False

        @window.event
        def on_key_press(sym, mods):
            self.on_key_press(sym, mods)

        @window.event
        def on_mouse_motion(x, y, dx, dy):
            if self.hovered is None:
                for menu in self.menus:
                    if (
                            x > menu.getleft() and
                            x < menu.getright() and
                            y > menu.getbot() and
                            y < menu.gettop()):
                        for item in menu.items:
                            if (
                                    x > item.getleft() and
                                    x < item.getright() and
                                    y > item.getbot() and
                                    y < item.gettop()):
                                if hasattr(item, 'set_hovered'):
                                    item.set_hovered()
                                self.hovered = item
                                return
                for spot in self.spots:
                    if (
                            x > spot.getleft() and
                            x < spot.getright() and
                            y > spot.getbot() and
                            y < spot.gettop()):
                        if hasattr(spot, 'set_hovered'):
                            spot.set_hovered()
                        self.hovered = spot
                        return
                for pawn in self.pawns:
                    if (
                            x > pawn.getleft() and
                            x < pawn.getright() and
                            y > pawn.getbot() and
                            y < pawn.gettop()):
                        if hasattr(pawn, 'set_hovered'):
                            pawn.set_hovered()
                        self.hovered = pawn
                        return
            else:
                if (
                        x < self.hovered.getleft() or
                        x > self.hovered.getright() or
                        y < self.hovered.getbot() or
                        y > self.hovered.gettop()):
                    if hasattr(self.hovered, 'unset_hovered'):
                        self.hovered.unset_hovered()
                    self.hovered = None

        @window.event
        def on_mouse_press(x, y, button, modifiers):
            if self.hovered is None:
                return
            else:
                self.pressed = self.hovered
                if hasattr(self.pressed, 'set_pressed'):
                    self.pressed.set_pressed()

        @window.event
        def on_mouse_release(x, y, button, modifiers):
            if self.grabbed is not None:
                if hasattr(self.grabbed, 'dropped'):
                    self.grabbed.dropped(x, y, button, modifiers)
                self.grabbed = None
            elif (self.pressed is not None and
                  x > self.pressed.getleft() and
                  x < self.pressed.getright() and
                  y > self.pressed.getbot() and
                  y < self.pressed.gettop() and
                  hasattr(self.pressed, 'onclick')):
                    self.pressed.onclick(button, modifiers)
            if self.pressed is not None:
                if hasattr(self.pressed, 'unset_pressed'):
                    self.pressed.unset_pressed()
                self.pressed = None

        @window.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            if self.grabbed is not None:
                self.grabbed.move_with_mouse(x, y, dx, dy, buttons, modifiers)
            elif (self.pressed is not None and
                  x > self.pressed.getleft() and
                  x < self.pressed.getright() and
                  y > self.pressed.getbot() and
                  y < self.pressed.gettop() and
                  hasattr(self.pressed, 'move_with_mouse')):
                    self.grabbed = self.pressed
            else:
                if self.pressed is not None:
                    self.pressed.unset_pressed()
                    self.pressed = None
                self.grabbed = None

        @window.event
        def on_resize(w, h):
            self.width = w
            self.height = h
            self.resized = True
