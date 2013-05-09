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
        self.cellgroup = pyglet.graphics.OrderedGroup(5)
        self.labelgroup = pyglet.graphics.OrderedGroup(5)

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
        self.resized = True
        self.batch = batch
        self.menus = self.board.menudict.values()
        self.spots = self.board.spotdict.values()
        self.pawns = self.board.pawndict.values()
        self.portals = self.board.dimension.portaldict.values()
        self.calendars = self.board.calendardict.values()
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
                col_todo = [
                    calcol for calcol in self.calendars if
                    calcol.get_state_tup() not in self.onscreen]
                cel_todo = []
                for calcol in col_todo:
                    cel_todo.extend(
                        [cel for cel in calcol.cells if
                         cel.get_state_tup() not in self.onscreen])
            # delete stuff not being drawn anymore; update onscreen
            for todo in [menus_todo, mi_todo, pawn_todo,
                         spot_todo, col_todo, cel_todo]:
                for widget in todo:
                    try:
                        widget.sprite.delete()
                    except AttributeError:
                        pass
                    newstate = widget.get_state_tup()
                    if widget.visible:
                        self.onscreen.add(newstate)
                    else:
                        self.onscreen.discard(widget.oldstate)
                    widget.oldstate = widget.newstate
                    widget.newstate = newstate
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
            # draw the pawns, representing things
            for pawn in pawn_todo:
                if pawn.visible:
                    (x, y) = pawn.getcoords()
                    pawn.sprite = pyglet.sprite.Sprite(
                        pawn.img, x, y, batch=self.batch,
                        group=self.pawngroup)
            # draw the menus, really just their backgrounds for the moment
            for menu in menus_todo:
                if self.resized:
                    menu.set_gw(self)
                w = menu.width
                h = menu.height
                image = menu.inactive_pattern.create_image(w, h)
                menu.sprite = pyglet.sprite.Sprite(
                    image, menu.left, menu.bot,
                    batch=self.batch, group=self.menugroup)
            # draw the menu items proper
            for mitem in mi_todo:
                sty = mitem.menu.style
                if self.hovered == mitem:
                    color = sty.fg_active
                else:
                    color = sty.fg_inactive
                left = mitem.menu.left,
                bot = mitem.bot,
                mitem.label = pyglet.text.Label(
                    mitem.text, sty.fontface, sty.fontsize,
                    color=color.tup, x=left, y=bot,
                    batch=self.batch, group=self.labelgroup)
            # draw the calendars
            for col in col_todo:
                if self.resized:
                    col.set_gw(self)
                w = col.width
                h = col.height
                image = col.inactive_pattern.create_image(w, h)
                col.sprite = pyglet.sprite.Sprite(
                    image, col.left, col.bot,
                    batch=self.batch, group=self.calendargroup)
                # It would be a lot nicer if I only adjusted when the
                # calendar scrolled, rather than whenever it's rendered.
                col.adjust()
            # draw the cells in the calendars
            for cel in cel_todo:
                w = cel.width
                h = cel.height
                if self.hovered is cel:
                    pattern = cel.active_pattern
                else:
                    pattern = cel.inactive_pattern
                image = pattern.create_image(w, h)
                cel.sprite = pyglet.sprite.Sprite(
                    image, cel.left, cel.bot,
                    batch=self.batch, group=self.cellgroup)
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

        @window.event
        def on_resize(w, h):
            self.width = w
            self.height = h
            self.resized = True
