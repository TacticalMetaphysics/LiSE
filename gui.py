import pyglet
import ctypes
import math
import logging
from edge import Edge
from math import tan, sin, cos, atan, sqrt, pi
ninety = pi / 2

fortyfive = pi / 4

threesixty =  pi * 2

line_len_hints = {}

def line_len_rise_run(rise, run):
    if rise == 0:
        return run
    elif run == 0:
        return rise
    else:
        if rise not in line_len_hints:
            line_len_hints[rise] = {}
        if run not in line_len_hints[rise]:
            line_len_hints[rise][run] = sqrt(rise**2 + run**2)
        return line_len_hints[rise][run]

def line_len(ox, oy, dx, dy):
    rise = dy - oy
    run = dx - ox
    return line_len_rise_run(rise, run)


slope_theta_hints = {}

def slope_theta_rise_run(rise, run):
    if rise not in slope_theta_hints:
        slope_theta_hints[rise] = {}
    if run not in slope_theta_hints[rise]:
        try:
            slope_theta_hints[rise][run] = atan(rise/run)
        except ZeroDivisionError:
            if rise >= 0:
                return ninety
            else:
                return -1 * ninety
    return slope_theta_hints[rise][run]

def slope_theta(ox, oy, dx, dy):
    rise = dy - oy
    run = dx - ox
    return slope_theta_rise_run(rise, run)


opp_theta_hints = {}

def opp_theta_rise_run(rise, run):
    if run not in opp_theta_hints:
        opp_theta_hints[run] = {}
    if rise not in opp_theta_hints[run]:
        try:
            opp_theta_hints[run][rise] = atan(run/rise)
        except ZeroDivisionError:
            if run >= 0:
                opp_theta_hints[run][rise] = ninety
            else:
                opp_theta_hints[run][rise] = -1 * ninety
    return opp_theta_hints[run][rise]

def opp_theta(ox, oy, dx, dy):
    rise = dy - oy
    run = dx - ox
    return opp_theta_rise_run(rise, run)


def truncated_line(leftx, boty, rightx, topy, r, from_start=False):
    # presumes pointed up and right
    if r == 0:
        return (leftx, boty, rightx, topy)
    rise = topy - boty
    run = rightx - leftx
    length = line_len_rise_run(rise, run) - r
    theta = slope_theta_rise_run(rise, run)
    if from_start:
        leftx = rightx - cos(theta) * length
        boty = topy - sin(theta) * length
    else:
        rightx = leftx + cos(theta) * length
        topy = boty + sin(theta) * length
    return (leftx, boty, rightx, topy)

def trimmed_line(leftx, boty, rightx, topy, trim_start, trim_end):
    et = truncated_line(leftx, boty, rightx, topy, trim_end)
    return truncated_line(et[0], et[1], et[2], et[3], trim_start, True)

wedge_offset_hints = {}

def wedge_offsets(rise, run, taillen):
    # theta is the slope of a line bisecting the ninety degree wedge.
    # theta == atan(rise/run)
    # tan(theta) == rise/run
    # opp_theta == atan(run/rise)
    # tan(opp_theta) == run/rise
    # 1/tan(theta) == run/rise == tan(opp_theta)
    # atan(1/tan(theta)) == opp_theta
    if rise not in wedge_offset_hints:
        wedge_offset_hints[rise] = {}
    if run not in wedge_offset_hints[rise]:
        wedge_offset_hints[rise][run] = {}
    if taillen not in wedge_offset_hints[rise][run]:
        theta = slope_theta_rise_run(rise, run)
        opp_theta = opp_theta_rise_run(rise, run)
        if theta > fortyfive:
            top_theta = threesixty + theta - fortyfive
            bot_theta = threesixty + fortyfive - opp_theta
        else:
            top_theta = threesixty + fortyfive - theta
            bot_theta = threesixty + opp_theta - fortyfive
        xoff1 = sin(top_theta) * taillen
        yoff1 = cos(top_theta) * taillen
        xoff2 = sin(bot_theta) * taillen
        yoff2 = cos(bot_theta) * taillen
        wedge_offset_hints[rise][run][taillen] = (
            xoff1, yoff1, xoff2, yoff2)
    return wedge_offset_hints[rise][run][taillen]

def get_line_width():
    see = ctypes.c_float()
    pyglet.gl.glGetFloatv(pyglet.gl.GL_LINE_WIDTH, see)
    return float(see.value)

def set_line_width(w):
    wcf = ctypes.c_float(w)
    pyglet.gl.glLineWidth(wcf)


