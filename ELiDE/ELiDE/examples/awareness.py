from tempfile import mkdtemp
from multiprocessing import freeze_support
from inspect import getsource

from kivy.clock import Clock
from kivy.lang.builder import Builder
from kivy.properties import BooleanProperty, NumericProperty

from ELiDE.game import GameApp, GameScreen, GridBoard


def game_start(engine, random_seed=69105) -> None:
	from random import Random
	import networkx as nx

	@engine.function
	def remove_prefix(s: str, prefix: str):
		"""py3.8 compat"""
		if s.startswith(prefix):
			return s[len(prefix) :]
		return s

	rand = Random()
	if random_seed is not None:
		rand.seed(random_seed)
	rand.setstate(engine.universal.setdefault("rando_state", rand.getstate()))

	# ensure we're on a fresh branch
	if engine.turn != 0 or engine.tick != 0:
		if engine.branch == "trunk":
			new_branch_name = "trunk0"
		else:
			new_branch_num = int(engine.branch[5:])
			new_branch_name = "trunk" + str(new_branch_num)
		engine.turn = 0
		engine.tick = 0
		engine.switch_main_branch(new_branch_name)

	engine.eternal["nonusage-limit"] = 100
	wide = engine.eternal.setdefault("max-pxcor", 36)
	high = engine.eternal.setdefault("max-pycor", 37)
	initworld = nx.grid_2d_graph(wide, high)
	# world wraps vertically
	for x in range(wide):
		initworld.add_edge((x, high - 1), (x, 0))
	# world wraps horizontally
	for y in range(high):
		initworld.add_edge((wide - 1, y), (0, y))

	locs = list(initworld.nodes.keys())
	rand.shuffle(locs)

	for turtle in range(engine.eternal.setdefault("people", 60)):
		initworld.add_node(
			"turtle" + str(turtle),
			awareness=0,
			facing=randint(0, 3),
			location=locs.pop(),
			_image_paths=[
				"atlas://rltiles/base/unseen",
				"atlas://rltiles/body/robe_black",
			],
		)

	for center in range(engine.eternal.setdefault("centers", 20)):
		initworld.add_node(
			"center" + str(center),
			location=locs.pop(),
			nonusage=0,
			_image_paths=["atlas://rltiles/dungeon/dngn_altar_xom"],
		)

	phys = engine.new_character("physical", initworld)
	peep = engine.new_character("people")
	lit = engine.new_character("literature")
	# there really ought to be a way to specify a character's units in its starting data
	for node in phys.thing.values():
		if node.name.startswith("turtle"):
			peep.add_unit(node)
		elif node.name.startswith("center"):
			lit.add_unit(node)

	@peep.unit.rule(always=True)
	def wander(person):
		x, y = person.location.name
		if person["facing"] == 0:
			y += 1
		elif person["facing"] == 1:
			x += 1
		elif person["facing"] == 2:
			y -= 1
		elif person["facing"] == 3:
			x -= 1
		x %= person.engine.eternal["max-pxcor"]
		y %= person.engine.eternal["max-pycor"]
		person["location"] = (x, y)
		person["facing"] = (
			person["facing"]
			+ person.engine.randint(0, 1)
			- person.engine.randint(0, 1)
		)

	@engine.function
	def has_literature(person):
		for contained in person.location.contents():
			if contained.name.startswith("flyer") or contained.name.startswith(
				"center"
			):
				return True
		return False

	@peep.unit.rule
	def learn(person):
		person["awareness"] = (person["awareness"] + 1) % 15
		if person["awareness"] < 5:
			image_paths = [
				"atlas://rltiles/base/unseen",
				"atlas://rltiles/body/robe_black",
			]
		elif person["awareness"] < 10:
			image_paths = [
				"atlas://rltiles/base/unseen",
				"atlas://rltiles/body/robe_green",
			]
		elif person["awareness"] < 15:
			image_paths = [
				"atlas://rltiles/base/unseen",
				"atlas://rltiles/body/robe_white_green",
			]
		else:
			image_paths = [
				"atlas://rltiles/base/unseen",
				"atlas://rltiles/body/robe_green_gold",
			]
		if person["_image_paths"] != image_paths:
			person["_image_paths"] = image_paths
		person["last_learned"] = person.engine.turn
		for contained in person.location.contents():
			if contained.name.startswith("flyer") or contained.name.startswith(
				"center"
			):
				contained["last_read"] = person.engine.turn

	# this would be more pleasant as something like a partial
	@learn.trigger
	def literature_here(person):
		return person.engine.function.has_literature(person)

	@peep.unit.rule
	def unlearn(person):
		person["awareness"] = max((person["awareness"] - 1, 0))

	@unlearn.trigger
	def no_literature_here(person):
		return not person.engine.function.has_literature(person)

	@peep.unit.rule
	def write(person):
		lit_ = person.engine.character["literature"]
		maxnum = 0
		for unit in lit_.units():
			if unit.name.startswith("flyer"):
				maxnum = max(
					(
						int(engine.function.remove_prefix(unit.name, "flyer")),
						maxnum,
					)
				)
		scroll = person.location.new_thing(
			f"flyer{maxnum:02}",
			nonusage=0,
			_image_paths=["atlas://rltiles/scroll/scroll-0"],
		)
		lit_.add_unit(scroll)

	@write.trigger
	def activist(person):
		return person["awareness"] >= 15

	@peep.unit.rule
	def preach(person):
		for that in person.location.contents():
			if that != person and that.name.startswith("turtle"):
				that["awareness"] = (that["awareness"] + 1) % 15

	@preach.trigger
	def well_informed(person):
		return person["awareness"] >= 10

	@lit.unit.rule
	def disappear(ctr):
		ctr.delete()

	@disappear.trigger
	def unused(ctr):
		return (
			ctr.get("last_read", ctr.engine.turn) - ctr.engine.turn
			> ctr.engine.eternal["nonusage-limit"]
		)

	engine.universal.setdefault("rando_state", rand.getstate())


