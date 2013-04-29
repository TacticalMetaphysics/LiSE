from menu import Menu, MenuItem
from style import Color, Style
from dimension import Dimension
from item import Item, Thing, Place, Portal
from img import Img
from pawn import Pawn
from spot import Spot
from board import Board
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


def populate_gfx(db, imgs, pawns, spots, boards):
    img_td = {'img': imgs}
    pawn_td = {'pawn': pawns}
    spot_td = {'spot': spots}
    board_td = {'board': boards}
    Img.dbop['insert'](db, img_td)
    Pawn.dbop['insert'](db, pawn_td)
    Spot.dbop['insert'](db, spot_td)
    Board.dbop['insert'](db, board_td)


db = Database(TARGET_DB_FILE)


populate_menus(db, parms.menus, parms.menu_items)
populate_styles(db, parms.colors, parms.styles)
populate_items(db, parms.things, parms.places, parms.portals)
populate_gfx(db, parms.imgs, parms.pawns, parms.spots, parms.boards)

db.__del__()
del db
