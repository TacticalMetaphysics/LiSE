from menu import Menu, MenuItem
from style import Color, Style
from dimension import Dimension
from item import Item, Thing, Place, Portal
from img import Img
from pawn import Pawn
from spot import Spot
from board import Board
from effect import Effect, EffectDeck
from database import Database
import parms

EMPTY_DB_FILE = 'empty.sqlite'

TARGET_DB_FILE = 'default.sqlite'

infile = open(EMPTY_DB_FILE, 'rb')
outfile = open(TARGET_DB_FILE, 'wb')

outfile.write(infile.read())

infile.close()
outfile.close()


def populate_menus(db, menus, menu_items):
    menutd = {"menu": menus}
    mitd = {"menu_item": menu_items}
    Menu.dbop['insert'](db, menutd)
    MenuItem.dbop['insert'](db, mitd)


def populate_styles(db, colors, styles):
    colortd = {"color": colors}
    styletd = {"style": styles}
    Color.dbop['insert'](db, colortd)
    Style.dbop['insert'](db, styletd)


def populate_items(db, things, places, portals):
    combined = things + places + portals
    dimensions = []
    for row in combined:
        dim = {'name': row['dimension']}
        if dim not in dimensions:
            dimensions.append(dim)
    items = []
    for row in combined:
        it = {'dimension': row['dimension'], 'name': row['name']}
        if it not in items:
            items.append(it)
    dimension_td = {'dimension': dimensions}
    item_td = {'item': items}
    thing_td = {'thing': things}
    place_td = {'place': places}
    portal_td = {'portal': portals}
    Dimension.dbop['insert'](db, dimension_td)
    Item.dbop['insert'](db, item_td)
    Thing.dbop['insert'](db, thing_td)
    Place.dbop['insert'](db, place_td)
    Portal.dbop['insert'](db, portal_td)


def populate_effects(db, effects, decks):
    eftd = {"effect": effects}
    decktd = {"effect_deck_link": decks}
    Effect.dbop['insert'](db, eftd)
    EffectDeck.dbop['insert'](db, decktd)


def populate_gfx(db, imgs, pawns, spots, boards):
    img_td = {'img': imgs}
    pawn_td = {'pawn': pawns}
    spot_td = {'spot': spots}
    board_td = {'board': boards}
    Img.dbop['insert'](db, img_td)
    Pawn.dbop['insert'](db, pawn_td)
    Spot.dbop['insert'](db, spot_td)
    Board.dbop['insert'](db, board_td)


def boardmenu(db, board_menu_pairs):
    qryfmt = "INSERT INTO board_menu VALUES {0}"
    qms = ["(?, ?)"] * len(board_menu_pairs)
    qrystr = qryfmt.format(", ".join(qms))
    qrylst = []
    for pair in board_menu_pairs:
        qrylst.extend(pair)
    db.c.execute(qrystr, qrylst)


def populate_database(db, data):
    populate_menus(db, data.menus, data.menu_items)
    populate_styles(db, data.colors, data.styles)
    populate_items(db, data.things, data.places, data.portals)
    populate_effects(db, data.effects, data.effect_decks)
    populate_gfx(db, data.imgs, data.pawns, data.spots, data.boards)
    boardmenu(db, data.board_menu)


db = Database(TARGET_DB_FILE)
populate_database(db, parms)
db.__del__()
del db
