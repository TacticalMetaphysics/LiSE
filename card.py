import pyglet
from util import SaveableMetaclass, PatternHolder, stringlike, dictify_row, phi
from style import read_styles

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
        self._img = image
        self._text = text
        self._style = style
        self.widget = None
        self.db.carddict[self.name] = self

    def __getattr__(self, attrn):
        if attrn == 'base':
            return self
        elif attrn == 'img':
            if self._img == '':
                return None
            else:
                return self.db.imgdict[self._img]
        elif attrn == 'text':
            if self._text[0] == '@':
                return self.db.get_text(self._text[1:])
            else:
                return self._text
        elif attrn == 'display_name':
            if self._display_name[0] == '@':
                return self.db.get_text(self._display_name[1:])
            else:
                return self._display_name
        elif attrn == 'style':
            return self.db.styledict[self._style]
        elif hasattr(self.widget, attrn):
            return getattr(self.widget, attrn)
        else:
            raise AttributeError("Card has no attribute {0}".format(attrn))

    def __str__(self):
        return self.name

    def unravel(self):
        self.style.unravel()

    def get_tabdict(self):
        stylen = str(self.style)
        return {
            "card": {
                "name": self.name,
                "display_name": self._display_name,
                "img": self._img,
                "text": self._text,
                "style": stylen}
        }

    def mkwidget(self, x, y):
        self.widget = CardWidget(self, x, y)
        self.widget.unravel()


class TextHolder:
    def __init__(self, cardwidget):
        self.cardwidget = cardwidget
        self.bgimage = None
        self.bgsprite = None
        self.label = None

    def __getattr__(self, attrn):
        if attrn == "width":
            return self.cardwidget.width - 4 * self.cardwidget.style.spacing
        elif attrn == "height":
            if isinstance(self.cardwidget.base.img, pyglet.image.AbstractImage):
                return self.cardwidget.height / 2 - 4 * self.cardwidget.style.spacing
            else:
                return self.cardwidget.height - 4 * self.cardwidget.style.spacing
        elif attrn == "window_left":
            return self.cardwidget.x + 2 * self.cardwidget.style.spacing
        elif attrn == "window_right":
            return self.window_left + self.width
        elif attrn == "window_bot":
            return self.cardwidget.window_bot + 2 * self.cardwidget.style.spacing
        elif attrn == "window_top":
            return self.window_bot + self.height
        elif attrn == "text_left":
            return self.window_left + self.cardwidget.style.spacing
        elif attrn == "text_bot":
            return self.window_bot + self.cardwidget.style.spacing
        elif attrn == "text_width":
            return self.width - self.cardwidget.style.spacing
        elif attrn == "text_height":
            return self.height - self.cardwidget.style.spacing
        else:
            return getattr(self.cardwidget, attrn)


