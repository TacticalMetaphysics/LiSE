class Character:
    """An incorporeal object connecting corporeal ones together across
dimensions, indicating that they represent one thing and have that
thing's attributes.

Every item in LiSE's world model must be part of a Character, though
it may be the only member of that Character. Where items can only have
generic attributes appropriate to the dimension they occupy,
Characters have all the attributes of the items that make them up, and
possibly many more. There are no particular restrictions on what
manner of attribute a Character can have, so long as it is not used by
the physics of any dimension.

Characters may contain EventDecks. These may represent skills the
character has, in which case every EventCard in the EventDeck
represents something can happen upon using the skill, regardless of
what it's used on or where. "Success" and "failure" are appropriate
EventCards in this case, though there may be finer distinctions to be
made between various kinds of success and failure with a given skill.

However, the EventCards that go in a Character's EventDeck to
represent a skill should never represent anything particular to any
use-case of the skill. Those EventCards should instead be in the
EventDeck of those other Characters--perhaps people, perhaps places,
perhaps tools--that the skill may be used on, with, or for. All of
those Characters' relevant EventDecks will be used in constructing a
new one, called the OutcomeDeck, and the outcome of the event will be
drawn from that.

Otherwise, Characters can be treated much like three-dimensional
dictionaries, wherein you may look up the Character's attributes. The
key is composed of the dimension an item of this character is in, the
item's name, and the name of the attribute.

"""
    tablename = "character"
    coldecls = {
        "character":
        {"name": "text"},
        "character_item_link":
        {"character": "text",
         "dimension": "text",
         "item": "text"},
        "attribute":
        {"name": "text",
         "type": "text"},
        "attribution":
        {"character": "text",
         "attribute": "text",
         "value": "text"}}
    primarykeys = {
        "character": ("name",),
        "character_item_link": ("character", "dimension", "item"),
        "attribute": ("name",),
        "attribution": ("character", "attribute")}
    foreignkeys = {
        "character_item_link":
        {"character": ("character", "name"),
         "dimension, item": ("item", "dimension, name")},
        "attribution":
        {"character": ("character", "name"),
         "attribute": ("attribute", "name")}}


class CharacterThing:
    # dictionary generatin' stuff for associating characters with things

    # I feel like it might be a good idea to model the particular
    # relevance a thing has to a character but I have no idea how, for
    # the moment...
    tablename = "characterthing"
    keydecldict = {"character": "text",
                   "dimension": "text",
                   "thing": "text"}
    valdecldict = {}
    fkeydict = {"character": ("character", "name")}


class CharacterStat:
    # generic stats. There are more columns than you might expect
    # because it's easier this way.
    tablename = "characterstat"
    keydecldict = {"character": "text",
                   "stat_name": "text"}
    valdecldict = {"stat_type": "text",
                   "bool_val": "boolean",
                   "int_val": "integer",
                   "float_val": "float",
                   "text_val": "text"}
    fkeydict = {"character": ("character", "name")}
    checks = ["stat_type in ('boolean', 'integer', 'float', 'text')"]


class CharacterAttemptDeck:
    # Associating characters with decks representing those things the
    # character can attempt irrespective of their skills or tools or
    # situation. Most of the time the links will be more indirect than
    # this, through Actions for instance.
    tablename = "charattempt"
    keydecldict = {"character": "text",
                   "deck": "text"}
    valdecldict = {}
    fkeydict = {"character": ("character", "name")}
