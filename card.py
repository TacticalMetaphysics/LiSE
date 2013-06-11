import pyglet
import rumor
from util import SaveableMetaclass, stringlike

"""Rectangle shaped widget with picture on top and words on bottom."""


class Card:
    __metaclass__ = SaveableMetaclass
    tables = [
        (
            "card",
            {
                "name": "text not null",
                "display_name": "text not null",
                "image": "text",
                "text": "text",
                "style": "text"},
            ("name",),
            {
                "image": ("img", "name"),
                "style": ("style", "name")},
            []
            )
    ]

    def __init__(self, db, name, display_name, image, text, style):
        self.db = db
        self.name = name
        self._display_name = display_name
        self.img = image
        self._text = text
        self.style = style

    def unravel(self):
        if stringlike(self.img):
            self.img = self.db.imgdict[self.img]
        if self._text[0] == "@":
            self.text = self.db.get_text(self._text[1:])
        else:
            self.text = self._text
        if self._display_name[0] == "@":
            self.display_name = self.db.get_text(self._display_name[1:])
        else:
            self.display_name = self._display_name
        if stringlike(self.style):
            self.style = self.db.get_style(self.style)

    def get_tabdict(self):
        if self.img is None:
            imgn = None
        else:
            imgn = str(self.img)
        stylen = str(self.style)
        return {
            "card": {
                "name": self.name,
                "display_name": self._display_name,
                "img": imgn,
                "text": self._text,
                "style": stylen}
        }

    def get_widget(self, x, y):
        r = CardWidget(self.db, self.name, x, y)
        r.unravel()
        return r


class CardWidget:
    def __init__(self, base, x, y):
        self.base = base
        self.x = x
        self.y = y
        self.db = self.base.db
        self.grabpoint = None
        self.visible = True
        self.interactive = True
        self.hovered = False
        self.tweaks = 0

    def __getattr__(self, attrn):
        if attrn == 'img':
            return self.base.img
        elif attrn == 'display_name':
            return self.base.display_name
        elif attrn == 'name':
            return self.base.name
        elif attrn == 'text':
            return self.base.text
        elif attrn == 'style':
            return self.base.style
        elif attrn == 'width':
            if self.img is None:
                # Just a default width for now
                return 128
            else:
                # The width of the image plus some gutterspace on each side
                return self.img.width + self.style.spacing * 2
        elif attrn == 'height':
            # The height of the text should be the same as that of the
            # image. There should be a gutter between the two, as well
            # as at the top and the bottom. The top gutter is tall
            # enough for a regular gutter and also a single line of
            # text.
            if self.img is None:
                return 256
            else:
                return (
                    self.img.width * 2 +
                    self.style.spacing * 3 +
                    self.style.fontsize)
        elif attrn == 'window_left':
            return self.x
        elif attrn == 'window_right':
            return self.x + self.width
        elif atttrn == 'window_bot':
            return self.y
        elif attrn == 'window_top':
            return self.y + self.height
        else:
            raise AttributeError(
                "Card has no such attribute: {0}".format(atttrn))

    def __hash__(self):
        return hash(self.get_state_tup())

    def unravel(self):
        if self.base is None:
            self.base = self.db.get_card(self.name)
        self.base.unravel()

    def save(self):
        self.base.save()

    def toggle_visibility(self):
        self.visible = not self.visible
        self.tweaks += 1

    def hide(self):
        if self.visible:
            self.toggle_visibility()

    def show(self):
        if not self.visible:
            self.toggle_visibility()

    def move_with_mouse(self, x, y, dx, dy, buttons, modifiers):
        if self.grabpoint is None:
            self.grabpoint = (x - self.x, y - self.y)
        (grabx, graby) = self.grabpoint
        self.x = x - grabx + dx
        self.y = y - graby + dy

    def dropped(self, x, y, button, modifiers):
        self.grabpoint = None

    def get_state_tup(self):
        return (
            self.name,
            self.display_name,
            self.text,
            self.img,
            self.visible,
            self.interactive,
            self.hovered,
            self.tweaks)