class AwarenessGridBoard(GridBoard):
	def on_selection(self, *args):
		def remove_prefix(s: str, pre: str) -> str:
			if s.startswith(pre):
				return s[len(pre) :]
			return s

		if not GameApp.get_running_app().placing_centers or not isinstance(
			self.selection, self.spot_cls
		):
			return
		prox = self.selection.proxy
		for contained in prox.contents():
			if contained.name.startswith("center"):
				return
		name = f"""center{max(
			int(remove_prefix(name,'center')) for name in self.character.thing.keys()
			if isinstance(name, str) and name.startswith('center')) + 1}"""
		prox.add_thing(
			name,
			nonusage=0,
			_image_paths=["atlas://rltiles/dungeon/dngn_altar_xom"],
		)


class MainGame(GameScreen):
	def on_parent(self, *args):
		if "game" not in self.ids:
			Clock.schedule_once(self.on_parent, 0)
			return
		self.set_up()
		self.ids.game.board = AwarenessGridBoard(
			character=self.engine.character["physical"]
		)
		AwarenessApp.get_running_app().bind(turn=self._get_turn)

	def _get_turn(self, *args):
		app = AwarenessApp.get_running_app()
		if app.turn > app.end_turn:
			app.end_turn = app.turn
		self.ids.timeslider.value = app.turn

	def set_up(self):
		"""Regenerate the whole map"""

		def remove_prefix(s: str, prefix: str):
			"""py3.8 compat"""
			if s.startswith(prefix):
				return s[len(prefix) :]
			return s

		branch = self.engine.branch
		try:
			branchidx = int(remove_prefix(branch, "branch")) + 1
			branch = f"branch{branchidx:02}"
		except ValueError:
			branch = f"branch01"
		self.engine.turn = 0
		self.engine.tick = 0
		self.engine.switch_main_branch(branch)
		if hasattr(self, "ran_once"):
			self.engine.eternal["people"] = int(self.ids.people.value)
			self.engine.eternal["centers"] = int(self.ids.centers.value)
			self.engine.eternal["nonusage-limit"] = int(
				self.ids.nonusage.value
			)
		self.engine.game_start()
		app = GameApp.get_running_app()
		self._push_character()
		if not hasattr(self, "ran_once"):
			self.ids.people.value = app.engine.eternal.setdefault(
				"people", 100
			)
			self.ids.centers.value = app.engine.eternal.setdefault(
				"centers", 60
			)
			self.ids.nonusage.value = app.engine.eternal.setdefault(
				"nonusage-limit", 10
			)
			self.ran_once = True

	def _push_character(self, *args):
		board = self.ids.game.board
		if not board:
			Clock.schedule_once(self._push_character, 0)
			return
		board.character.thing.disconnect(board.update_from_thing)
		phys = AwarenessApp.get_running_app().engine.character["physical"]
		board.character = phys
		board.update()
		phys.thing.connect(board.update_from_thing)