class BoldLineGroup(pyglet.graphics.Group):
    def __init__(self, parent=None, width=1.0):
        super(BoldLineGroup, self).__init__(parent)
        self.width = float(width)

    def set_state(self):
        self.oldwidth = get_line_width()
        set_line_width(self.width)

    def unset_state(self):
        set_line_width(self.oldwidth)

class BoldLineOrderedGroup(pyglet.graphics.OrderedGroup, BoldLineGroup):
    def __init__(self, order, parent=None, width=1.0):
        pyglet.graphics.OrderedGroup.__init__(self, order, parent)
        self.width = float(width)

class TransparencyGroup(pyglet.graphics.Group):
    def set_state(self):
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)

    def unset_state(self):
        pyglet.gl.glDisable(pyglet.gl.GL_BLEND)

class TransparencyOrderedGroup(pyglet.graphics.OrderedGroup, TransparencyGroup):
    pass


class GameWindow:
    arrowhead_angle = 45
    arrowhead_len = 10
    # One window, batch, and WidgetFactory per board.

    def __init__(self, gamestate, boardname):
        self.squareoff = self.arrowhead_size * sin(fortyfive)
        self.db = gamestate.db
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

        @window.event
        def on_resize(w, h):
            """Inform the on_draw function that the window's been resized."""
            self.resized = True

        @window.event
        def on_mouse_scroll(x, y, scroll_x, scroll_y):
            # for now, this only does anything if you're moused over
            # the calendar
            if (
                    self.calendar.visible and
                    x > self.calendar.window_left and
                    x < self.calendar.window_right and
                    y > self.calendar.window_bot and
                    y < self.calendar.window_top):
                sf = self.calendar.scroll_factor
                self.calendar.scrolled_to -= scroll_y * sf
                if self.calendar.scrolled_to < 0:
                    self.calendar.scrolled_to = 0

    def __getattr__(self, attrn):
        if attrn == 'width':
            return self.window.width
        elif attrn == 'height':
            return self.window.height
        else:
            raise AttributeError(
                "GameWindow has no attribute named {0}".format(attrn))

    def create_place(self):
        self.window.set_mouse_cursor(self.create_place_cursor)
        self.placing = True

    def create_thing(self):
        self.thinging = True

    def create_portal(self):
        self.portaling = True

    def connect_arrow(self, ox, oy, dx, dy,
                      center_shrink=0,
                      old_vertlist_left=None,
                      old_vertlist_center=None,
                      old_vertlist_right=None,
                      order=0):
        # xs and ys should be integers.
        #
        # results will be called l, c, r for left tail, center, right tail
        if old_vertlist_center is None:
            obg = None
            ofg = None
        else:
            obg = old_vertlist_center[0]
            ofg = old_vertlist_center[1]
        c = self.connect_line(
            ox, oy, dx, dy, old_bg_vlist=obg, old_fg_vlist=ofg, order=order)
        if dy < oy:
            yco = -1
        else:
            yco = 1
        if dx < ox:
            xco = -1
        else:
            xco = 1
        (leftx, boty, rightx, topy) = truncated_line(
            float(ox * xco), float(oy * yco),
            float(dx * xco), float(dy * yco), center_shrink)
        taillen = float(self.arrowhead_size)
        rise = topy - boty
        run = rightx - leftx
        if rise == 0:
            xoff1 = self.squareoff * taillen
            yoff1 = xoff1
            xoff2 = xoff1
            yoff2 = -1 * yoff1
        elif run == 0:
            xoff1 = self.squareoff * taillen
            yoff1 = xoff1
            xoff2 = -1 * xoff1
            yoff2 = yoff1
        else:
            (xoff1, yoff1, xoff2, yoff2) = wedge_offsets(
                rise, run, taillen)
        x1 = int(rightx - xoff1) * xco
        x2 = int(rightx - xoff2) * xco
        y1 = int(topy - yoff1) * yco
        y2 = int(topy - yoff2) * yco
        endx = int(rightx) * xco
        endy = int(topy) * yco
        if old_vertlist_left is None:
            obg = None
            ofg = None
        else:
            obg = old_vertlist_left[0]
            ofg = old_vertlist_left[1]
        l = self.connect_line(
            x1, y1, endx, endy, old_bg_vlist=obg, old_fg_vlist=ofg, order=order)
        if old_vertlist_right is None:
            obg = None
            ofg = None
        else:
            obg = old_vertlist_right[0]
            ofg = old_vertlist_right[1]
        r = self.connect_line(
            x2, y2, endx, endy, old_bg_vlist=obg, old_fg_vlist=ofg, order=order)
        return (l, c, r)


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
