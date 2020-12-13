from kivy.base import EventLoop
from kivy.tests.common import GraphicUnitTest
from kivy.logger import Logger
import networkx as nx

from LiSE.character import Facade
from ELiDE.app import ELiDEApp
from ELiDE.grid.board import GridBoard, GridBoardView
from ELiDE.tests.util import MockTouch


class GridBoardTest(GraphicUnitTest):
    @staticmethod
    def test_layout_grid():
        spots_wide = 3
        spots_tall = 3
        spot_width = 32
        spot_height = 32
        graph = nx.grid_2d_graph(spots_wide, spots_tall)
        char = Facade(graph)
        something = char.place[1, 1].new_thing('something')
        otherthing = char.place[2, 2].new_thing('otherthing')
        assert len(char.thing) == 2
        board = GridBoard(
            character=char
        )
        boardview = GridBoardView(board=board)
        EventLoop.ensure_window()
        win = EventLoop.window
        win.add_widget(boardview)
        def all_spots_placed():
            for x in range(spots_wide):
                for y in range(spots_tall):
                    if (x, y) not in board.spot:
                        return False
            return True
        def all_pawns_placed():
            for thing in char.thing:
                if thing not in board.pawn:
                    return False
            return True
        while not (all_spots_placed() and all_pawns_placed()):
            EventLoop.idle()
        otherthing['location'] = board.pawn['otherthing'].loc_name = (0, 0)
        while board.pawn['otherthing'].parent != board.spot[0, 0]:
            EventLoop.idle()
        for x in range(spots_wide):
            for y in range(spots_tall):
                spot = board.spot[x, y]
                assert spot.x == x * spot_width
                assert spot.y == y * spot_height
        assert board.pawn['something'].parent == board.spot[1, 1]
        assert board.pawn['otherthing'].parent == board.spot[0, 0]
        assert board.pawn['otherthing'].pos == board.spot[0, 0].pos