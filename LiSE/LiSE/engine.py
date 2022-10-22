# This file is part of ELiDE, frontend to LiSE, a framework for life simulation games.
# Copyright (c) Zachary Spector, public@zacharyspector.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The "engine" of LiSE is an object relational mapper with special
stores for game data and entities, as well as properties for manipulating the
flow of time.

"""
from functools import partial
from collections import defaultdict
from types import FunctionType, ModuleType
from typing import Union, Tuple, Any, Set, List, Type, Hashable
from os import PathLike
from abc import ABC, abstractmethod

import numpy as np
from networkx import Graph
from blinker import Signal
from .allegedb import ORM as gORM
from .allegedb import (StatDictType, NodeValDictType, EdgeValDictType,
						DeltaType, world_locked)
from .util import sort_set, AbstractEngine, final_rule
from .xcollections import StringStore, FunctionStore, MethodStore
from .query import (Query, EqQuery, NeQuery, make_side_sel,
					windows_intersection, make_select_from_eq_query,
					StatusAlias, ComparisonQuery, CompoundQuery,
					EqNeQueryResultEndTurn, GtLtQueryResultMidTurn,
					QueryResult, GtLtQueryResultEndTurn, CombinedQueryResult,
					_msfq_mid_turn, _getcol, _msfq_end_turn)
from . import exc


class InnerStopIteration(StopIteration):
	pass


class DummyEntity(dict):
	"""Something to use in place of a node or edge"""
	__slots__ = ['engine']

	def __init__(self, engine: 'AbstractEngine'):
		super().__init__()
		self.engine = engine


class NextTurn(Signal):
	"""Make time move forward in the simulation.

	Calls ``advance`` repeatedly, returning a list of the rules' return values.

	I am also a ``Signal``, so you can register functions to be
	called when the simulation runs. Pass them to my ``connect``
	method.

	"""

	def __init__(self, engine: AbstractEngine):
		super().__init__()
		self.engine = engine

	def __call__(self) -> Tuple[List, DeltaType]:
		engine = self.engine
		start_branch, start_turn, start_tick = engine._btt()
		latest_turn = engine._turns_completed[start_branch]
		if start_turn < latest_turn:
			engine.turn += 1
			self.send(engine,
						branch=engine.branch,
						turn=engine.turn,
						tick=engine.tick)
			return [], engine.get_delta(branch=start_branch,
										turn_from=start_turn,
										turn_to=engine.turn,
										tick_from=start_tick,
										tick_to=engine.tick)
		elif start_turn > latest_turn + 1:
			raise exc.RulesEngineError(
				"Can't run the rules engine on any turn but the latest")
		if start_turn == latest_turn:
			# As a side effect, the following assignment sets the tick
			# to the latest in the new turn, which will be 0 if that
			# turn has not yet been simulated.
			engine.turn += 1
		with engine.advancing():
			for res in iter(engine.advance, final_rule):
				if res:
					engine.universal['last_result'] = res
					engine.universal['last_result_idx'] = 0
					branch, turn, tick = engine._btt()
					self.send(engine, branch=branch, turn=turn, tick=tick)
					return res, engine.get_delta(branch=start_branch,
													turn_from=start_turn,
													turn_to=turn,
													tick_from=start_tick,
													tick_to=tick)
		engine._turns_completed[start_branch] = engine.turn
		engine.query.complete_turn(
			start_branch,
			engine.turn,
			discard_rules=not engine.keep_rules_journal)
		kfi = engine.keyframe_interval
		if kfi and engine.turn % kfi == 0:
			engine.snap_keyframe()
		if engine.flush_interval and engine.turn % engine.flush_interval == 0:
			engine.query.flush()
		if engine.commit_interval and engine.turn % engine.commit_interval == 0:
			engine.query.commit()
		self.send(self.engine,
					branch=engine.branch,
					turn=engine.turn,
					tick=engine.tick)
		delta = engine.get_delta(branch=engine.branch,
									turn_from=start_turn,
									turn_to=engine.turn,
									tick_from=start_tick,
									tick_to=engine.tick)
		return [], delta


class AbstractSchema(ABC):
	"""Base class for schemas describing what changes are permitted to the game world"""

	def __init__(self, engine: AbstractEngine):
		self.engine = engine

	@abstractmethod
	def entity_permitted(self, entity):
		raise NotImplementedError

	@abstractmethod
	def stat_permitted(self, turn, entity, key, value):
		raise NotImplementedError


class NullSchema(AbstractSchema):
	"""Schema that permits all changes to the game world"""

	def entity_permitted(self, entity):
		return True

	def stat_permitted(self, turn, entity, key, value):
		return True


class Engine(AbstractEngine, gORM):
	"""LiSE, the Life Simulator Engine.

	Each instance of LiSE maintains a connection to a database
	representing the state of a simulated world. Simulation rules
	within this world are described by lists of Python functions, some
	of which make changes to the world.

	The top-level data structure within LiSE is the character. Most
	data within the world model is kept in some character or other;
	these will quite frequently represent people, but can be readily
	adapted to represent any kind of data that can be comfortably
	described as a graph or a JSON object. Every change to a character
	will be written to the database.

	LiSE tracks history as a series of turns. In each turn, each
	simulation rule is evaluated once for each of the simulated
	entities it's been applied to. World changes in a given turn are
	remembered together, such that the whole world state can be
	rewound: simply set the properties ``branch`` and ``turn`` back to
	what they were just before the change you want to undo.

	Properties:

	- ``branch``: The fork of the timestream that we're on.
	- ``turn``: Units of time that have passed since the sim started.
	- ``time``: ``(branch, turn)``, and you can register functions to be called
	  when the time changes, as ``eng.time.connect(func)``
	- ``tick``: A counter of how many changes have occurred this turn.
	  Can be set manually, but is more often set to the last tick in a turn
	  as a side effect of setting ``turn``.
	- ``character``: A mapping of :class:`Character` objects by name.
	- ``rule``: A mapping of all rules that have been made.
	- ``rulebook``: A mapping of lists of rules. They are followed in
	  their order.  A whole rulebook full of rules may be assigned to
	  an entity at once.
	- ``trigger``: Functions that might trigger a rule.
	- ``prereq``: Functions a rule might require to return
	  ``True`` for it to run.
	- ``action``: Functions that might manipulate the world
	  state as a result of a rule running.
	- ``method``: Extension methods to be added to the engine object.
	- ``function``: Generic functions. All of ``trigger``, ``prereq``,
	  ``action``, ``method``, and ``function`` are modules or similar;
	  they default to :class:`FunctionStore` objects, which can write
	  Python code to the underlying module at runtime.
	- ``string``: A mapping of strings, probably shown to the player
	  at some point. Defaults to a :class:`StringStore` object,
	  which can alter the underlying JSON file at runtime.
	- ``eternal``: Mapping of arbitrary serializable objects. It isn't
	  sensitive to sim-time. A good place to keep game settings.
	- ``universal``: Another mapping of arbitrary serializable
	  objects, but this one *is* sensitive to sim-time. Each turn, the
	  state of the randomizer is saved here under the key
	  ``'rando_state'``.

	"""
	from .character import Character
	from .thing import Thing
	from .place import Place
	from .portal import Portal
	from .query import QueryEngine
	char_cls = Character
	thing_cls = Thing
	place_cls = node_cls = Place
	portal_cls = edge_cls = Portal
	query_engine_cls = QueryEngine
	illegal_graph_names = [
		'global', 'eternal', 'universal', 'rulebooks', 'rules'
	]
	illegal_node_names = ['nodes', 'node_val', 'edges', 'edge_val', 'things']

	def __init__(self,
					prefix: Union[PathLike, str] = '.',
					*,
					string: Union[StringStore, dict] = None,
					trigger: Union[FunctionStore, ModuleType] = None,
					prereq: Union[FunctionStore, ModuleType] = None,
					action: Union[FunctionStore, ModuleType] = None,
					function: Union[FunctionStore, ModuleType] = None,
					method: Union[MethodStore, ModuleType] = None,
					connect_string: str = None,
					connect_args: dict = None,
					schema_cls: Type[AbstractSchema] = NullSchema,
					flush_interval=1,
					keyframe_interval=10,
					commit_interval: int = None,
					random_seed: int = None,
					logfun: FunctionType = None,
					clear=False,
					keep_rules_journal=True,
					keyframe_on_close=True,
					cache_arranger=False):
		"""Store the connections for the world database and the code database;
		set up listeners; and start a transaction

		:arg prefix: directory containing the simulation and its code;
		defaults to the working directory
		:arg string: module storing strings to be used in the game
		:arg function: module containing utility functions
		:arg method: module containing functions taking this engine as
		first arg
		:arg trigger: module containing trigger functions, taking a LiSE
		entity and returning a boolean for whether to run a rule
		:arg prereq: module containing prereq functions, taking a LiSE entity and
		returning a boolean for whether to permit a rule to run
		:arg action: module containing action functions, taking a LiSE entity and
		mutating it (and possibly the rest of the world)
		:arg connect_string: a rfc1738 URI for a database to connect to
		:arg connect_args: dictionary of keyword arguments for the
		database connection
		:arg schema: a Schema class that determines which changes to allow to
		the world; used when a player should not be able to change just anything.
		Defaults to `NullSchema`
		:arg flush_interval: LiSE will put pending changes into the database
		transaction every ``flush_interval`` turns. If ``None``), only flush
		on commit. Default ``1``.
		:arg keyframe_interval: How many turns to pass before automatically
		snapping a keyframe, default ``10``. If ``None``, you'll need
		to call ``snap_keyframe`` yourself.
		:arg commit_interval: LiSE will commit changes to disk every
		``commit_interval`` turns. If ``None`` (the default), only commit
		on close or manual call to ``commit``
		:arg random_seed: a number to initialize the randomizer
		:arg logfun: an optional function taking arguments
		``level, message``, which should log `message` somehow
		:arg clear: whether to delete *any and all* existing data
		and code in ``prefix``. Use with caution!
		:arg keep_rules_journal: Boolean; if true (default), keep
		information on the behavior of the rules engine in the database.
		Makes the database rather large, but useful for debugging.
		:arg keyframe_on_close: Whether to snap a keyframe when closing the
		engine, default ``True``. This is usually what you want, as it will
		make future startups faster, but could cause database bloat if
		your game runs few turns per session.
		:arg cache_arranger: Whether to start a background
		process that indexes the caches to make time travel faster
		when it's to points we anticipate. If you use this, you can
		specify some other point in time to index by putting the
		`(branch, turn, tick)` in my `cache_arrange_queue`. Default ``False``.

		"""
		if logfun is None:
			from logging import getLogger
			logger = getLogger("Life Sim Engine")

			def logfun(level, msg):
				getattr(logger, level)(msg)

		self.log = logfun
		import os
		from .xcollections import StringStore
		if connect_args is None:
			connect_args = {}
		if not os.path.exists(prefix):
			os.mkdir(prefix)
		if not os.path.isdir(prefix):
			raise FileExistsError("Need a directory")
		self.keep_rules_journal = keep_rules_journal
		self._keyframe_on_close = keyframe_on_close
		if string:
			self.string = string
		else:
			self._string_file = os.path.join(prefix, 'strings.json')
			if clear and os.path.exists(self._string_file):
				os.remove(self._string_file)
		if function:
			self.function = function
		else:
			self._function_file = os.path.join(prefix, 'function.py')
			if clear and os.path.exists(self._function_file):
				os.remove(self._function_file)
		if method:
			self.method = method
		else:
			self._method_file = os.path.join(prefix, 'method.py')
			if clear and os.path.exists(self._method_file):
				os.remove(self._method_file)
		if trigger:
			self.trigger = trigger
		else:
			self._trigger_file = os.path.join(prefix, 'trigger.py')
			if clear and os.path.exists(self._trigger_file):
				os.remove(self._trigger_file)
		if prereq:
			self.prereq = prereq
		else:
			self._prereq_file = os.path.join(prefix, 'prereq.py')
			if clear and os.path.exists(self._prereq_file):
				os.remove(self._prereq_file)
		if action:
			self.action = action
		else:
			self._action_file = os.path.join(prefix, 'action.py')
			if clear and os.path.exists(self._action_file):
				os.remove(self._action_file)
		self.schema = schema_cls(self)
		if connect_string:
			connect_string = connect_string.split('sqlite:///')[-1]
		super().__init__(connect_string or os.path.join(prefix, 'world.db'),
							clear=clear,
							connect_args=connect_args,
							cache_arranger=cache_arranger)
		self._things_cache.setdb = self.query.set_thing_loc
		self._universal_cache.setdb = self.query.universal_set
		self._rulebooks_cache.setdb = self.query.rulebook_set
		self.eternal = self.query.globl
		if hasattr(self, '_string_file'):
			self.string = StringStore(
				self.query, self._string_file,
				self.eternal.setdefault('language', 'eng'))
		self.next_turn = NextTurn(self)
		self.commit_interval = commit_interval
		self.keyframe_interval = keyframe_interval
		self.flush_interval = flush_interval
		self._rules_iter = self._follow_rules()
		# set up the randomizer
		from random import Random
		self._rando = Random()
		if 'rando_state' in self.universal:
			self._rando.setstate(self.universal['rando_state'])
		else:
			self._rando.seed(random_seed)
			self.universal['rando_state'] = self._rando.getstate()
		if hasattr(self.method, 'init'):
			self.method.init(self)
		if cache_arranger:
			self._start_cache_arranger()

	def _start_cache_arranger(self) -> None:
		for branch, (parent, turn_start, tick_start, turn_end,
						tick_end) in self._branches.items():
			self.cache_arrange_queue.put((branch, turn_start, tick_start))
			if (turn_start, tick_start) != (turn_end, tick_end):
				self.cache_arrange_queue.put((branch, turn_end, tick_end))
		if not self._cache_arrange_thread.is_alive():
			self._cache_arrange_thread.start()

	def _init_load(self) -> None:
		from .rule import Rule
		q = self.query
		super()._init_load()
		self._unitness_cache.load(q.units_dump())
		self._universal_cache.load(q.universals_dump())
		self._rulebooks_cache.load(q.rulebooks_dump())
		self._characters_rulebooks_cache.load(q.character_rulebook_dump())
		self._units_rulebooks_cache.load(q.unit_rulebook_dump())
		self._characters_things_rulebooks_cache.load(
			q.character_thing_rulebook_dump())
		self._characters_places_rulebooks_cache.load(
			q.character_place_rulebook_dump())
		self._characters_portals_rulebooks_cache.load(
			q.character_portal_rulebook_dump())
		self._nodes_rulebooks_cache.load(q.node_rulebook_dump())
		self._portals_rulebooks_cache.load(q.portal_rulebook_dump())
		self._triggers_cache.load(q.rule_triggers_dump())
		self._prereqs_cache.load(q.rule_prereqs_dump())
		self._actions_cache.load(q.rule_actions_dump())
		store_crh = self._character_rules_handled_cache.store
		for row in q.character_rules_handled_dump():
			store_crh(*row, loading=True)
		store_arh = self._unit_rules_handled_cache.store
		for row in q.unit_rules_handled_dump():
			store_arh(*row, loading=True)
		store_ctrh = self._character_thing_rules_handled_cache.store
		for row in q.character_thing_rules_handled_dump():
			store_ctrh(*row, loading=True)
		store_cprh = self._character_place_rules_handled_cache.store
		for row in q.character_place_rules_handled_dump():
			store_cprh(*row, loading=True)
		store_cporh = self._character_portal_rules_handled_cache.store
		for row in q.character_portal_rules_handled_dump():
			store_cporh(*row, loading=True)
		store_cnrh = self._node_rules_handled_cache.store
		for row in q.node_rules_handled_dump():
			store_cnrh(*row, loading=True)
		store_porh = self._portal_rules_handled_cache.store
		for row in q.portal_rules_handled_dump():
			store_porh(*row, loading=True)
		self._turns_completed.update(q.turns_completed_dump())
		self._rules_cache = {
			name: Rule(self, name, create=False)
			for name in q.rules_dump()
		}

	def _load_at(self, branch: str, turn: int, tick: int) -> None:
		(latest_past_keyframe, earliest_future_keyframe, keyframed, noderows,
			edgerows, graphvalrows, nodevalrows,
			edgevalrows) = super()._load_at(branch, turn, tick)
		thingrows = []

		def build_thingrows(graf, windows):
			if not windows:
				return
			if len(windows) == 1:
				btt = windows[0]
				thingrows.extend(load_things(graf, *btt))
				return
			for window in reversed(windows):
				thingrows.extend(load_things(graf, *window))

		load_things = self.query.load_things
		if latest_past_keyframe is None:
			# Load thing data from the beginning of time to now
			for graph in self.graph:
				build_thingrows(
					graph,
					self._build_loading_windows('trunk', 0, 0, branch, turn,
												tick))
		else:
			past_branch, past_turn, past_tick = latest_past_keyframe
			if earliest_future_keyframe is None:
				# Load thing data from the keyframe to now
				for graph in self.graph:
					build_thingrows(
						graph,
						self._build_loading_windows(past_branch, past_turn,
													past_tick, branch, turn,
													tick))
			else:
				# Load thing data between the two keyframes
				(future_branch, future_turn,
					future_tick) = earliest_future_keyframe

				for graph in self.graph:
					build_thingrows(
						graph,
						self._build_loading_windows(past_branch, past_turn,
													past_tick, future_branch,
													future_turn, future_tick))
		if thingrows:
			with self.batch():
				self._things_cache.load(thingrows)
		else:
			self.warning(f"No thing data at {branch, turn, tick}")

	def _init_caches(self) -> None:
		from .xcollections import (FunctionStore, CharacterMapping,
									UniversalMapping)
		from .cache import (
			NodeContentsCache, InitializedCache, EntitylessCache,
			InitializedEntitylessCache, UnitnessCache, UnitRulesHandledCache,
			CharacterThingRulesHandledCache, CharacterPlaceRulesHandledCache,
			CharacterPortalRulesHandledCache, NodeRulesHandledCache,
			PortalRulesHandledCache, CharacterRulesHandledCache, ThingsCache)
		from .rule import AllRuleBooks, AllRules

		super()._init_caches()
		self._things_cache = ThingsCache(self)
		self._node_contents_cache = NodeContentsCache(self)
		self.character = self.graph = CharacterMapping(self)
		self._universal_cache = EntitylessCache(self)
		self._universal_cache.name = 'universal_cache'
		self._rulebooks_cache = InitializedEntitylessCache(self)
		self._rulebooks_cache.name = 'rulebooks_cache'
		self._characters_rulebooks_cache = InitializedEntitylessCache(self)
		self._characters_rulebooks_cache.name = 'characters_rulebooks_cache'
		self._units_rulebooks_cache = InitializedEntitylessCache(self)
		self._units_rulebooks_cache.name = 'units_rulebooks_cache'
		ctrc = InitializedEntitylessCache(self)
		ctrc.name = 'characters_things_rulebooks_cache'
		self._characters_things_rulebooks_cache = ctrc
		cprc = InitializedEntitylessCache(self)
		cprc.name = 'characters_places_rulebooks_cache'
		self._characters_places_rulebooks_cache = cprc
		cporc = InitializedEntitylessCache(self)
		cporc.name = 'characters_portals_rulebooks_cache'
		self._characters_portals_rulebooks_cache = cporc
		self._nodes_rulebooks_cache = InitializedCache(self)
		self._nodes_rulebooks_cache.name = 'nodes_rulebooks_cache'
		self._portals_rulebooks_cache = InitializedCache(self)
		self._portals_rulebooks_cache.name = 'portals_rulebooks_cache'
		self._triggers_cache = InitializedEntitylessCache(self)
		self._triggers_cache.name = 'triggers_cache'
		self._prereqs_cache = InitializedEntitylessCache(self)
		self._prereqs_cache.name = 'prereqs_cache'
		self._actions_cache = InitializedEntitylessCache(self)
		self._actions_cache.name = 'actions_cache'
		self._node_rules_handled_cache = NodeRulesHandledCache(self)
		self._node_rules_handled_cache.name = 'node_rules_handled_cache'
		self._portal_rules_handled_cache = PortalRulesHandledCache(self)
		self._portal_rules_handled_cache.name = 'portal_rules_handled_cache'
		crhc = CharacterRulesHandledCache(self)
		crhc.name = 'character_rules_handled_cache'
		self._character_rules_handled_cache = crhc
		self._unit_rules_handled_cache = UnitRulesHandledCache(self)
		self._unit_rules_handled_cache.name = 'unit_rules_handled_cache'
		ctrhc = CharacterThingRulesHandledCache(self)
		ctrhc.name = 'character_thing_rules_handled_cache'
		self._character_thing_rules_handled_cache = ctrhc
		cprhc = CharacterPlaceRulesHandledCache(self)
		cprhc.name = 'character_place_rules_handled_cache'
		self._character_place_rules_handled_cache = cprhc
		cporhc = CharacterPortalRulesHandledCache(self)
		cporhc.name = 'character_portal_rules_handled_cache'
		self._character_portal_rules_handled_cache = cporhc
		self._unitness_cache = UnitnessCache(self)
		self._unitness_cache.name = 'unitness_cache'
		self._turns_completed = defaultdict(lambda: max((0, self.turn - 1)))
		self._turns_completed_previous = self._turns_completed.copy()
		"""The last turn when the rules engine ran in each branch"""
		self.universal = UniversalMapping(self)
		if hasattr(self, '_action_file'):
			self.action = FunctionStore(self._action_file)
		if hasattr(self, '_prereq_file'):
			self.prereq = FunctionStore(self._prereq_file)
		if hasattr(self, '_trigger_file'):
			self.trigger = FunctionStore(self._trigger_file)
		if hasattr(self, '_function_file'):
			self.function = FunctionStore(self._function_file)
		if hasattr(self, '_method_file'):
			self.method = FunctionStore(self._method_file)
		self.rule = AllRules(self)
		self.rulebook = AllRuleBooks(self)

	def _load_graphs(self) -> None:
		for charn in self.query.characters():
			self._graph_objs[charn] = self.char_cls(self,
													charn,
													init_rulebooks=False)

	def _make_node(self, graph: Character,
					node: Hashable) -> Union[thing_cls, place_cls]:
		if self._is_thing(graph.name, node):
			return self.thing_cls(graph, node)
		else:
			return self.place_cls(graph, node)

	def _make_edge(self,
					graph: Character,
					orig: Union[thing_cls, place_cls],
					dest: Union[thing_cls, place_cls],
					idx=0) -> portal_cls:
		return self.portal_cls(graph, orig, dest)

	def get_delta(self, branch: str, turn_from: int, tick_from: int,
					turn_to: int, tick_to: int) -> DeltaType:
		"""Get a dictionary describing changes to the world.

		Most keys will be character names, and their values will be
		dictionaries of the character's stats' new values, with ``None``
		for deleted keys. Characters' dictionaries have special keys
		'nodes' and 'edges' which contain booleans indicating whether
		the node or edge exists at the moment, and 'node_val' and
		'edge_val' for the stats of those entities. For edges (also
		called portals) these dictionaries are two layers deep, keyed
		first by the origin, then by the destination.

		Characters also have special keys for the various rulebooks
		they have:

		* 'character_rulebook'
		* 'unit_rulebook'
		* 'character_thing_rulebook'
		* 'character_place_rulebook'
		* 'character_portal_rulebook'

		And each node and edge may have a 'rulebook' stat of its own.
		If a node is a thing, it gets a 'location'; when the 'location'
		is deleted, that means it's back to being a place.

		Keys at the top level that are not character names:

		* 'rulebooks', a dictionary keyed by the name of each changed
		  rulebook, the value being a list of rule names
		* 'rules', a dictionary keyed by the name of each changed rule,
		  containing any of the lists 'triggers', 'prereqs', and 'actions'

		"""
		from .allegedb.window import update_window, update_backward_window
		if not isinstance(branch, str):
			raise TypeError("branch must be str")
		for arg in (turn_from, tick_from, turn_to, tick_to):
			if not isinstance(arg, int):
				raise TypeError("turn and tick must be int")
		if turn_from == turn_to:
			return self.get_turn_delta(branch,
										turn_to,
										tick_to,
										start_tick=tick_from)
		delta = super().get_delta(branch, turn_from, tick_from, turn_to,
									tick_to)
		if turn_from < turn_to:
			updater = partial(update_window, turn_from, tick_from, turn_to,
								tick_to)
			attribute = 'settings'
			tick_to += 1
		else:
			updater = partial(update_backward_window, turn_from, tick_from,
								turn_to, tick_to)
			attribute = 'presettings'
		univbranches = getattr(self._universal_cache, attribute)
		avbranches = getattr(self._unitness_cache, attribute)
		thbranches = getattr(self._things_cache, attribute)
		rbbranches = getattr(self._rulebooks_cache, attribute)
		trigbranches = getattr(self._triggers_cache, attribute)
		preqbranches = getattr(self._prereqs_cache, attribute)
		actbranches = getattr(self._actions_cache, attribute)
		charrbbranches = getattr(self._characters_rulebooks_cache, attribute)
		avrbbranches = getattr(self._units_rulebooks_cache, attribute)
		charthrbbranches = getattr(self._characters_things_rulebooks_cache,
									attribute)
		charplrbbranches = getattr(self._characters_places_rulebooks_cache,
									attribute)
		charporbbranches = getattr(self._characters_portals_rulebooks_cache,
									attribute)
		noderbbranches = getattr(self._nodes_rulebooks_cache, attribute)
		edgerbbranches = getattr(self._portals_rulebooks_cache, attribute)

		def upduniv(_, key, val):
			delta.setdefault('universal', {})[key] = val

		if branch in univbranches:
			updater(upduniv, univbranches[branch])

		def updav(char, graph, node, av):
			delta.setdefault(char, {}).setdefault('units', {}).setdefault(
				graph, {})[node] = bool(av)

		if branch in avbranches:
			updater(updav, avbranches[branch])

		def updthing(char, thing, loc):
			if (char in delta and 'nodes' in delta[char]
				and thing in delta[char]['nodes']
				and not delta[char]['nodes'][thing]):
				return
			thingd = delta.setdefault(char, {}).setdefault('node_val',
															{}).setdefault(
																thing, {})
			thingd['location'] = loc

		if branch in thbranches:
			updater(updthing, thbranches[branch])

		def updrb(_, rulebook, rules):
			delta.setdefault('rulebooks', {})[rulebook] = rules

		if branch in rbbranches:
			updater(updrb, rbbranches[branch])

		def updru(key, _, rule, funs):
			delta.setdefault('rules', {}).setdefault(rule, {})[key] = funs

		if branch in trigbranches:
			updater(partial(updru, 'triggers'), trigbranches[branch])

		if branch in preqbranches:
			updater(partial(updru, 'prereqs'), preqbranches[branch])

		if branch in actbranches:
			updater(partial(updru, 'actions'), actbranches[branch])

		def updcrb(key, _, character, rulebook):
			delta.setdefault(character, {})[key] = rulebook

		if branch in charrbbranches:
			updater(partial(updcrb, 'character_rulebook'),
					charrbbranches[branch])

		if branch in avrbbranches:
			updater(partial(updcrb, 'unit_rulebook'), avrbbranches[branch])

		if branch in charthrbbranches:
			updater(partial(updcrb, 'character_thing_rulebook'),
					charthrbbranches[branch])

		if branch in charplrbbranches:
			updater(partial(updcrb, 'character_place_rulebook'),
					charplrbbranches[branch])

		if branch in charporbbranches:
			updater(partial(updcrb, 'character_portal_rulebook'),
					charporbbranches[branch])

		def updnoderb(character, node, rulebook):
			if (character in delta and 'nodes' in delta[character]
				and node in delta[character]['nodes']
				and not delta[character]['nodes'][node]):
				return
			delta.setdefault(character,
								{}).setdefault('node_val', {}).setdefault(
									node, {})['rulebook'] = rulebook

		if branch in noderbbranches:
			updater(updnoderb, noderbbranches[branch])

		def updedgerb(character, orig, dest, rulebook):
			if (character in delta and 'edges' in delta[character]
				and orig in delta[character]['edges']
				and dest in delta[character]['edges'][orig]
				and not delta[character]['edges'][orig][dest]):
				return
			delta.setdefault(character,
								{}).setdefault('edge_val', {}).setdefault(
									orig,
									{}).setdefault(dest,
													{})['rulebook'] = rulebook

		if branch in edgerbbranches:
			updater(updedgerb, edgerbbranches[branch])

		return delta

	def get_turn_delta(self,
						branch: str = None,
						turn: int = None,
						tick: int = None,
						start_tick=0) -> DeltaType:
		"""Get a dictionary of changes to the world within a given turn

		Defaults to the present turn, and stops at the present tick
		unless specified.

		See the documentation for ``get_delta`` for a detailed
		description of the delta format.

		:arg branch: branch of history, defaulting to the present branch
		:arg turn: turn within the branch, defaulting to the present
				   turn
		:arg tick: tick at which to stop the delta, defaulting to the
				   present tick
		:arg start_tick: tick at which to start the delta, default 0

		"""
		branch = branch or self.branch
		turn = turn or self.turn
		tick = tick or self.tick
		if tick == start_tick:
			return {}
		delta = super().get_turn_delta(branch, turn, start_tick, tick)
		if start_tick < tick:
			attribute = 'settings'
			tick += 1
		else:
			attribute = 'presettings'
		avatarness_settings = getattr(self._unitness_cache, attribute)
		things_settings = getattr(self._things_cache, attribute)
		rulebooks_settings = getattr(self._rulebooks_cache, attribute)
		triggers_settings = getattr(self._triggers_cache, attribute)
		prereqs_settings = getattr(self._prereqs_cache, attribute)
		actions_settings = getattr(self._actions_cache, attribute)
		character_rulebooks_settings = getattr(
			self._characters_rulebooks_cache, attribute)
		avatar_rulebooks_settings = getattr(self._units_rulebooks_cache,
											attribute)
		character_thing_rulebooks_settings = getattr(
			self._characters_things_rulebooks_cache, attribute)
		character_place_rulebooks_settings = getattr(
			self._characters_places_rulebooks_cache, attribute)
		character_portal_rulebooks_settings = getattr(
			self._characters_portals_rulebooks_cache, attribute)
		node_rulebooks_settings = getattr(self._nodes_rulebooks_cache,
											attribute)
		portal_rulebooks_settings = getattr(self._portals_rulebooks_cache,
											attribute)
		if branch in avatarness_settings and turn in avatarness_settings[
			branch]:
			for chara, graph, node, is_av in avatarness_settings[branch][turn][
				start_tick:tick]:
				delta.setdefault(chara, {}).setdefault('units', {}).setdefault(
					graph, {})[node] = is_av
		if branch in things_settings and turn in things_settings[branch]:
			for chara, thing, location in things_settings[branch][turn][
				start_tick:tick]:
				thingd = delta.setdefault(chara, {}).setdefault(
					'node_val', {}).setdefault(thing, {})
				thingd['location'] = location
		delta['rulebooks'] = rbdif = {}
		if branch in rulebooks_settings and turn in rulebooks_settings[branch]:
			for _, rulebook, rules in rulebooks_settings[branch][turn][
				start_tick:tick]:
				rbdif[rulebook] = rules
		delta['rules'] = rdif = {}
		if branch in triggers_settings and turn in triggers_settings[branch]:
			for _, rule, funs in triggers_settings[branch][turn][
				start_tick:tick]:
				rdif.setdefault(rule, {})['triggers'] = funs
		if branch in prereqs_settings and turn in prereqs_settings[branch]:
			for _, rule, funs in prereqs_settings[branch][turn][
				start_tick:tick]:
				rdif.setdefault(rule, {})['prereqs'] = funs
		if branch in actions_settings and turn in actions_settings[branch]:
			for _, rule, funs in actions_settings[branch][turn][
				start_tick:tick]:
				rdif.setdefault(rule, {})['actions'] = funs

		if (branch in character_rulebooks_settings
			and turn in character_rulebooks_settings[branch]):
			for _, character, rulebook in character_rulebooks_settings[branch][
				turn][start_tick:tick]:
				delta.setdefault(character,
									{})['character_rulebook'] = rulebook
		if (branch in avatar_rulebooks_settings
			and turn in avatar_rulebooks_settings[branch]):
			for _, character, rulebook in avatar_rulebooks_settings[branch][
				turn][start_tick:tick]:
				delta.setdefault(character, {})['unit_rulebook'] = rulebook
		if (branch in character_thing_rulebooks_settings
			and turn in character_thing_rulebooks_settings[branch]):
			for _, character, rulebook in character_thing_rulebooks_settings[
				branch][turn][start_tick:tick]:
				delta.setdefault(character,
									{})['character_thing_rulebook'] = rulebook
		if (branch in character_place_rulebooks_settings
			and turn in character_place_rulebooks_settings[branch]):
			for _, character, rulebook in character_place_rulebooks_settings[
				branch][turn][start_tick:tick]:
				delta.setdefault(character,
									{})['character_place_rulebook'] = rulebook
		if (branch in character_portal_rulebooks_settings
			and turn in character_portal_rulebooks_settings[branch]):
			for _, character, rulebook in character_portal_rulebooks_settings[
				branch][turn][start_tick:tick]:
				delta.setdefault(character,
									{})['character_portal_rulebook'] = rulebook

		if (branch in node_rulebooks_settings
			and turn in node_rulebooks_settings[branch]):
			for character, node, rulebook in node_rulebooks_settings[branch][
				turn][start_tick:tick]:
				delta.setdefault(character,
									{}).setdefault('node_val', {}).setdefault(
										node, {})['rulebook'] = rulebook
		if (branch in portal_rulebooks_settings
			and turn in portal_rulebooks_settings[branch]):
			for character, orig, dest, rulebook in portal_rulebooks_settings[
				branch][turn][start_tick:tick]:
				delta.setdefault(character, {}).setdefault(
					'edge_val',
					{}).setdefault(orig,
									{}).setdefault(dest,
													{})['rulebook'] = rulebook
		return delta

	def _del_rulebook(self, rulebook):
		raise NotImplementedError("Can't delete rulebooks yet")

	def _remember_unitness(self,
							character: Character,
							graph: Character,
							node: Union[thing_cls, place_cls],
							is_unit=True,
							branch: str = None,
							turn: int = None,
							tick: int = None) -> None:
		"""Use this to record a change in unitness.

		Should be called whenever a node that wasn't an unit of a
		character now is, and whenever a node that was an unit of a
		character now isn't.

		``character`` is the one using the node as an unit,
		``graph`` is the character the node is in.

		"""
		branch = branch or self.branch
		turn = turn or self.turn
		tick = tick or self.tick
		self._unitness_cache.store(character, graph, node, branch, turn, tick,
									is_unit)
		self.query.unit_set(character, graph, node, branch, turn, tick,
							is_unit)

	@property
	def stores(self):
		return (self.action, self.prereq, self.trigger, self.function,
				self.method, self.string)

	def debug(self, msg: str) -> None:
		"""Log a message at level 'debug'"""
		self.log('debug', msg)

	def info(self, msg: str) -> None:
		"""Log a message at level 'info'"""
		self.log('info', msg)

	def warning(self, msg: str) -> None:
		"""Log a message at level 'warning'"""
		self.log('warning', msg)

	def error(self, msg: str) -> None:
		"""Log a message at level 'error'"""
		self.log('error', msg)

	def critical(self, msg: str) -> None:
		"""Log a message at level 'critical'"""
		self.log('critical', msg)

	def flush(self) -> None:
		self.query.flush()

	@world_locked
	def commit(self) -> None:
		try:
			self.universal['rando_state'] = self._rando.getstate()
		except exc.OutOfTimelineError:
			branch, turn, tick = self.branch, self.turn, self.tick
			self.turn = self._branches[branch][3]
			self.universal['rando_state'] = self._rando.getstate()
			self.turn = turn
			self.tick = tick
		turns_completed_previous = self._turns_completed_previous
		turns_completed = self._turns_completed
		set_turn_completed = self.query.set_turn_completed
		for branch, turn_late in turns_completed.items():
			turn_early = turns_completed_previous.get(branch)
			if turn_late != turn_early:
				if turn_early is not None and turn_late <= turn_early:
					raise RuntimeError("Incoherent turns_completed cache")
				set_turn_completed(branch, turn_late)
		self._turns_completed_previous = turns_completed.copy()
		super().commit()

	def close(self) -> None:
		"""Commit changes and close the database."""
		import sys
		import os
		if self._keyframe_on_close:
			self.snap_keyframe()
		for store in self.stores:
			if hasattr(store, 'save'):
				store.save(reimport=False)
			path, filename = os.path.split(store._filename)
			modname = filename[:-3]
			if modname in sys.modules:
				del sys.modules[modname]
		super().close()

	def __enter__(self):
		"""Return myself. For compatibility with ``with`` semantics."""
		return self

	def __exit__(self, *args):
		"""Close on exit."""
		self.close()

	def _set_branch(self, v: str) -> None:
		oldrando = self.universal.get('rando_state')
		curbranch = self._get_branch()
		super()._set_branch(v)
		self._turns_completed[v] = self._turns_completed[curbranch]
		newrando = self.universal.get('rando_state')
		if newrando and newrando != oldrando:
			self._rando.setstate(newrando)
		self.time.send(self.time, branch=self._obranch, turn=self._oturn)

	def _set_turn(self, v: int) -> None:
		turn_end = self._branch_end_plan[self.branch]
		if v > turn_end + 1:
			raise exc.OutOfTimelineError(
				f"The turn {v} is after the end of the branch {self.branch}. "
				f"Go to turn {turn_end + 1} and simulate with `next_turn`.",
				self.branch, self.turn, self.tick, self.branch, v, self.tick)
		oldrando = self.universal.get('rando_state')
		oldturn = self._oturn
		super()._set_turn(v)
		newrando = self.universal.get('rando_state')
		if v > oldturn and newrando and newrando != oldrando:
			self._rando.setstate(newrando)
		self.time.send(self.time, branch=self._obranch, turn=self._oturn)

	def _set_tick(self, v: int) -> None:
		tick_end = self._turn_end_plan[self.branch, self.turn]
		if v > tick_end + 1:
			raise exc.OutOfTimelineError(
				f"The tick {v} is after the end of the turn {self.turn}. "
				f"Go to tick {tick_end + 1} and simulate with `next_turn`.",
				self.branch, self.turn, self.tick, self.branch, self.turn, v)
		oldrando = self.universal.get('rando_state')
		oldtick = self._otick
		super()._set_tick(v)
		newrando = self.universal.get('rando_state')
		if v > oldtick and newrando and newrando != oldrando:
			self._rando.setstate(newrando)

	def _handled_char(self, charn: Hashable, rulebook: Hashable,
						rulen: Hashable, branch: str, turn: int,
						tick: int) -> None:
		try:
			self._character_rules_handled_cache.store(charn, rulebook, rulen,
														branch, turn, tick)
		except ValueError:
			assert rulen in self._character_rules_handled_cache.handled[
				charn, rulebook, branch, turn]
			return
		self.query.handled_character_rule(charn, rulebook, rulen, branch, turn,
											tick)

	def _handled_av(self, character: Hashable, graph: Hashable,
					avatar: Hashable, rulebook: Hashable, rule: Hashable,
					branch: str, turn: int, tick: int) -> None:
		try:
			self._unit_rules_handled_cache.store(character, graph, avatar,
													rulebook, rule, branch,
													turn, tick)
		except ValueError:
			assert rule in self._unit_rules_handled_cache.handled[character,
																	graph,
																	avatar,
																	rulebook,
																	branch,
																	turn]
			return
		self.query.handled_unit_rule(character, rulebook, rule, graph, avatar,
										branch, turn, tick)

	def _handled_char_thing(self, character: Hashable, thing: Hashable,
							rulebook: Hashable, rule: Hashable, branch: str,
							turn: int, tick: int) -> None:
		try:
			self._character_thing_rules_handled_cache.store(
				character, thing, rulebook, rule, branch, turn, tick)
		except ValueError:
			assert rule in self._character_thing_rules_handled_cache.handled[
				character, thing, rulebook, branch, turn]
			return
		self.query.handled_character_thing_rule(character, rulebook, rule,
												thing, branch, turn, tick)

	def _handled_char_place(self, character: Hashable, place: Hashable,
							rulebook: Hashable, rule: Hashable, branch: str,
							turn: int, tick: int) -> None:
		try:
			self._character_place_rules_handled_cache.store(
				character, place, rulebook, rule, branch, turn, tick)
		except ValueError:
			assert rule in self._character_place_rules_handled_cache.handled[
				character, place, rulebook, branch, turn]
			return
		self.query.handled_character_place_rule(character, rulebook, rule,
												place, branch, turn, tick)

	def _handled_char_port(self, character: Hashable, orig: Hashable,
							dest: Hashable, rulebook: Hashable, rule: Hashable,
							branch: str, turn: int, tick: int) -> None:
		try:
			self._character_portal_rules_handled_cache.store(
				character, orig, dest, rulebook, rule, branch, turn, tick)
		except ValueError:
			assert rule in self._character_portal_rules_handled_cache.handled[
				character, orig, dest, rulebook, branch, turn]
			return
		self.query.handled_character_portal_rule(character, orig, dest,
													rulebook, rule, branch,
													turn, tick)

	def _handled_node(self, character: Hashable, node: Hashable,
						rulebook: Hashable, rule: Hashable, branch: str,
						turn: int, tick: int) -> None:
		try:
			self._node_rules_handled_cache.store(character, node, rulebook,
													rule, branch, turn, tick)
		except ValueError:
			assert rule in self._node_rules_handled_cache.handled[character,
																	node,
																	rulebook,
																	branch,
																	turn]
			return
		self.query.handled_node_rule(character, node, rulebook, rule, branch,
										turn, tick)

	def _handled_portal(self, character: Hashable, orig: Hashable,
						dest: Hashable, rulebook: Hashable, rule: Hashable,
						branch: str, turn: int, tick: int) -> None:
		try:
			self._portal_rules_handled_cache.store(character, orig, dest,
													rulebook, rule, branch,
													turn, tick)
		except ValueError:
			assert rule in self._portal_rules_handled_cache.handled[character,
																	orig, dest,
																	rulebook,
																	branch,
																	turn]
			return
		self.query.handled_portal_rule(character, orig, dest, rulebook, rule,
										branch, turn, tick)

	def _follow_rules(self):
		# TODO: roll back changes done by rules that raise an exception
		# TODO: if there's a paradox while following some rule,
		#  start a new branch, copying handled rules
		from collections import defaultdict
		branch, turn, tick = self._btt()
		charmap = self.character
		rulemap = self.rule
		todo = defaultdict(list)

		def check_triggers(rule, handled_fun, entity):
			for trigger in rule.triggers:
				res = trigger(entity)
				if res:
					return True
			else:
				handled_fun(self.tick)
				return False

		def check_prereqs(rule, handled_fun, entity):
			if not entity:
				return False
			for prereq in rule.prereqs:
				res = prereq(entity)
				if not res:
					handled_fun(self.tick)
					return False
			return True

		def do_actions(rule, handled_fun, entity):
			actres = []
			for action in rule.actions:
				res = action(entity)
				if res:
					actres.append(res)
				if not entity:
					break
			handled_fun(self.tick)
			return actres

		# TODO: triggers that don't mutate anything should be
		#  evaluated in parallel
		for (charactername, rulebook, rulename
				) in self._character_rules_handled_cache.iter_unhandled_rules(
					branch, turn, tick):
			if charactername not in charmap:
				continue
			self.debug(f"checking triggers for character rule: "
						f"{charactername}, {rulebook}, {rulename}")
			rule = rulemap[rulename]
			handled = partial(self._handled_char, charactername, rulebook,
								rulename, branch, turn)
			entity = charmap[charactername]
			if check_triggers(rule, handled, entity):
				self.debug(f"character rule triggered: "
							f"{charactername}, {rulebook}, {rulename}")
				todo[rulebook].append((rule, handled, entity))
		avcache_retr = self._unitness_cache._base_retrieve
		node_exists = self._node_exists
		get_node = self._get_node
		for (charn, graphn, avn, rulebook,
				rulen) in self._unit_rules_handled_cache.iter_unhandled_rules(
					branch, turn, tick):
			if not node_exists(graphn, avn) or avcache_retr(
				(charn, graphn, avn, branch, turn, tick)) in (KeyError, None):
				continue
			self.debug(f"checking triggers for unit rule: "
						f"{charn, graphn, avn, rulebook, rulen}")
			rule = rulemap[rulen]
			handled = partial(self._handled_av, charn, graphn, avn, rulebook,
								rulen, branch, turn)
			entity = get_node(graphn, avn)
			if check_triggers(rule, handled, entity):
				self.debug(f"unit rule triggered: "
							f"{charn, graphn, avn, rulebook, rulen}")
				todo[rulebook].append((rule, handled, entity))
		is_thing = self._is_thing
		handled_char_thing = self._handled_char_thing
		for (
			charn, thingn, rulebook, rulen
		) in self._character_thing_rules_handled_cache.iter_unhandled_rules(
			branch, turn, tick):
			if not node_exists(charn, thingn) or not is_thing(charn, thingn):
				continue
			self.debug(f"checking triggers for character-thing rule: "
						f"{charn, thingn, rulebook, rulen}")
			rule = rulemap[rulen]
			handled = partial(handled_char_thing, charn, thingn, rulebook,
								rulen, branch, turn)
			entity = get_node(charn, thingn)
			if check_triggers(rule, handled, entity):
				self.debug(f"character-thing rule triggered: "
							f"{charn, thingn, rulebook, rulen}")
				todo[rulebook].append((rule, handled, entity))
		handled_char_place = self._handled_char_place
		for (
			charn, placen, rulebook, rulen
		) in self._character_place_rules_handled_cache.iter_unhandled_rules(
			branch, turn, tick):
			if not node_exists(charn, placen) or is_thing(charn, placen):
				continue
			self.debug(f"checking triggers for character-place rule: "
						f"{charn, placen, rulebook, rulen}")
			rule = rulemap[rulen]
			handled = partial(handled_char_place, charn, placen, rulebook,
								rulen, branch, turn)
			entity = get_node(charn, placen)
			if check_triggers(rule, handled, entity):
				self.debug(f"character-place rule triggered: "
							f"{charn, placen, rulebook, rulen}")
				todo[rulebook].append((rule, handled, entity))
		edge_exists = self._edge_exists
		get_edge = self._get_edge
		handled_char_port = self._handled_char_port
		for (
			charn, orign, destn, rulebook, rulen
		) in self._character_portal_rules_handled_cache.iter_unhandled_rules(
			branch, turn, tick):
			if not edge_exists(charn, orign, destn):
				continue
			self.debug(f"checking triggers for character-portal rule: "
						f"{charn, orign, destn, rulebook, rulen}")
			rule = rulemap[rulen]
			handled = partial(handled_char_port, charn, orign, destn, rulebook,
								rulen, branch, turn)
			entity = get_edge(charn, orign, destn)
			if check_triggers(rule, handled, entity):
				self.debug(f"character-portal rule triggered: "
							f"{charn, orign, destn, rulebook, rulen}")
				todo[rulebook].append((rule, handled, entity))
		handled_node = self._handled_node
		for (charn, noden, rulebook,
				rulen) in self._node_rules_handled_cache.iter_unhandled_rules(
					branch, turn, tick):
			if not node_exists(charn, noden):
				continue
			self.debug(f"checking triggers for node rule: "
						f"{charn, noden, rulebook, rulen}")
			rule = rulemap[rulen]
			handled = partial(handled_node, charn, noden, rulebook, rulen,
								branch, turn)
			entity = get_node(charn, noden)
			if check_triggers(rule, handled, entity):
				self.debug(
					f"node rule triggered: {charn, noden, rulebook, rulen}")
				todo[rulebook].append((rule, handled, entity))
		handled_portal = self._handled_portal
		for (
			charn, orign, destn, rulebook,
			rulen) in self._portal_rules_handled_cache.iter_unhandled_rules(
				branch, turn, tick):
			if not edge_exists(charn, orign, destn):
				continue
			self.debug(f"checking triggers for portal rule: "
						f"{charn, orign, destn, rulebook, rulen}")
			rule = rulemap[rulen]
			handled = partial(handled_portal, charn, orign, destn, rulebook,
								rulen, branch, turn)
			entity = get_edge(charn, orign, destn)
			if check_triggers(rule, handled, entity):
				self.debug(f"portal rule triggered: "
							f"{charn, orign, destn, rulebook, rulen}")
				todo[rulebook].append((rule, handled, entity))

		# TODO: rulebook priorities (not individual rule priorities, just follow the order of the rulebook)
		def fmtent(entity):
			if isinstance(entity, self.char_cls):
				return entity.name
			elif hasattr(entity, 'name'):
				return f"{entity.character.name}.node[{entity.name}]"
			else:
				return (f"{entity.character.name}.portal"
						f"[{entity.origin.name}][{entity.destination.name}]")

		for rulebook in sort_set(todo.keys()):
			for rule, handled, entity in todo[rulebook]:
				if not entity:
					continue
				self.debug(
					f"checking prereqs for rule {rule} on entity {fmtent(entity)}"
				)
				if check_prereqs(rule, handled, entity):
					self.debug(
						f"prereqs for rule {rule} on entity "
						f"{fmtent(entity)} satisfied, will run actions")
					try:
						yield do_actions(rule, handled, entity)
						self.debug(
							f"actions for rule {rule} on entity "
							f"{fmtent(entity)} have run without incident")
					except StopIteration:
						raise InnerStopIteration

	def advance(self) -> Any:
		"""Follow the next rule if available.

		If we've run out of rules, reset the rules iterator.

		"""
		assert self.turn > self._turns_completed[self.branch]
		try:
			return next(self._rules_iter)
		except InnerStopIteration:
			self._rules_iter = self._follow_rules()
			return StopIteration()
		except StopIteration:
			self._rules_iter = self._follow_rules()
			return final_rule

	# except Exception as ex:
	#	 self._rules_iter = self._follow_rules()
	#	 return ex

	def new_character(self,
						name: Hashable,
						data: Graph = None,
						**kwargs) -> Character:
		"""Create and return a new :class:`Character`."""
		self.add_character(name, data, **kwargs)
		return self.character[name]

	new_graph = new_character

	def add_character(self,
						name: Hashable,
						data: Graph = None,
						**kwargs) -> None:
		"""Create a new character.

		You'll be able to access it as a :class:`Character` object by
		looking up ``name`` in my ``character`` property.

		``data``, if provided, should be a networkx-compatible graph
		object. Your new character will be a copy of it.

		Any keyword arguments will be set as stats of the new character.

		"""
		self._init_graph(name, 'DiGraph', data)
		self._graph_objs[name] = graph_obj = self.char_cls(self, name)
		if kwargs:
			graph_obj.stat.update(kwargs)

	def del_character(self, name: Hashable) -> None:
		"""Remove the Character from the database entirely.

		This also deletes all its history. You'd better be sure.

		"""
		self.query.del_character(name)
		self.del_graph(name)
		del self.character[name]

	def _is_thing(self, character: Hashable, node: Hashable) -> bool:
		return self._things_cache.contains_entity(character, node,
													*self._btt())

	def _set_thing_loc(self, character: Hashable, node: Hashable,
						loc: Hashable) -> None:
		branch, turn, tick = self._nbtt()
		self._things_cache.store(character, node, branch, turn, tick, loc)
		self.query.set_thing_loc(character, node, branch, turn, tick, loc)

	def _snap_keyframe(self, graph: Hashable, branch: str, turn: int,
						tick: int, nodes: NodeValDictType,
						edges: EdgeValDictType,
						graph_val: StatDictType) -> None:
		super()._snap_keyframe(graph, branch, turn, tick, nodes, edges,
								graph_val)
		newkf = {}
		contkf = {}
		for (name, node) in nodes.items():
			if 'location' not in node:
				continue
			locn = node['location']
			newkf[name] = locn
			if locn in contkf:
				contkf[locn].add(name)
			else:
				contkf[locn] = {
					name,
				}
		contents_keyframes = self._node_contents_cache.keyframe
		contkfs = contents_keyframes[graph, ][branch]
		if turn not in contkfs:
			contkfs[turn] = {tick: contkf}
		else:
			contkfs[turn][tick] = contkf
		kfs = self._things_cache.keyframe[graph, ][branch]
		if turn not in kfs:
			kfs[turn] = {tick: newkf}
		else:
			kfs[turn][tick] = newkf

	def turns_when(self,
					qry: Query,
					mid_turn=False) -> Union[QueryResult, set]:
		"""Return the turns when the query held true

		Only the state of the world at the end of the turn is considered.
		To include turns where the query held true at some tick, but
		became false, set ``mid_turn=True``

		:arg qry: a Query, likely constructed by comparing the result
				  of a call to an entity's ``historical`` method with
				  the output of ``self.alias(..)`` or another
				  ``historical(..)``

		"""
		unpack = self.unpack
		end = self._branch_end_plan[self.branch] + 1

		def unpack_gt_lt_data(data):
			return [((lfrom, lto), (rfrom, rto), unpack(v))
					for (lfrom, lto, rfrom, rto, v) in data]

		if not isinstance(qry, ComparisonQuery):
			if not isinstance(qry, CompoundQuery):
				raise TypeError("Unsupported query type: " + repr(type(qry)))
			return CombinedQueryResult(
				self.turns_when(qry.leftside, mid_turn),
				self.turns_when(qry.rightside, mid_turn), qry.oper)
		self.query.flush()
		branches = list({branch for branch, _, _ in self._iter_parent_btt()})
		if not isinstance(qry, EqQuery) and not isinstance(qry, NeQuery):
			left = qry.leftside
			right = qry.rightside
			if isinstance(left, StatusAlias) and isinstance(
				right, StatusAlias):
				left_sel = make_side_sel(left.entity, left.stat, branches,
											self.pack, mid_turn)
				right_sel = make_side_sel(right.entity, right.stat, branches,
											self.pack, mid_turn)
				left_data = self.query.execute(left_sel)
				right_data = self.query.execute(right_sel)
				if mid_turn:
					return GtLtQueryResultMidTurn(
						unpack_gt_lt_data(left_data),
						unpack_gt_lt_data(right_data), qry.oper, end)
				else:
					return GtLtQueryResultEndTurn(
						unpack_gt_lt_data(left_data),
						unpack_gt_lt_data(right_data), qry.oper, end)
			elif isinstance(left, StatusAlias):
				left_sel = make_side_sel(left.entity, left.stat, branches,
											self.pack, mid_turn)
				left_data = self.query.execute(left_sel)
				_, turn, tick = self._btt()
				if mid_turn:
					return GtLtQueryResultMidTurn(
						left_data, [(0, 0, turn, tick, right)], qry.oper, end)
				else:
					return GtLtQueryResultEndTurn(left_data, [(0, 0, right)],
													qry.oper, end)
			elif isinstance(right, StatusAlias):
				right_sel = make_side_sel(right.entity, right.stat, branches,
											self.pack, mid_turn)
				right_data = self.query.execute(right_sel)
				_, turn, tick = self._btt()
				if mid_turn:
					return GtLtQueryResultMidTurn([(0, 0, turn, tick, left)],
													right_data, qry.oper, end)
				else:
					return GtLtQueryResultEndTurn([(0, 0, left)], [
						(turn_from, turn_to, value)
						for (turn_from, _, turn_to, _, value) in right_data
					], qry.oper, end)
			else:
				if qry.oper(left, right):
					return set(range(0, self.turn))
				else:
					return set()
		# Make a select statement that gets the turns when the predicate held true
		try:
			sel = make_select_from_eq_query(qry, list(branches), self.pack,
											mid_turn)
			res = []

			def upd(turn_from, turn_to):
				assert turn_from is not None
				if turn_to is None:
					res.append((turn_from, end))
				else:
					res.append((turn_from, turn_to))

			tups = self.query.execute(sel)
			for tup in tups:
				if len(tup) == 8:
					(left_turn_from, left_tick_from, left_turn_to,
						left_tick_to, right_turn_from, right_tick_from,
						right_turn_to, right_tick_to) = tup
					for turn_from, turn_to in windows_intersection([
						(left_turn_from, left_turn_to),
						(right_turn_from, right_turn_to)
					]):
						upd(turn_from, turn_to)
				elif len(tup) == 4:
					(left_turn_from, left_turn_to, right_turn_from,
						right_turn_to) = tup
					for turn_from, turn_to in windows_intersection([
						(left_turn_from, left_turn_to),
						(right_turn_from, right_turn_to)
					]):
						upd(turn_from, turn_to)
				elif len(tup) == 2:
					upd(*tup)
				else:
					raise RuntimeError("make_select_from_query went bad")
			return EqNeQueryResultEndTurn(res)
		except NotImplementedError:
			if mid_turn:
				raise NotImplementedError("Can't do mid_turn this way yet")
			return {turn for (branch, turn) in qry.iter_times()}

	def _node_contents(self, character: Hashable, node: Hashable) -> Set:
		return self._node_contents_cache.retrieve(character, node,
													*self._btt())

	def apply_choices(
		self,
		choices: List[dict],
		dry_run=False,
		perfectionist=False
	) -> Tuple[List[Tuple[Any, Any]], List[Tuple[Any, Any]]]:
		"""Validate changes a player wants to make, and apply if acceptable.

		Returns a pair of lists containing acceptance and rejection messages,
		which the UI may present as it sees fit. They are always in a pair
		with the change request as the zeroth item. The message may be None
		or a string.

		Validator functions may return only a boolean indicating acceptance.
		If they instead return a pair, the initial boolean indicates
		acceptance and the following item is the message.

		This function will not actually result in any simulation happening.
		It creates a plan. See my ``plan`` context manager for the precise
		meaning of this.

		With ``dry_run=True`` just return the acceptances and rejections
		without really planning anything. With ``perfectionist=True`` apply
		changes if and only if all of them are accepted.

		"""
		schema = self.schema
		todo = defaultdict(list)
		acceptances = []
		rejections = []
		for track in choices:
			entity = track['entity']
			permissible = schema.entity_permitted(entity)
			if isinstance(permissible, tuple):
				permissible, msg = permissible
			else:
				msg = ''
			if not permissible:
				for turn, changes in enumerate(track['changes'],
												start=self.turn):
					rejections.extend(
						((turn, entity, k, v), msg) for (k, v) in changes)
				continue
			for turn, changes in enumerate(track['changes'], start=self.turn):
				for k, v in changes:
					ekv = (entity, k, v)
					parcel = (turn, entity, k, v)
					val = schema.stat_permitted(*parcel)
					if type(val) is tuple:
						accept, message = val
						if accept:
							todo[turn].append(ekv)
							l = acceptances
						else:
							l = rejections
						l.append((parcel, message))
					elif val:
						todo[turn].append(ekv)
						acceptances.append((parcel, None))
					else:
						rejections.append((parcel, None))
		if dry_run or (perfectionist and rejections):
			return acceptances, rejections
		now = self.turn
		with self.plan():
			for turn in sorted(todo):
				self.turn = turn
				for entity, key, value in todo[turn]:
					if isinstance(entity, self.char_cls):
						entity.stat[key] = value
					else:
						entity[key] = value
		self.turn = now
		return acceptances, rejections