class AwarenessApp(GameApp):
	play = BooleanProperty(False)
	placing_centers = BooleanProperty(False)
	end_turn = NumericProperty(0)
	inspector = True

	def on_play(self, *args):
		if self.play:
			Clock.schedule_interval(self.next_turn, self.turn_length)
			self._scheduled_next_turn = True
		elif hasattr(self, "_scheduled_next_turn"):
			Clock.unschedule(self.next_turn)
			del self._scheduled_next_turn

	def on_turn(self, *args):
		turn = int(self.turn)
		if turn != self.engine.turn:
			self.engine.turn = turn


kv = """
# kv_start
<ScreenManager>:
	MainGame:
		name: 'play'
<MainGame>:
	BoxLayout:
		orientation: 'vertical'
		BoxLayout:
			orientation: 'horizontal'
			BoxLayout:
				id: sidebar
				orientation: 'vertical'
				width: 333
				size_hint_x: None
				BoxLayout:
					id: controls
					orientation: 'vertical'
					size_hint_y: 0.3
					BoxLayout:
						id: toprow
						Button:
							id: setup
							text: 'setup'
							on_release: root.set_up()
						Slider:
							id: people
							min: 0
							max: 300
							step: 1
							Label:
								text: 'people'
								x: people.x
								y: people.y
								size: self.texture_size
								size_hint: None, None
							Label:
								text: str(int(people.value))
								x: people.right - self.texture_size[0]
								y: people.y
								size: self.texture_size
								size_hint: None, None
						ToggleButton:
							text: 'place centers'
							on_release: app.placing_centers = self.state == 'down'
					BoxLayout:
						id: midrow	
						ToggleButton:
							id: play
							text: 'Go'
							on_state: app.play = self.state == 'down'
						Slider:
							id: centers
							min: 0
							max: 100
							step: 1
							Label:
								text: 'centers'
								size: self.texture_size
								pos: self.parent.pos
							Label:
								text: str(int(self.parent.value))
								size: self.texture_size
								center_x: self.parent.center_x
								y: self.parent.y
						Widget:
							id: filler0
					Slider:
						id: nonusage
						min: 0
						max: 500
						step: 1
						Label:
							text: 'non-usage limit'
							size: self.texture_size
							pos: nonusage.pos
						Label:
							text: '{:d} ticks'.format(int(nonusage.value))
							size: self.texture_size
							x: nonusage.right - self.texture_size[0]
							y: nonusage.y
				Widget:
					id: filler
			Widget:
				id: gamebox
				size_hint_x: 0.7
				GridBoardView:
					id: game		
					pos: gamebox.pos
					size: gamebox.size
		Slider:
			id: timeslider
			x: 0
			y: 0
			height: 50
			size_hint_y: None
			min: 0
			max: app.end_turn
			step: 1
			on_value: app.turn = self.value
# kv_end
"""

Builder.load_string(kv)

if __name__ == "__main__":
	freeze_support()
	d = mkdtemp()
	with open(d + "/game_start.py", "w", encoding="utf-8") as outf:
		outf.write(getsource(game_start))
	AwarenessApp(prefix=d).run()
	print("Files are in " + d)