class HandIterator:
    def __init__(self, hand):
        self.i = 0
        self.hand = hand

    def next(self):
        try:
            r = self.hand[self.i]
        except IndexError:
            raise StopIteration
        self.i += 1
        return r


class Hand:
    __metaclass__ = SaveableMetaclass
    tables = [
        (
            "hand_card",
            {
                "hand": "text not null",
                "idx": "integer not null",
                "card": "text not null"},
            ("hand", "idx"),
            {"card": ("card", "name")},
            ("idx>=0",)
        ),
    ]
    def __init__(self, db, board, visible, interactive, style, left, right, bot, top):
        self.db = db
        self.board = board
        self._visible = visible
        self._interactive = interactive
        self.style = style
        self._left = left
        self._right = right
        self._bot = bot
        self._top = top
        self.carddict = None
        self.oldstate = None

    def __hash__(self):
        return hash(self.get_state_tup())

    def __iter__(self):
        return HandIterator(self)

    def __getattr__(self, attrn):
        if attrn == "visible":
            return self._visible and hasattr(self.board, 'gw')
        elif attrn == "interactive":
            return self._interactive
        elif attrn == "window":
            # may raise AttributeError if the board has been loaded
            # but not yet assigned to any game window
            return self.board.gw.window
        elif attrn == "window_left":
            try:
                return int(self._left * self.window.width)
            except AttributeError:
                return 0
        elif attrn == "window_right":
            try:
                return int(self._right * self.window.width)
            except AttributeError:
                return 0
        elif attrn == "window_bot":
            try:
                return int(self._bot * self.window.height)
            except AttributeError:
                return 0
        elif attrn == "window_top":
            try:
                return int(self._top * self.window.height)
            except AttributeError:
                return 0
        else:
            raise AttributeError(
                "Hand has no attribute named {0}".format(attrn))

    def __getitem__(self, key):
        if isinstance(key, int):
            i = self._translate_index(key)
            return self.cards[i]
        else:
            return self.carddict[key]

    def __len__(self):
        return len(self.carddict)

    def _translate_index(self, idx):
        if idx > 0 and idx < len(self):
            return idx
        elif idx >= len(self):
            raise IndexError(
                "Index {0} in Hand {1} out of range.".format(
                    idx, self.name))
        while idx < 0:
            idx += len(self)
        return idx

    def get_state_tup(self):
        card_hashes = [hash(card) for card in iter(self)]
        return (
            self._visible,
            self._interactive,
            self._left,
            self._right,
            self._bot,
            self._top,
            hash(tuple(card_hashes)))

    def unravel(self):
        if stringlike(self.board):
            self.board = self.db.boarddict[self.board]
        self.carddict = db.handcarddict[self.name]

    def append(self, card):
        idx = len(self)
        self.carddict[idx] = card
        card.idx = idx

    def insert(self, i, card):
        for j in xrange(i, len(self)-1):
            self.carddict[j+1] = self.carddict[j]
        self.carddict[i] = card

    def remove(self, card):
        i = card.idx
        del self.carddict[i]
        for j in xrange(i+1, len(self)-1):
            self.carddict[j-1] = self.carddict[j]

    def index(self, card):
        return card.idx

    def pop(self, i=-1):
        r = self[i]
        self.remove(r)
        return r

    def adjust(self):
        if len(self) == 0:
            return
        windobot = self.window_bot + self.style.spacing
        prev_right = self.window_left
        for card in iter(self):
            card.x = prev_right + self.style.spacing
            prev_right = card.x + card.width
            card.y = windobot

    def unravel(self):
        for card in self.carddict.itervalues():
            card.unravel()


cards_qryfmt = (
    """SELECT {0} FROM card WHERE name IN ({1})""".format(
        ", ".join(Card.colns), "{0}"))

def read_cards(db, names):
    qryfmt = cards_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, tuple(names))
    r = {}
    for row in db.c:
        rowdict = dictify_row(row, Card.colns)
        rowdict["db"] = db
        r[rowdict["name"]] = Card(**rowdict)
    return r


def load_cards(db, names):
    r = read_cards(db, names)
    for card in r.itervalues():
        card.unravel()
    return r
