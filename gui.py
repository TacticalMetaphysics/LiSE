import pyglet
import math
import logging
from edge import Edge

logger = logging.getLogger(__name__)

ninety = math.pi / 2

fortyfive = math.pi / 4

threesixty = math.pi * 2


class DummyEdge:
    visible = True

nedge = DummyEdge()


class GameWindow:
    """Instantiates a Pyglet window and displays the given board in it."""
    arrowhead_size = 10

    def __init__(self, gamestate, boardname):
        self.squareoff = self.arrowhead_size * math.sin(fortyfive)

        self.db = gamestate.db
        self.gamestate = gamestate

        self.boardgroup = pyglet.graphics.OrderedGroup(0)
        self.edgegroup = pyglet.graphics.OrderedGroup(1)
        self.spotgroup = pyglet.graphics.OrderedGroup(2)
        self.pawngroup = pyglet.graphics.OrderedGroup(3)
        self.menugroup = pyglet.graphics.OrderedGroup(4)
        self.calendargroup = pyglet.graphics.OrderedGroup(4)
        self.cellgroup = pyglet.graphics.OrderedGroup(5)
        self.card_bg_group = pyglet.graphics.OrderedGroup(6)
        self.card_text_bg_group = pyglet.graphics.OrderedGroup(7)
        self.card_img_group = pyglet.graphics.OrderedGroup(8)
        self.labelgroup = pyglet.graphics.OrderedGroup(10)
        self.topgroup = pyglet.graphics.OrderedGroup(65535)

        self.pressed = None
        self.hovered = None
        self.grabbed = None
        self.prev_view_bot = 0
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        window = pyglet.window.Window()

        self.window = window
        self.batch = pyglet.graphics.Batch()

        self.board = self.db.boarddict[boardname]
        self.board.set_gw(self)
        # replace this
        for port in self.board.dimension.portals:
            Edge(self.board.db, self.board.dimension, port).unravel()
        self.calcols = []
        for pawn in self.board.pawndict.itervalues():
            if hasattr(pawn, 'calcol'):
                self.calcols.append(pawn.calcol)
        self.calendar = self.board.calendar
        self.drawn_board = None
        self.drawn_edges = None
        self.timeline = None

        self.onscreen = set()
        self.last_age = -1
        self.last_timeline_y = -1

        orbimg = self.db.imgdict['default_spot']
        rx = orbimg.width / 2
        ry = orbimg.height / 2
        self.create_place_cursor = pyglet.window.ImageMouseCursor(orbimg, rx, ry)
        self.create_place_cursor.rx = rx
        self.create_place_cursor.ry = ry
        self.placing = False
        self.thinging = False
        self.portaling = False
        self.portal_from = None
        self.edge_from_portal_from = None
        self.left_tail_edge_from_portal_from = None
        self.right_tail_edge_from_portal_from = None

        @window.event
        def on_draw():
            """Draw the background image; all spots, pawns, and edges on the
board; all visible menus; and the calendar, if it's visible."""
            from math import atan
            # draw the edges, representing portals
            if self.portal_from is not None: 
                (self.left_tail_edge_from_portal_from,
                 self.edge_from_portal_from,
                 self.right_tail_edge_from_portal_from
                ) = self.connect_arrow(
                    self.portal_from.window_x,
                    self.portal_from.window_y,
                    self.last_mouse_x,
                    self.last_mouse_y,
                    0,
                    self.left_tail_edge_from_portal_from,
                    self.edge_from_portal_from,
                    self.right_tail_edge_from_portal_from)
            for edge in self.board.edges:
                newstate = edge.get_state_tup()
                if newstate in self.onscreen:
                    continue
                self.onscreen.discard(edge.oldstate)
                self.onscreen.add(newstate)
                edge.oldstate = newstate
                if edge.visible:
                    (edge.wedge_a,
                     edge.vertlist,
                     edge.wedge_b
                    ) = self.connect_arrow(
                         edge.orig.window_x,
                         edge.orig.window_y,
                         edge.dest.window_x,
                         edge.dest.window_y,
                         edge.dest.r,
                         edge.wedge_a,
                         edge.vertlist,
                         edge.wedge_b)
                else:
                    if edge.wedge_a is not None:
                        try:
                            edge.wedge_a.delete()
                        except (AttributeError, AssertionError):
                            pass
                    if edge.vertlist is not None:
                        try:
                            edge.vertlist.delete()
                        except (AttributeError, AssertionError):
                            pass
                    if edge.wedge_b is not None:
                        try:
                            edge.wedge_b.delete()
                        except (AttributeError, AssertionError):
                            pass
            # draw the spots, representing places
            for spot in self.board.spotdict.itervalues():
                newstate = spot.get_state_tup()
                if newstate in self.onscreen:
                    continue
                self.onscreen.discard(spot.oldstate)
                self.onscreen.add(newstate)
                spot.oldstate = newstate
                if spot.visible and spot.img is not None:
                    try:
                        spot.sprite.x = spot.window_left
                        spot.sprite.y = spot.window_bot
                    except AttributeError:
                        spot.sprite = pyglet.sprite.Sprite(
                            spot.img.tex,
                            spot.window_left,
                            spot.window_bot,
                            batch=self.batch,
                            group=self.spotgroup)
                else:
                    if spot.sprite is not None:
                        try:
                            spot.sprite.delete()
                        except (AttributeError, AssertionError):
                            pass
            # draw the pawns, representing things
            for pawn in self.board.pawndict.itervalues():
                newstate = pawn.get_state_tup()
                if newstate in self.onscreen:
                    continue
                self.onscreen.discard(pawn.oldstate)
                self.onscreen.add(newstate)
                pawn.oldstate = newstate
                if pawn.visible:
                    try:
                        pawn.sprite.x = pawn.window_left
                        pawn.sprite.y = pawn.window_bot
                    except AttributeError:
                        pawn.sprite = pyglet.sprite.Sprite(
                            pawn.img.tex,
                            pawn.window_left,
                            pawn.window_bot,
                            batch=self.batch,
                            group=self.pawngroup)
                else:
                    if pawn.sprite is not None:
                        try:
                            pawn.sprite.delete()
                        except (AttributeError, AssertionError):
                            pass

            # draw the menus, really just their backgrounds for the moment
            for menu in self.board.menudict.itervalues():
                for menu_item in menu:
                    newstate = menu_item.get_state_tup()
                    if newstate in self.onscreen:
                        continue
                    self.onscreen.discard(menu_item.oldstate)
                    self.onscreen.add(newstate)
                    menu_item.oldstate = newstate
                    if menu_item.label is not None:
                        try:
                            menu_item.label.delete()
                        except (AttributeError, AssertionError):
                            pass
                    if menu_item.visible:
                        sty = menu.style
                        if menu_item.hovered:
                            color = sty.fg_active.tup
                        else:
                            color = sty.fg_inactive.tup
                        menu_item.label = pyglet.text.Label(
                            menu_item.text,
                            sty.fontface,
                            sty.fontsize,
                            color=color,
                            x=menu_item.window_left,
                            y=menu_item.window_bot,
                            batch=self.batch,
                            group=self.labelgroup)
                newstate = menu.get_state_tup()
                if newstate in self.onscreen:
                    continue
                self.onscreen.discard(menu.oldstate)
                self.onscreen.add(newstate)
                menu.oldstate = newstate
                if menu.sprite is not None:
                    try:
                        menu.sprite.delete()
                    except (AttributeError, AssertionError):
                        pass
                if menu.visible:
                    image = (
                        menu.inactive_pattern.create_image(
                            menu.width,
                            menu.height))
                    menu.sprite = pyglet.sprite.Sprite(
                        image, menu.window_left, menu.window_bot,
                        batch=self.batch, group=self.menugroup)

            # draw the calendar
            newstate = self.calendar.get_state_tup()
            if newstate not in self.onscreen:
                self.onscreen.add(newstate)
                self.onscreen.discard(self.calendar.oldstate)
                self.calendar.oldstate = newstate
                for calcol in self.calcols:
                    if calcol.sprite is not None:
                        try:
                            calcol.sprite.delete()
                        except (AttributeError, AssertionError):
                            pass
                    if calcol.visible:
                        if calcol.width != calcol.old_width:
                            calcol.old_image = calcol.inactive_pattern.create_image(
                                calcol.width, calcol.height)
                            calcol.old_width = calcol.width
                        image = calcol.old_image
                        calcol.sprite = pyglet.sprite.Sprite(
                            image,
                            calcol.window_left,
                            calcol.window_bot,
                            batch=self.batch,
                            group=self.calendargroup)
                    for cel in calcol.celldict.itervalues():
                        if cel.sprite is not None:
                            try:
                                cel.sprite.delete()
                            except (AttributeError, AssertionError):
                                pass
                        if cel.visible:
                            if self.hovered == cel:
                                color = cel.style.fg_active.tup
                                if (
                                        cel.old_active_image is None or
                                        cel.old_width != cel.width or
                                        cel.old_height != cel.height):
                                    cel.old_active_image = cel.active_pattern.create_image(
                                        cel.width, cel.height).texture
                                    cel.old_width = cel.width
                                    cel.old_height = cel.height
                                image = cel.old_active_image
                            else:
                                color = cel.style.fg_inactive.tup
                                if (
                                        cel.old_inactive_image is None or
                                        cel.old_width != cel.width or
                                        cel.old_height != cel.height):
                                    cel.old_inactive_image = cel.inactive_pattern.create_image(
                                        cel.width, cel.height).texture
                                    cel.old_width = cel.width
                                    cel.old_height = cel.height
                                image = cel.old_inactive_image
                            cel.sprite = pyglet.sprite.Sprite(
                                image,
                                cel.window_left,
                                cel.window_bot,
                                batch=self.batch,
                                group=self.cellgroup)
                            y = cel.window_top - cel.label_height
                            if cel.label is None:
                                cel.label = pyglet.text.Label(
                                    cel.text,
                                    cel.style.fontface,
                                    cel.style.fontsize,
                                    width=cel.width,
                                    height=cel.height,
                                    x=cel.window_left,
                                    y=y,
                                    multiline=True,
                                    batch=self.batch,
                                    group=self.labelgroup)
                            else:
                                cel.label.x = cel.window_left
                                cel.label.y = y
            if self.last_age != self.gamestate.age:
                # draw the time line on top of the calendar
                if (
                        self.timeline is not None and
                        self.timeline.domain.allocator.starts):
                    try:
                        self.timeline.delete()
                    except (AttributeError, AssertionError):
                        pass
                top = self.calendar.window_top
                left = self.calendar.window_left
                right = self.calendar.window_right
                rowheight = self.calendar.row_height
                rows = self.calendar.scrolled_to
                age = self.gamestate.age
                y = top - rowheight * (age - rows)
                color = (255, 0, 0)
                if (
                        self.calendar.visible and
                        y > self.calendar.window_bot):
                    self.timeline = self.batch.add(
                        2, pyglet.graphics.GL_LINES, self.topgroup,
                        ('v2i', (left, y, right, y)),
                        ('c3B', color * 2))
                self.last_age = self.gamestate.age
                self.last_timeline_y = y
            # draw any and all hands
            for hand in self.board.hands:
                # No state management yet because the hand itself has
                # no graphics. The cards in it do.
                for card in hand:
                    ctxth = card.textholder
                    redrawn = (card.bgimage is None or
                               ctxth.bgimage is None or
                               card.bgimage.width != card.width or
                               card.bgimage.height != card.height)
                    if redrawn:
                        card.bgimage = (
                            card.pats.bg_inactive.create_image(
                                card.width, card.height))
                        ctxth.bgimage = (
                            card.pats.bg_active.create_image(
                                ctxth.width,
                                ctxth.height))
                        try:
                            card.bgsprite.delete()
                        except (AttributeError, AssertionError):
                            pass
                        try:
                            ctxth.bgsprite.delete()
                        except (AttributeError, AssertionError):
                            pass
                        card.bgsprite = None
                        ctxth.bgsprite = None
                    if card.visible:
                        if card.bgsprite is None:
                            card.bgsprite = pyglet.sprite.Sprite(
                                card.bgimage,
                                card.window_left,
                                card.window_bot,
                                batch=self.batch,
                                group=self.card_bg_group)
                        else:
                            if card.bgsprite.x != card.window_left:
                                card.bgsprite.x = card.window_left
                            if card.bgsprite.y != card.window_bot:
                                card.bgsprite.y = card.window_bot
                            if redrawn:
                                card.bgsprite.image = card.bgimage
                        if ctxth.bgsprite is None:
                            ctxth.bgsprite = pyglet.sprite.Sprite(
                                ctxth.bgimage,
                                ctxth.window_left,
                                ctxth.window_bot,
                                batch=self.batch,
                                group=self.card_text_bg_group)
                        else:
                            if ctxth.bgsprite.x != ctxth.window_left:
                                ctxth.bgsprite.x = ctxth.window_left
                            if ctxth.bgsprite.y != ctxth.window_bot:
                                ctxth.bgsprite.y = ctxth.window_bot
                            if redrawn:
                                ctxth.bgsprite.image = ctxth.bgimage
                        if ctxth.label is None:
                            ctxth.label = pyglet.text.Label(
                                card.text,
                                ctxth.style.fontface,
                                ctxth.style.fontsize,
                                anchor_y='bottom',
                                x=ctxth.text_left,
                                y=ctxth.text_bot,
                                width=ctxth.text_width,
                                height=ctxth.text_height,
                                multiline=True,
                                batch=self.batch,
                                group=self.labelgroup)
                        else:
                            if (
                                    ctxth.label.x !=
                                    ctxth.text_left):
                                ctxth.label.x = (
                                    ctxth.text_left)
                            if (
                                    ctxth.label.y !=
                                    ctxth.text_bot):
                                ctxth.label.y = (
                                    ctxth.text_bot)
                            if (
                                    ctxth.label.width !=
                                    ctxth.text_width):
                                ctxth.label.width = (
                                    ctxth.text_width)
                            if (
                                    ctxth.label.height !=
                                    ctxth.text_height):
                                ctxth.label.height = (
                                    ctxth.text_height)
                        if isinstance(card.img, pyglet.image.AbstractImage):
                            x = card.window_left + card.style.spacing
                            y = ctxth.window_top + card.style.spacing
                            if card.imgsprite is None:
                                card.imgsprite = pyglet.sprite.Sprite(
                                    card.img,
                                    x, y,
                                    batch=self.batch,
                                    group=self.card_img_group)
                            else:
                                if card.imgsprite.x != x:
                                    card.imgsprite.x = x
                                if card.imgsprite.y != y:
                                    card.imgsprite.y = y
                    else: # card not visible
                        for dead in (
                                card.bgsprite,
                                card.imgsprite,
                                ctxth.bgsprite,
                                ctxth.label):
                            if dead is not None:
                                try:
                                    dead.delete()
                                except:
                                    pass
                        card.bgsprite = None
                        card.imgsprite = None
                        ctxth.bgsprite = None
                        ctxth.label = None
                        
            # draw the background image
            if self.drawn_board is None:
                self.drawn_board = pyglet.sprite.Sprite(
                    self.board.wallpaper.tex,
                    self.board.offset_x,
                    self.board.offset_y,
                    batch=self.batch, group=self.boardgroup)
            else:
                if self.drawn_board.x != self.board.offset_x:
                    self.drawn_board.x = self.board.offset_x
                if self.drawn_board.y != self.board.offset_y:
                    self.drawn_board.y = self.board.offset_y
            # well, I lied. I was really only adding those things to the batch.
            # NOW I'll draw them.
            self.batch.draw()
            self.resized = False

        @window.event
        def on_mouse_motion(x, y, dx, dy):
            """Find the widget, if any, that the mouse is over, and highlight
it."""
            self.last_mouse_x = x
            self.last_mouse_y = y
            if self.hovered is None:
                for hand in self.board.hands:
                    if (
                            hand.visible and
                            x > hand.window_left and
                            x < hand.window_right and
                            y > hand.window_bot and
                            y < hand.window_top):
                        for card in hand:
                            if (
                                    x > card.window_left and
                                    x < card.window_right):
                                self.hovered = card
                                card.tweaks += 1
                                return
                for menu in self.board.menus:
                    if (
                            menu.visible and
                            x > menu.window_left and
                            x < menu.window_right and
                            y > menu.window_bot and
                            y < menu.window_top):
                        for item in menu.items:
                            if (
                                    y > item.window_bot and
                                    y < item.window_top):
                                self.hovered = item
                                item.tweaks += 1
                                return
                for spot in self.board.spots:
                    if (
                            spot.visible and
                            x > spot.window_left and
                            x < spot.window_right and
                            y > spot.window_bot and
                            y < spot.window_top):
                        self.hovered = spot
                        spot.tweaks += 1
                        return
                for pawn in self.board.pawns:
                    if (
                            pawn.visible and
                            x > pawn.window_left and
                            x < pawn.window_right and
                            y > pawn.window_bot and
                            y < pawn.window_top):
                        self.hovered = pawn
                        pawn.tweaks += 1
                        return
            else:
                if (
                        x < self.hovered.window_left or
                        x > self.hovered.window_right or
                        y < self.hovered.window_bot or
                        y > self.hovered.window_top):
                    self.hovered.tweaks += 1
                    self.hovered = None

        @window.event
        def on_mouse_press(x, y, button, modifiers):
            """If there's something already highlit, and the mouse is
still over it when pressed, it's been half-way clicked; remember this."""
            if self.placing or self.thinging or self.hovered is None:
                return
            else:
                self.pressed = self.hovered

        @window.event
        def on_mouse_release(x, y, button, modifiers):
            """If something was being dragged, drop it. If something was being
pressed but not dragged, it's been clicked. Otherwise do nothing."""
            if self.placing:
                placed = self.db.make_generic_place(str(self.board))
                self.db.make_spot(str(self.board), str(placed), x, y)
                self.window.set_mouse_cursor()
                self.placing = False
            elif self.thinging:
                thung = self.db.make_generic_thing(str(self.board))
                self.db.make_pawn(str(self.board), str(thung))
                self.thinging = False
            elif self.portaling:
                dimn = str(self.board.dimension)
                if self.portal_from is None:
                    if hasattr(self.pressed, 'place'):
                        self.portal_from = self.pressed
                        logger.debug("Making a portal from %s...", str(self.portal_from.place))
                    else:
                        self.portaling = False
                        self.portal_from = None
                        try:
                            self.edge_from_portal_from.delete()
                        except AttributeError:
                            pass
                        try:
                            self.left_tail_edge_from_portal_from.delete()
                        except AttributeError:
                            pass
                        try:
                            self.right_tail_edge_from_portal_from.delete()
                        except AttributeError:
                            pass
                else:
                    if (
                            hasattr(self.pressed, 'place') and
                            hasattr(self.portal_from, 'place') and
                            self.pressed.place != self.portal_from.place):
                        logger.debug("...to %s", str(self.pressed.place))
                        port = self.db.make_portal(
                            str(self.board),
                            str(self.portal_from.place),
                            str(self.pressed.place))
                        edge = Edge(self.board.db, self.board.dimension, port)
                        edge.unravel()
                    self.portaling = False
                    self.portal_from = None
                    try:
                        self.edge_from_portal_from.delete()
                    except AttributeError:
                        pass
                    try:
                        self.left_tail_edge_from_portal_from.delete()
                    except AttributeError:
                        pass
                    try:
                        self.right_tail_edge_from_portal_from.delete()
                    except AttributeError:
                        pass
            elif self.grabbed is None:
                pass
            else:
                if hasattr(self.grabbed, 'dropped'):
                    self.grabbed.dropped(x, y, button, modifiers)
                self.grabbed = None
            if self.pressed is not None:
                if (
                        hasattr(self.pressed, 'onclick') and
                        x > self.pressed.window_left and
                        x < self.pressed.window_right and
                        y > self.pressed.window_bot and
                        y < self.pressed.window_top):
                    self.pressed.onclick()
                self.pressed = None

        @window.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            """If the thing previously pressed has a
move_with_mouse method, use it.

            """
            if self.grabbed is None:
                if (
                        self.pressed is not None and
                        x > self.pressed.window_left and
                        x < self.pressed.window_right and
                        y > self.pressed.window_bot and
                        y < self.pressed.window_top and
                        hasattr(self.pressed, 'move_with_mouse')):
                    self.grabbed = self.pressed
                else:
                    if self.board.view_left - dx < 0 or (
                            (self.board.view_left - dx)
                            + self.window.width > self.board.width):
                        effective_dx = 0
                    else:
                        effective_dx = dx
                    if self.board.view_bot - dy < 0 or (
                            (self.board.view_bot - dy)
                            + self.window.height > self.board.height):
                        effective_dy = 0
                    else:
                        effective_dy = dy
                    self.board.view_left -= effective_dx
                    self.board.view_bot -= effective_dy
                    if self.pressed is not None:
                        self.pressed = None
                    self.grabbed = None
            else:
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

    def connect_arrow(self, ox, oy, dx, dy, center_shrink=0,
                      old_vertlist_left=None,
                      old_vertlist_center=None,
                      old_vertlist_right=None):
        # xs and ys should be integers.
        #
        # results will be called l, c, r for left tail, center, right tail
        if old_vertlist_center is None:
            c = self.batch.add(
                2, pyglet.graphics.GL_LINES,
                self.edgegroup, ('v2i', (ox, oy, dx, dy)))
        else:
            c = old_vertlist_center
            c.vertices = [ox, oy, dx, dy]
        if dy < oy:
            yco = -1
        else:
            yco = 1
        if dx < ox:
            xco = -1
        else:
            xco = 1
        leftx = float(ox * xco)
        rightx = float(dx * xco)
        boty = float(oy * yco)
        topy = float(dy * yco)
        taillen = float(self.arrowhead_size)
        rise = topy - boty
        run = rightx - leftx
        length = math.sqrt(rise**2 + run**2) - center_shrink
        try:
            slope_theta = math.atan(rise/run)
            opp_theta = math.atan(run/rise)
            if center_shrink != 0:
                rightx = leftx + math.cos(slope_theta) * length
                topy = boty + math.sin(slope_theta) * length
                rise = topy - boty
                run = rightx - leftx
            if rise > run:
                top_theta = slope_theta - fortyfive
                bot_theta = math.pi - opp_theta - fortyfive
            else:
                bot_theta = slope_theta - fortyfive
                top_theta = math.pi - opp_theta - fortyfive
            xoff1 = math.cos(top_theta) * taillen
            yoff1 = math.sin(top_theta) * taillen
            xoff2 = math.cos(bot_theta) * taillen
            yoff2 = math.sin(bot_theta) * taillen
        except ZeroDivisionError:
            if ox == dx:
                topy = boty + length
                yoff1 = self.squareoff
                xoff1 = yoff1
                xoff2 = -1 * xoff1
                yoff2 = yoff1
            else:
                rightx = leftx + length
                xoff1 = self.squareoff
                yoff1 = xoff1
                xoff2 = xoff1
                yoff2 = -1 * yoff1
        x1 = int(rightx - xoff1) * xco
        x2 = int(rightx - xoff2) * xco
        y1 = int(topy - yoff1) * yco
        y2 = int(topy - yoff2) * yco
        endx = int(rightx) * xco
        endy = int(topy) * yco
        if old_vertlist_left is None:
            l = self.batch.add(
                2, pyglet.graphics.GL_LINES,
                self.edgegroup, ('v2i', (x1, y1, endx, endy)))
        else:
            l = old_vertlist_left
            vertices = [x1, y1, endx, endy]
            if l.vertices != vertices:
                l.vertices = vertices
        if old_vertlist_right is None:
            r = self.batch.add(
                2, pyglet.graphics.GL_LINES,
                self.edgegroup, ('v2i', (x2, y2, endx, endy)))
        else:
            r = old_vertlist_right
            vertices = [x2, y2, endx, endy]
            if r.vertices != vertices:
                r.vertices = vertices
        return (l, c, r)
