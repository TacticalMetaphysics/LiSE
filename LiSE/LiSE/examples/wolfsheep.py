import random
import networkx as nx

from LiSE import Engine


def install(eng: Engine, map_size=(100, 100), wolves=10, sheep=10, seed=None):
	if seed is not None:
		random.seed(seed)
	bare_places = []
	proto: nx.Graph = nx.grid_2d_graph(*map_size)
	for node_name, node in proto.nodes.items():
		node['bare'] = random.choice([True, False])
		node['_image_paths'] = [
			'atlas://rltiles/floor/' +
			('floor-normal' if node['bare'] else 'floor-moss')
		]
		if node['bare']:
			bare_places.append(node_name)
	phys = eng.new_character('physical', proto)
	phys.stat['bare_places'] = bare_places
	wolfs = eng.new_character('wolf')
	sheeps = eng.new_character('sheep')
	unoccupied = [(x, y) for x in range(map_size[0])
					for y in range(map_size[0])]
	random.shuffle(unoccupied)
	for i in range(wolves):
		loc = phys.place[unoccupied.pop()]
		wolf = loc.new_thing(
			f'wolf{i}', _image_paths=['atlas://rltiles/dc-mon/war_dog'])
		wolfs.add_unit(wolf)
		print('wolf', i)
	for i in range(sheep):
		loc = phys.place[unoccupied.pop()]
		shep = loc.new_thing(f'sheep{i}',
								_image_paths=['atlas://rltiles/dc-mon/sheep'])
		sheeps.add_unit(shep)
		print('sheep', i)

	@phys.rule(always=True)
	def grow(chara):
		bare_places = chara.stat['bare_places']
		i = chara.engine.randrange(0, len(bare_places))
		there = chara.place[bare_places.pop(i)]
		there['bare'] = False
		there['_image_paths'] = ['atlas://rltiles/floor/floor-moss']

	@sheeps.unit.rule
	def graze(shep):
		shep.location['bare'] = True
		shep.engine.character['physical'].stat['bare_places'].append(
			shep['location'])
		shep.location['_image_paths'] = ['atlas://rltiles/floor/floor-normal']

	@graze.trigger
	def grass_here(shep):
		return not shep.location['bare']

	@sheeps.unit.rule(always=True)
	def wander(shep):
		here = shep.location
		x, y = here.name
		physical = shep.engine.character['physical']
		neighbors = list(
			filter(lambda b: b in physical.place, [(x + 1, y), (x - 1, y),
													(x, y + 1), (x, y - 1)]))
		for neighbor in neighbors:
			neighbor = physical.place[neighbor]
			if not neighbor['bare']:
				shep.location = neighbor
				return
		shep.location = shep.engine.choice(neighbors)

	@wolfs.unit.rule(always=True)
	def pursue_sheep(wolff):
		import numpy as np
		# find the sheep that's nearest
		sheep_locs = [
			sheep['location']
			for sheep in wolff.engine.character['sheep'].units()
		]
		my_loc = wolff['location']
		if len(sheep_locs) == 1:
			nearest = sheep_locs[0]
		else:
			sheep_locs = np.array(sheep_locs)
			dists = np.linalg.norm((sheep_locs - my_loc), axis=1)
			nearest = tuple(sheep_locs[dists.argmin()])
		if my_loc == nearest:  # om nom nom
			sheepch = wolff.engine.character['sheep']
			n_del = 0
			for the_sheep in wolff.location.contents():
				if the_sheep.user.only is sheepch:
					the_sheep.delete()
					n_del += 1
			assert n_del
			return
		# take a step closer
		if nearest[0] > my_loc[0]:
			wolff['location'] = (my_loc[0] + 1, my_loc[1])
		elif nearest[0] < my_loc[0]:
			wolff['location'] = (my_loc[0] - 1, my_loc[1])
		elif nearest[1] > my_loc[1]:
			wolff['location'] = (my_loc[0], my_loc[1] + 1)
		else:
			assert nearest[1] < my_loc[1]
			wolff['location'] = (my_loc[0], my_loc[1] - 1)

	@pursue_sheep.prereq
	def sheep_remains(wolff):
		return bool(wolff.engine.character['sheep'].unit)


if __name__ == '__main__':
	import sys

	args = []
	kwargs = {}
	if len(sys.argv) == 3:
		kwargs['random_seed'] = sys.argv[-1]
		args.append(sys.argv[-2])
	elif len(sys.argv) == 2:
		args.append(sys.argv[-1])
	else:
		kwargs['connect_string'] = 'sqlite:///:memory:'
	with Engine(*args, **kwargs) as engn:
		install(engn)
