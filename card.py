import pyglet
import rumor
from util import SaveableMetaclass, stringlike, dictify_row

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
        self.db.carddict[self.name] = self

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


class TextHolder:
    def __init__(self, cardwidget):
        self.cardwidget = cardwidget
        self.bgimage = None
        self.bgsprite = None
        self.label = None

    def __getattr__(self, attrn):
        if attrn == "width":
            return self.cardwidget.width - 2 * self.cardwidget.style.spacing
        elif attrn == "height":
            if isinstance(self.cardwidget.base.img, pyglet.image.AbstractImage):
                return self.cardwidget.height / 2 - 2 * self.cardwidget.style.spacing
            else:
                return self.cardwidget.height - 2 * self.cardwidget.style.spacing
        elif attrn == "window_left":
            return self.cardwidget.x + self.cardwidget.style.spacing
        elif attrn == "window_right":
            return self.window_left + self.width
        elif attrn == "window_bot":
            return self.cardwidget.window_bot + self.cardwidget.style.spacing
        elif attrn == "window_top":
            return self.window_bot + self.height
        else:
            return getattr(self.cardwidget, attrn)


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
        self.pats = PatternHolder(self.base.style)
        self.bgimage = None
        self.bgsprite = None
        self.textholder = TextHolder(self)
        self.imgsprite = None

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
            return getattr(self.base, attrn)

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

    def __iter__(self):
        return self

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
        (
            "hand_board",
            {
                "hand": "text not null",
                "board": "text not null",
                "visible": "boolean default 1",
                "interactive": "boolean default 1",
                "style": "text not null default 'SmallLight'",
                "left": "float default 0.3",
                "right": "float default 0.6",
                "bot": "float default 0.0",
                "top": "float default 0.3"},
            ("hand", "board"),
            {
                "hand": ("hand_card", "hand"),
                "board": ("board", "dimension"),
                "style": ("style", "name")},
            ("left>=0.0", "left<=1.0", "right>=0.0", "right<=1.0",
             "bot>=0.0", "bot<=1.0", "top>=0.0", "top<=1.0",
             "right>left", "top>bot")
        )
    ]
    def __init__(self, db, name, board, visible, interactive, style, left, right, bot, top):
        self.db = db
        self.name = name
        self.board = board
        self._visible = visible
        self._interactive = interactive
        self.style = style
        self._left = left
        self._right = right
        self._bot = bot
        self._top = top
        self.db.handdict[self.name] = self
        self.carddict = None
        self.oldstate = None
        self.pats = PatternHolder(self.style)

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
        if self.carddict is None:
            return -1
        else:
            return len(self.carddict)

    def __str__(self):
        return self.name

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
        cardbits = []
        for card in self.cards:
            cardbits.extend(iter(card.get_state_tup()))
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
        if str(self) not in self.db.handcarddict:
            self.db.handcarddict[str(self)] = {}
        self.carddict = db.handcarddict[str(self)]

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
        if self.carddict is None:
            if 
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

hand_card_qryfmt = (
    """SELECT {0} FROM hand_card JOIN card WHERE hand IN ({1})""".format(
        "hand, idx, card, " + ", ".join(Card.valns), "{0}"))

hand_card_colns = ["hand", "idx", "card"] + Card.valns

def read_cards_in_hands(db, handnames):
    qryfmt = hand_card_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(handnames)))
    db.c.execute(qrystr, tuple(handnames))
    r = {}
    cards = set()
    for handname in handnames:
        r[handname] = []
    for row in db.c:
        rowdict = dictify_row(row, hand_card_colns)
        rowdict["db"] = db
        handn = rowdict["hand"]
        cardn = rowdict["card"]
        idx = rowdict["idx"]
        while len(r[handn]) <= idx:
            r[handn].append(None)
        r[handn][idx] = cardn
        cards.add(cardn)
    read_cards(db, tuple(cards))
    for (handn, cardl) in r.iteritems():
        for i in xrange(0, len(cardl)-1):
            cardl[i] = db.carddict[cardl[i]]
        db.handcarddict[handn] = cardl
    return r

hands_qryfmt = (
    """SELECT {0} FROM hand_board WHERE board IN ({1})""".format(
        ", ".join(Hand.colnames["hand_board"]), "{0}"))

def read_hands_in_boards(db, boardnames):
    qryfmt = hands_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(boardnames)))
    db.c.execute(qrystr, tuple(boardnames))
    r = {}
    handns = set()
    for boardname in boardnames:
        r[boardname] = {}
    for row in db.c:
        rowdict = dictify_row(row, Hand.colnames["hand_board"])
        rowdict["db"] = db
        boardname = rowdict["board"]
        handname = rowdict["hand"]
        handns.add(handname)
        rowdict["name"] = handname
        del rowdict["hand"]
        r[boardname][handname] = Hand(**rowdict)
    read_cards_in_hands(db, tuple(handns))
    return r
