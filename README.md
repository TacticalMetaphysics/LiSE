LiSE is both a library and a standalone application for developing life simulation games.

# What is a life simulation game?

For the purposes of LiSE, it is any game where you are primarily concerned with "who you are" rather than "what you're doing". Everything your character in a life simulator can do should be represented somehow, but mostly in non-interactive form. This frees the player to attend to the high-level tasks of "living" in the game world: choosing what to do and when, rather than how.

In concrete terms, LiSE-style life simulators are games of time and resource management. The primary method for interacting with the game is to arrange events on a schedule, and then wait for your character(s) to carry them out. These games may be turn-based or real-time, but in the latter case, they allow the player to control the passage of game-time.

Existing games that LiSE seeks to imitate include:

* The Sims
* Kudos
* Animal Crossing
* Dwarf Fortress

# Why should I develop my life sim in LiSE?

At the moment, you probably shouldn't; it's pre-alpha and lacks most everything.

If you're not already a decent computer programmer, there just aren't many alternatives at the moment. You can make this kind of game in other game development systems, such as Adventure Game Studio, RenPy, or RPG Maker, but you will have to implement nearly all of the game logic on your own. They all offer systems to manage characters' time and money, but what if you want to let the game play itself for a few months or years of game-time, and see what happens? You could implement that function on your own, but that would be coding.

With LiSE, you can construct a world model with a drag-and-drop interface, then describe characters in the world by making decks of cards to represent such things as skills, habits, and personality traits. If the life you want to simulate is not too far out of the ordinary, you could get a game working in a few days. It might not be the most immersive thing, but you could still give characters routines to follow, and then fast-forward time to see how things turn out.

LiSE provides templates for the kinds of simulation elements that life sims tend to feature. Even if you *are* a good coder, these may be of use to you, and they are all written in pure Python. You could write your own engine with them, or compile a Python interpreter into some other game engine and use the templates to add life sim elements.
