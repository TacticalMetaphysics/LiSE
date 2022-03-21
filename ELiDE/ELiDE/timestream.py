from collections import defaultdict
from threading import Thread

from ELiDE.util import trigger

from kivy.app import App
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty
from kivy.graphics import Color, Line
from kivy.uix.recycleview import RecycleView
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget


class ThornyRectangle(Label):
    left_margin = NumericProperty(10)
    right_margin = NumericProperty(10)
    top_margin = NumericProperty(10)
    bottom_margin = NumericProperty(10)

    draw_left = BooleanProperty(True)
    draw_right = BooleanProperty(True)
    draw_up = BooleanProperty(True)
    draw_down = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            pos=self._trigger_redraw,
            size=self._trigger_redraw,
            left_margin=self._trigger_redraw,
            right_margin=self._trigger_redraw,
            top_margin=self._trigger_redraw,
            bottom_margin=self._trigger_redraw,
            draw_left=self._trigger_redraw,
            draw_right=self._trigger_redraw,
            draw_up=self._trigger_redraw,
            draw_down=self._trigger_redraw,
        )
        self._trigger_redraw()

    def collide_point(self, x, y):
        return (
            self.x + self.left_margin < x < self.right - self.right_margin and
            self.y + self.bottom_margin < y < self.top - self.top_margin
        )

    def _redraw_line(self, enabled, name, point_lambda):
        if enabled:
            points = point_lambda()
            if hasattr(self, name):
                the_line = getattr(self, name)
                the_line.points = points
            else:
                the_line = Line(points=points)
            if the_line not in self.canvas.children:
                self.canvas.add(the_line)
        elif hasattr(self, name):
            self.canvas.remove(getattr(self, name))
            delattr(self, name)

    def _get_left_line_points(self):
        return [
            self.x, self.center_y,
            self.x + self.left_margin, self.center_y
        ]

    def _get_right_line_points(self):
        return [
            self.right - self.right_margin, self.center_y,
            self.right, self.center_y
        ]

    def _get_top_line_points(self):
        return [
            self.center_x, self.top,
            self.center_x, self.top - self.top_margin
        ]

    def _get_bottom_line_points(self):
        return [
            self.center_x, self.y,
            self.center_x, self.y + self.bottom_margin
        ]

    def _redraw(self, *args):
        self._color = Color(rgba=[1, 1, 1, 1])
        if self._color not in self.canvas.children:
            self.canvas.add(self._color)
        rectpoints = [
            self.x + self.left_margin, self.y + self.bottom_margin,
            self.right - self.right_margin, self.y + self.bottom_margin,
            self.right - self.right_margin, self.top - self.top_margin,
            self.x + self.left_margin, self.top - self.top_margin,
            self.x + self.left_margin, self.y + self.bottom_margin
        ]
        if hasattr(self, '_rect'):
            self._rect.points = rectpoints
        else:
            self._rect = Line(points=rectpoints)
            self.canvas.add(self._rect)
        self._redraw_line(self.draw_left, '_left_line',
                          self._get_left_line_points)
        self._redraw_line(self.draw_right, '_right_line',
                          self._get_right_line_points)
        self._redraw_line(self.draw_up, '_top_line',
                          self._get_top_line_points)
        self._redraw_line(self.draw_down, '_bot_line',
                          self._get_bottom_line_points)
        self.canvas.ask_update()

    _trigger_redraw = trigger(_redraw)


class Cross(Widget):
    draw_left = BooleanProperty(True)
    draw_right = BooleanProperty(True)
    draw_up = BooleanProperty(True)
    draw_down = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            draw_left=self._trigger_redraw,
            draw_right=self._trigger_redraw,
            draw_up=self._trigger_redraw,
            draw_down=self._trigger_redraw,
            size=self._trigger_redraw,
            pos=self._trigger_redraw
        )

    def _draw_line(self, enabled, name, get_points):
        if enabled:
            points = get_points()
            if hasattr(self, name):
                getattr(self, name).points = points
            else:
                the_line = Line(points=points)
                setattr(self, name, the_line)
                self.canvas.add(the_line)
        elif hasattr(self, name):
            the_line = getattr(self, name)
            if the_line in self.canvas.children:
                self.canvas.remove(the_line)
            delattr(self, name)

    def _get_left_points(self):
        return [
            self.x, self.center_y,
            self.center_x, self.center_y
        ]

    def _get_right_points(self):
        return [
            self.center_x, self.center_y,
            self.right, self.center_y
        ]

    def _get_up_points(self):
        return [
            self.center_x, self.center_y,
            self.center_x, self.top
        ]

    def _get_down_points(self):
        return [
            self.center_x, self.center_y,
            self.center_x, self.y
        ]

    def _redraw(self, *args):
        self._draw_line(self.draw_left, '_left_line', self._get_left_points)
        self._draw_line(self.draw_right, '_right_line', self._get_right_points)
        self._draw_line(self.draw_up, '_up_line', self._get_up_points)
        self._draw_line(self.draw_down, '_down_line', self._get_down_points)
        self.canvas.ask_update()

    _trigger_redraw = trigger(_redraw)


