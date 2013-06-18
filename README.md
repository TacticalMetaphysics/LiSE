LiSE is both a library and a standalone application for developing life simulation games.

# What is a life simulation game?

For the purposes of LiSE, it is any game where you are primarily concerned with "who you are" rather than "what you're doing". Everything your character in a life simulator can do should be represented somehow, but mostly in non-interactive form. This frees the player to attend to the high-level tasks of "living" in the game world: choosing what to do and when, rather than how.

In concrete terms, LiSE-style life simulators are games of time and resource management. The primary method for interacting with the game is to arrange events on a schedule, and then wait for your character(s) to carry them out. These games may be turn-based or real-time, but in the latter case, they allow the player to control the passage of game-time.

Existing games that LiSE seeks to imitate include:

* The Sims
* Kudos
* Animal Crossing
* Dwarf Fortress

# How does LiSE simulate life?

The stand-alone form of the engine provides a simple user interface
for both playing and developing games. The distinction is only in how
much control the user has over the world model--developers can
arbitrarily create and delete anything, players generally can't.

The interface metaphor is that of a board game. Developers put places
on the board--these, and the other visual elements, could be made to
look like anything, but are assumed to be dots or squares or other
simple geometric shapes, the likes of which you might see used in a
board game to distinguish the spots where you can put game
pieces. They draw lines between the places, called "portals," which
normally indicate that you can travel between two places. Then they
drag and drop a variety of things into the places, many of which
represent physical objects, such as people.

Actually, the engine distinguishes people from their bodies--more on
that later.

Potential changes to the state of the game world are "effects," which
look like trading cards. These could be given elaborate artwork of the
kind found in Magic: the Gathering and other such games. Players may
be given the option to play these "cards" from their "hand," but that
usually won't result in an immediate change to the game
world--instead, the effects will be assembled into an "event" that
gets scheduled in one of the game's many calendars. The player may be
allowed to reschedule the event by dragging it around in much the way
you do in a Personal Information Management app. Developers can do
this whenever they want, of course.

The distinction between a player and a developer is a matter of
launching the game engine with or without the developer's option. If you
don't want players to modify your game, this may not be the engine for
you.

Having scheduled a variety of events, the player starts time. Much as
in The Sims, they can pause whenever they want, and they can decide
how fast time should go. They may also be allowed to rewind! By
default, every game made with LiSE generates a random seed when first
started, and whenever a random choice is needed, the same seed is used
to make it. This makes it possible to try several approaches to a
given situation and see how *all of them* will turn out. It is also
convenient for debugging those random events.

Events with many possible outcomes are constructed from many effects,
resulting in an "outcome deck". When the event comes to pass, a given
number of effects are drawn from the deck, and are applied to the
world in the order they are drawn. Developers can decide whether a
given event should be drawn randomly or in FIFO or LIFO order. Events
constructed by players use the order the developer chose for the
player. Outcome decks from events already resolved may be kept around
and used again. They may also be rebuilt into their original state,
resulting in behavior similar to the roll of the die, or generated on
the fly by whatever algorithm you'd care to write.

Everything that happens in the game world happens as the result of
such an outcome deck, including eg. walking from one place to
another. Most of them won't be shown to the player, and many of the
decks will have only one effect in them. Some events aren't played
from the hand, but rather generated in response to some other command,
such as dragging the pawn representing your character to another place
in the game world. This will cause the engine (through the igraph
library) to perform pathfinding, and then schedule whatever movement
events it deems appropriate. You can reschedule those if you want,
though if you put them in the wrong order, you won't get to the place
you expected.

Most games will have more than one board in them. Events on all of
these can happen at the same time. Generally, only one of those boards
should represent "physical reality" in the form that video games
use--that is, only one board should manage the business of determining
where people are standing, how they get from here to there, and so
forth. The rest represent other game mechanics. You might use one to
implement a tech tree, as in Civilization, where instead of moving
about on it, the player has limited options for where to place
counters indicating they've acquired a given tech. You might use
another as a social graph, where the "places" are actually people, and
the "portals" are actually the relationships between them, connecting,
disconnecting, and changing color in response to drama. Templates for
several such boards will be provided.

Various places, things, and portals could represent the same person
for the purposes of different game mechanics. They are grouped
together in a "character," along with whatever other information the
game needs to have about the person. It's similar to the character
sheets that are used in tabletop roleplaying games. The information in
a character may be used to resolve the effects of any given event, and
to decide how to schedule any event. The character is what determines
how fast someone can move, whether in the physical world, the tech
tree, or elsewhere.

It's all very abstract. You could implement physics in this engine, if
you wanted, but if that's your main concern, you might be happier with
OpenSimulator.

# Requirements

* python 2.7
* python-igraph
* python-pyglet

# Roadmap

This is not even a prerelease. Call it a technical preview, maybe?

## UI

[ ] Show more than one board at a time.

### Widgets
- [x] Calendars
- [ ] Cards

## World model

- [x] Get effects to do more than open and close menus.
  They move things around now! Huzzah?
- [x] Get events and schedules working.
- [x] That last calls for a main loop--for the game state only, not the
UI--that polls the schedule, calls the events that are happening, and
advances the clock.

## Database
- [x] Sync the state of the UI.
- [ ] Sync changes to the world model.
- [ ] Keep a *branching* journal of the aforementioned changes.
- [ ] Roll-back and replay those changes in the most recent branch.
- [ ] Select a branch and replay it.
- [ ] Add the ability to import and export particular game elements to other
databases.

## Templates

I'll have to actually make a simulator in order to demonstrate the
concepts. Then I'll genericize the components of it and package them
as things you can drop into your own projects.

The premise of the test sim is that you are the headmaster of a wizarding school. It has a dungeon or two in it, and you've got to keep the monsters therein from getting out, and maybe retrieve valuables and do some research down there; but your main source of income is your students, who may inadvertently transmute one another.
