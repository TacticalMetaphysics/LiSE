from kivy.base import EventLoop
from kivy.tests.common import GraphicUnitTest
import networkx as nx

from LiSE.character import Facade
from ELiDE.app import ELiDEApp
from ELiDE.graph.board import GraphBoard, GraphBoardView, FinalLayout
from ELiDE.tests.util import MockTouch


class GraphBoardTest(GraphicUnitTest):
    @staticmethod
    def test_layout_grid():
        spots_wide = 3
        spots_tall = 3
        graph = nx.grid_2d_graph(spots_wide, spots_tall)
        char = Facade(graph)
        app = ELiDEApp()
        spotlayout = FinalLayout()
        arrowlayout = FinalLayout()
        board = GraphBoard(
            app=app,
            character=char,
            spotlayout=spotlayout,
            arrowlayout=arrowlayout
        )
        spotlayout.pos = board.pos
        board.bind(pos=spotlayout.setter('pos'))
        spotlayout.size = board.size
        board.bind(size=spotlayout.setter('size'))
        board.add_widget(spotlayout)
        arrowlayout.pos = board.pos
        board.bind(pos=arrowlayout.setter('pos'))
        arrowlayout.size = board.size
        board.bind(size=arrowlayout.setter('size'))
        board.add_widget(arrowlayout)
        board.update()
        boardview = GraphBoardView(board=board)
        EventLoop.ensure_window()
        win = EventLoop.window
        win.add_widget(boardview)
        def all_spots_placed():
            for x in range(spots_wide):
                for y in range(spots_tall):
                    if (x, y) not in board.spot:
                        return False
            return True
        while not all_spots_placed():
            EventLoop.idle()
        # Don't get too picky about the exact proportions of the grid; just make sure the
        # spots are positioned logically with respect to one another
        for name, spot in board.spot.items():
            x, y = name
            if x > 0:
                assert spot.x > board.spot[x-1, y].x
            if y > 0:
                assert spot.y > board.spot[x, y-1].y
            if x < spots_wide - 1:
                assert spot.x < board.spot[x+1, y].x
            if y < spots_tall - 1:
                assert spot.y < board.spot[x, y+1].y

    @staticmethod
    def test_select_arrow():
        char = Facade()
        char.add_place(0, _x=0.1, _y=0.1)
        char.add_place(1, _x=0.2, _y=0.1)
        char.add_portal(0, 1)
        app = ELiDEApp()
        board = GraphBoard(
            app=app,
            character=char
        )
        boardview = GraphBoardView(board=board)
        EventLoop.ensure_window()
        win = EventLoop.window
        win.add_widget(boardview)
        while 0 not in board.arrow \
                or 1 not in board.arrow[0] \
                or board.arrow[0][1] not in board.arrowlayout.children:
            EventLoop.idle()
        ox, oy = board.spot[0].center
        dx, dy = board.spot[1].center
        motion = MockTouch("unittest", 1, {
            'sx': (ox + ((dx - ox) / 2)) / win.width,
            'sy': dy / win.height})
        EventLoop.post_dispatch_input("begin", motion)
        EventLoop.post_dispatch_input("end", motion)
        assert app.selection == board.arrow[0][1]

    @staticmethod
    def test_select_spot():
        char = Facade()
        char.add_place(0, _x=0.1, _y=0.1)
        app = ELiDEApp()
        board = GraphBoard(
            app=app,
            character=char
        )
        boardview = GraphBoardView(board=board)
        EventLoop.ensure_window()
        win = EventLoop.window
        win.add_widget(boardview)
        while 0 not in board.spot \
                or board.spot[0] not in board.spotlayout.children:
            EventLoop.idle()
        x, y = board.spot[0].center
        motion = MockTouch("unittest", 1, {
            'sx': x / win.width,
            'sy': y / win.height})
        EventLoop.post_dispatch_input("begin", motion)
        EventLoop.post_dispatch_input("end", motion)
        assert app.selection == board.spot[0]

    @staticmethod
    def test_select_pawn():
        char = Facade()
        char.add_place(0, _x=0.1, _y=0.1)
        char.add_thing('that', location=0)
        app = ELiDEApp()
        board = GraphBoard(
            app=app,
            character=char
        )
        boardview = GraphBoardView(board=board)
        EventLoop.ensure_window()
        win = EventLoop.window
        win.add_widget(boardview)
        while 0 not in board.spot \
                or board.spot[0] not in board.spotlayout.children \
                or board.pawn['that'] not in board.spot[0].children:
            EventLoop.idle()
        x, y = board.pawn['that'].center
        motion = MockTouch("unittest", 1, {
            'sx': x / win.width,
            'sy': y / win.height})
        EventLoop.post_dispatch_input("begin", motion)
        EventLoop.post_dispatch_input("end", motion)
        assert app.selection == board.pawn['that']

    @staticmethod
    def test_pawn_relocate():
        char = Facade()
        char.add_place(0, _x=0.1, _y=0.1)
        char.add_place(1, _x=0.2, _y=0.1)
        char.add_thing('that', location=0)
        app = ELiDEApp()
        board = GraphBoard(
            app=app,
            character=char
        )
        boardview = GraphBoardView(board=board)
        EventLoop.ensure_window()
        win = EventLoop.window
        win.add_widget(boardview)
        while 0 not in board.spot \
                or board.spot[0] not in board.spotlayout.children \
                or 1 not in board.spot \
                or board.spot[1] not in board.spotlayout.children \
                or 'that' not in board.pawn \
                or board.pawn['that'] not in board.spot[0].children:
            EventLoop.idle()
        that = board.pawn['that']
        one = board.spot[1]
        # In a real ELiDE session, the following would happen as a
        # result of a Board.update() call
        char.thing['that']['location'] = that.loc_name = 1
        for ticked in range(1000):
            EventLoop.idle()
            if that in one.children:
                return
        else:
            assert False, "pawn did not relocate within 1000 ticks"
