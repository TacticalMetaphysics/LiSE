import database
import parms
import world
import widgets

tabclasses = [
    world.Dimension,
    world.Schedule,
    world.Item,
    world.Thing,
    world.Place,
    world.Portal,
    world.Journey,
    world.Effect,
    world.EffectDeck,
    world.Event,
    widgets.Color,
    widgets.Style,
    widgets.Menu,
    widgets.MenuItem,
    widgets.CalendarCol,
    widgets.Spot,
    widgets.Pawn,
    widgets.Board]

db = database.Database('default.sqlite')

for clas in tabclasses:
    for tab in clas.schemata:
        print tab
        db.c.execute(tab)

del db