class CardWidget:
    def __init__(self, base, x, y):
        self._base = str(base)
        self.x = x
        self.y = y
        self.db = self.base.db
        self.grabpoint = None
        self.oldx = x
        self.oldy = y
        self.visible = True
        self.interactive = True
        self.hovered = False
        self.floating = False
        self.tweaks = 0
        self.pats = PatternHolder(self.base.style)
        self.bgimage = None
        self.bgsprite = None
        self.textholder = TextHolder(self)
        self.imgsprite = None

    def __getattr__(self, attrn):
        if attrn == 'gw':
            return self.hand.gw
        elif attrn == 'base':
            return self.db.get_card(self._base)
        elif attrn == 'hovered':
            return self.gw.hovered is self
        elif attrn == 'pressed':
            return self.gw.pressed is self
        elif attrn == 'grabbed':
            return self.gw.grabbed is self
        elif attrn == 'img':
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
            return int(self.width * phi)
        elif attrn == 'window_left':
            return self.x
        elif attrn == 'window_right':
            return self.x + self.width
        elif attrn == 'window_bot':
            return self.y
        elif attrn == 'window_top':
            return self.y + self.height
        elif attrn == 'widget':
            return self
        elif hasattr(self.base, attrn):
            return getattr(self.base, attrn)
        else:
            raise AttributeError("CardWidget has no attribute {0}".format(attrn))

    def __hash__(self):
        return hash(self.get_state_tup())

    def unravel(self):
        self.base.unravel()
        if self.pats is None:
            self.pats = PatternHolder(self.base.style)

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

    def hovered(self):
        print "card hovered"
        self.hovered = True

    def unhovered(self):
        print "card unhovered"
        self.hovered = False

    def move_with_mouse(self, x, y, dx, dy, buttons, modifiers):
        if self.grabpoint is None:
            self.oldx = x
            self.oldy = y
            self.floating = True
            self.grabpoint = (x - self.x, y - self.y)
            self.hand.adjust()
        (grabx, graby) = self.grabpoint
        self.x = x - grabx + dx
        self.y = y - graby + dy

    def dropped(self, x, y, button, modifiers):
        if (
                x > self.hand.window_left and
                x < self.hand.window_right and
                y > self.hand.window_bot and
                y < self.hand.window_top):
            min_x = self.hand.window_right
            max_x = 0
            for card in self.hand:
                if card.window_left < min_x:
                    min_x = card.window_left
                if card.window_right > max_x:
                    max_x = card.window_right
                if (
                        x > card.window_left and
                        x < card.window_bot):
                    print "Dropped {0} on {1}".format(str(self), str(card))
                    self.hand.discard(self)
                    self.hand.insert(self.hand.index(card), self)
                    break
            # I am either to the left of all cards in hand, or to the right.
            # Which edge am I closer to?
            space_left = x - min_x
            space_right = max_x - x
            if space_left < space_right:
                print "Dropped {0} to the left of the hand".format(str(self))
                self.hand.discard(self)
                self.hand.insert(0, self)
            else:
                print "Dropped {0} to the right of the hand".format(str(self))
                self.hand.discard(self)
                self.hand.append(self)
            
        self.floating = False
        self.grabpoint = None
        self.hand.adjust()

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
            cardn = str(self.hand.db.handcarddict[str(self.hand)][self.i])
            card = self.hand.db.carddict[cardn]
            self.i += 1
            return card
        except IndexError:
            raise StopIteration


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
        self._board = str(board)
        self._visible = visible
        self._interactive = interactive
        self._style = str(style)
        self._left = left
        self._right = right
        self._bot = bot
        self._top = top
        self.db.handdict[self.name] = self
        if str(self.board) not in self.db.boardhanddict:
            self.db.boardhanddict[str(self.board)] = {}
        self.db.boardhanddict[str(self.board)][str(self)] = self
        self.oldstate = None

    def __hash__(self):
        return hash(self.get_state_tup())

    def __iter__(self):
        return HandIterator(self)

    def __getattr__(self, attrn):
        if attrn == "board":
            return self.db.boarddict[self._board]
        elif attrn == "style":
            return self.db.styledict[self._style]
        elif attrn == "gw":
            return self.board.gw
        elif attrn == "hovered":
            return self.gw.hovered is self
        elif attrn == "visible":
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
        elif attrn == 'cards':
            return self.db.handcarddict[str(self)]
        else:
            raise AttributeError(
                "Hand has no attribute named {0}".format(attrn))

    def __getitem__(self, i):
        return self.db.handcarddict[str(self)][i]

    def __len__(self):
        return len(self.db.handcarddict[str(self)])

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
        for card in self:
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
        pass

    def append(self, card):
        card.hand = self
        self.db.handcarddict[str(self)].append(str(card))

    def insert(self, i, card):
        card.hand = self
        self.db.handcarddict[str(self)].insert(i, str(card))

    def remove(self, card):
        self.db.handcarddict[str(self)].remove(str(card))

    def discard(self, card):
        if str(card) in self.db.handcarddict[str(self)]:
            self.remove(card)

    def index(self, card):
        return self.db.handcarddict[str(self)].index(str(card))

    def pop(self, i=-1):
        r = self.db.handcarddict[str(self)].pop(i)
        return r

    def adjust(self):
        if len(self) == 0:
            return
        windobot = self.window_bot + self.style.spacing
        prev_right = self.window_left
        print "Adjusting hand {0} at ({1},{2})".format(str(self), str(prev_right), str(windobot))
        print "Cards in hand:"
        print self.cards
        for card in iter(self):
            print "Adjusting card {0}".format(str(card))
            if card.widget is not None and card.widget.floating:
                print "Skipping adjustment of {0} because it's floating.".format(str(card))
                continue
            card.hand = self
            x = prev_right + self.style.spacing
            print "Moving {0} to ({1},{2})".format(str(card), str(x), str(windobot))
            if card.widget is None:
                card.mkwidget(x, windobot)
            else:
                card.widget.x = x
                card.widget.y = windobot
            prev_right = x + card.widget.width


cards_qryfmt = (
    """SELECT {0} FROM card WHERE name IN ({1})""".format(
        ", ".join(Card.colns), "{0}"))

def read_cards(db, names):
    qryfmt = cards_qryfmt
    qrystr = qryfmt.format(", ".join(["?"] * len(names)))
    db.c.execute(qrystr, tuple(names))
    r = {}
    styles = set()
    for row in db.c:
        rowdict = dictify_row(row, Card.colns)
        rowdict["db"] = db
        r[rowdict["name"]] = Card(**rowdict)
        styles.add(rowdict["style"])
    read_styles(db, tuple(styles))
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
    stylens = set()
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
        stylens.add(rowdict["style"])
        r[boardname][handname] = Hand(**rowdict)
    read_cards_in_hands(db, tuple(handns))
    read_styles(db, stylens)
    return r