class Timestream(RecycleView):
    cols = NumericProperty(1)  # should be equal to the number of turns on which branches were created + 1


class TimestreamScreen(Screen):
    toggle = ObjectProperty()
    timestream = ObjectProperty()

    def on_pre_enter(self, *args):
        self.timestream.disabled = True
        self._thread = Thread(target=self._get_branch_lineage)
        self._thread.start()

    def _get_branch_lineage(self, *args):
        Logger.debug("Timestream: getting branch lineage")
        engine = App.get_running_app().engine
        branch_lineage = engine.handle('branch_lineage')
        start_turn_branches = defaultdict(set)
        branch_split_turns_todo = defaultdict(set)
        branch_split_turns_done = defaultdict(set)
        for branch, (parent, parent_turn, parent_tick,
                     end_turn, end_tick) in branch_lineage.items():
            start_turn_branches[parent_turn].add(branch)
            branch_split_turns_todo[parent].add(parent_turn)
        branch_split_turns_todo['trunk'].add(0)
        col2turn = list(sorted(start_turn_branches.keys()))
        data = []
        if not col2turn:
            self.timestream.cols = 1
            self.timestream.data = []
            self.timestream.disabled = False
            return
        Logger.debug("Timestream: read branch lineage, processing...")
        trunk_lineage = branch_lineage.pop('trunk')
        sorted_branches = ['trunk'] + sorted(branch_lineage)
        branch_lineage['trunk'] = trunk_lineage
        for row, branch in enumerate(sorted_branches):
            for turn in col2turn:
                if branch == 'trunk' and turn == 0:
                    data.append({
                        'widget': 'ThornyRectangle',
                        'text': 'NEW',
                        'draw_left': False,
                        'draw_up': False,
                        'draw_down': len(start_turn_branches[turn]) > 1,
                        'draw_right': bool(branch_split_turns_todo[branch])
                    })
                elif branch in start_turn_branches[turn]:
                    data.append({
                        'widget': 'ThornyRectangle',
                        'text': f'{branch}\n{turn}',
                        'draw_left': turn > branch_lineage[branch][1],
                        'draw_up': turn == branch_lineage[branch][1],
                        'draw_down': len(start_turn_branches[turn]) > 1,
                        'draw_right': bool(branch_split_turns_todo[branch])
                    })
                elif start_turn_branches[turn]:
                    data.append({
                        'widget': 'Cross',
                        'draw_left': turn > branch_lineage[branch][1],
                        'draw_up': row > 0,
                        'draw_down': bool(start_turn_branches[turn]),
                        'draw_right': turn < col2turn[-1]
                    })
                else:
                    data.append({'widget': 'Widget'})
                start_turn_branches[turn].discard(branch)
                branch_split_turns_todo[branch].discard(turn)
                branch_split_turns_done[branch].add(turn)
            Logger.debug(f"Timestream: processed branch {branch}")
        self.timestream.cols = len(col2turn)
        self.timestream.data = data
        Logger.debug("Timestream: loaded!")
        self.timestream.disabled = False


Builder.load_string("""
<Timestream>:
    key_viewclass: 'widget'
    effect_cls: 'ScrollEffect'
    RecycleGridLayout:
        cols: root.cols
        default_width: 100
        default_height: 100
        default_size_hint: None, None
        height: self.minimum_height
        width: self.minimum_width
        size_hint: None, None
<TimestreamScreen>:
    name: 'timestream'
    timestream: timestream
    BoxLayout:
        orientation: 'vertical'
        Timestream:
            id: timestream
            size_hint_y: 0.95
        BoxLayout:
            size_hint_y: 0.05
            Button:
                text: 'Cancel'
                on_press: root.toggle()
""")

if __name__ == '__main__':
    from kivy.base import runTouchApp
    from kivy.core.window import Window
    from kivy.modules import inspector
    from kivy.uix.boxlayout import BoxLayout

    ts = Timestream()
    layout = BoxLayout()
    layout.add_widget(ts)
    ts.data = [{'text': str(i), 'widget': 'ThornyRectangle' if i % 7 != 0 else 'Cross'} for i in range(500)]
    inspector.create_inspector(Window, layout)
    runTouchApp(layout)