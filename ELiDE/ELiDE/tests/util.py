from blinker import Signal
from kivy.input.motionevent import MotionEvent
from kivy.base import EventLoop


def all_spots_placed(board, char):
    for place in char.place:
        if place not in board.spot:
            return False
    return True


def all_pawns_placed(board, char):
    for thing in char.thing:
        if thing not in board.pawn:
            return False
    return True


def all_arrows_placed(board, char):
    for orig, dests in char.portal.items():
        if orig not in board.arrow:
            return False
        arrows = board.arrow[orig]
        for dest in dests:
            if dest not in arrows:
                return False
    return True


def idle_until(condition, timeout=None, msg="Timed out"):
    if timeout is None:
        while not condition():
            EventLoop.idle()
        return
    for _ in range(timeout):
        if condition():
            return
        EventLoop.idle()
    raise TimeoutError(msg)


def window_with_widget(wid):
    EventLoop.ensure_window()
    win = EventLoop.window
    win.add_widget(wid)
    return win


class MockTouch(MotionEvent):
    def depack(self, args):
        self.is_touch = True
        self.sx = args['sx']
        self.sy = args['sy']
        super().depack(args)


class ListenableDict(dict, Signal):
    def __init__(self):
        Signal.__init__(self)


class MockTime(Signal):
    pass


class MockEngine(Signal):
    eternal = ListenableDict()
    universal = ListenableDict()
    character = ListenableDict()
    time = MockTime()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.turn = 0
        self._ready = True

    def __setattr__(self, key, value):
        if not hasattr(self, '_ready'):
            super().__setattr__(key, value)
            return
        self.send(self, key=key, value=value)
        super().__setattr__(key, value)

    def next_turn(self, *args, **kwargs):
        self.turn += 1
        kwargs['cb']('next_turn', 'master', self.turn, 0, ([], {}))

    def handle(self, *args, **kwargs):
        return {'a': 'b'}