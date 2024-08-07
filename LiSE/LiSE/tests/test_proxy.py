# This file is part of LiSE, a framework for life simulation games.
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
from unittest.mock import patch, MagicMock

import networkx as nx

from LiSE.engine import Engine
from LiSE.proxy import EngineProcessManager
from LiSE.handle import EngineHandle
import LiSE.allegedb.tests.test_all
from LiSE.tests import data
import pytest
import LiSE.examples.kobold as kobold
import LiSE.examples.college as college
import shutil
import tempfile
import msgpack


class ProxyTest(LiSE.allegedb.tests.test_all.AllegedTest):
	def setUp(self):
		self.manager = EngineProcessManager()
		self.tempdir = tempfile.mkdtemp(dir=".")
		self.engine = self.manager.start(
			self.tempdir,
			connect_string="sqlite:///:memory:",
			enforce_end_of_time=False,
		)
		self.graphmakers = (self.engine.new_character,)
		self.addCleanup(self._do_cleanup)

	def _do_cleanup(self):
		self.manager.shutdown()
		shutil.rmtree(self.tempdir)


@pytest.mark.test_proxy_graph_objects_create_delete
class ProxyGraphTest(
	LiSE.allegedb.tests.test_all.AbstractGraphTest, ProxyTest
):
	pass


class DictStorageTest(ProxyTest, LiSE.allegedb.tests.test_all.DictStorageTest):
	pass


class ListStorageTest(ProxyTest, LiSE.allegedb.tests.test_all.ListStorageTest):
	pass


class SetStorageTest(ProxyTest, LiSE.allegedb.tests.test_all.SetStorageTest):
	pass


@pytest.fixture(scope="function")
def handle(tempdir):
	from LiSE.handle import EngineHandle

	hand = EngineHandle(
		(tempdir,),
		{"connect_string": "sqlite:///:memory:", "random_seed": 69105},
	)
	yield hand
	hand.close()


@pytest.fixture(
	scope="function",
	params=[
		lambda eng: kobold.inittest(
			eng, shrubberies=20, kobold_sprint_chance=0.9
		),
		# college.install,
		# sickle.install
	],
)
def handle_initialized(request, handle):
	with handle._real.advancing():
		request.param(handle._real)
	yield handle


def test_fast_delta(handle_initialized):
	hand = handle_initialized

	# there's currently no way to do fast delta past the time when
	# a character was created, due to the way keyframes work...
	# so don't test that
	def unpack_delta(d):
		catted = hand._concat_char_delta(d)
		assert isinstance(catted, bytes)
		return hand.unpack(catted)

	branch, turn, tick = hand._real._btt()
	ret, diff = hand.next_turn()
	btt = hand._real._btt()
	slowd = unpack_delta(
		hand._get_slow_delta(btt_from=(branch, turn, tick), btt_to=btt)
	)
	assert hand.unpack(diff) == slowd, "Fast delta differs from slow delta"
	ret, diff2 = hand.time_travel("trunk", 0, tick)
	btt2 = hand._real._btt()
	slowd2 = unpack_delta(hand._get_slow_delta(btt_from=btt, btt_to=btt2))
	assert hand.unpack(diff2) == slowd2, "Fast delta differs from slow delta"
	ret, diff4 = hand.time_travel("trunk", 1)
	btt4 = hand._real._btt()
	slowd4 = unpack_delta(hand._get_slow_delta(btt_from=btt2, btt_to=btt4))
	assert hand.unpack(diff4) == slowd4, "Fast delta differs from slow delta"


@pytest.mark.slow
def test_serialize_deleted(engy):
	eng = engy
	with eng.advancing():
		college.install(eng)
	d0r0s0 = eng.character["dorm0room0student0"]
	roommate = d0r0s0.stat["roommate"]
	del eng.character[roommate.name]
	assert not roommate
	with pytest.raises(KeyError):
		eng.character[roommate.name]
	assert d0r0s0.stat["roommate"] == roommate
	assert eng.unpack(eng.pack(d0r0s0.stat["roommate"])) == roommate


def test_manip_deleted(engy):
	eng = engy
	phys = eng.new_character("physical")
	phys.stat["aoeu"] = True
	phys.add_node(0)
	phys.add_node(1)
	phys.node[1]["aoeu"] = True
	del phys.node[1]
	phys.add_node(1)
	assert "aoeu" not in phys.node[1]
	phys.add_edge(0, 1)
	phys.adj[0][1]["aoeu"] = True
	del phys.adj[0][1]
	phys.add_edge(0, 1)
	assert "aoeu" not in phys.adj[0][1]
	del eng.character["physical"]
	assert not phys
	phys = eng.new_character("physical")
	assert "aoeu" not in phys.stat
	assert 0 not in phys
	assert 1 not in phys
	assert 0 not in phys.adj
	assert 1 not in phys.adj


class TestSwitchMainBranch(ProxyTest):
	def test_switch_main_branch(self):
		phys = self.engine.new_character("physical", hello="hi")
		self.engine.next_turn()
		phys.stat["hi"] = "hello"
		with pytest.raises(ValueError):
			self.engine.switch_main_branch("tronc")
		self.engine.turn = 0
		self.engine.tick = 0
		self.engine.switch_main_branch("tronc")
		assert self.engine.branch == "tronc"
		assert "hello" not in phys.stat
		self.engine.next_turn()
		phys.stat["hi"] = "hey there"
		self.engine.turn = 0
		self.engine.tick = 0
		self.engine.switch_main_branch("trunk")
		assert phys.stat["hello"] == "hi"
		self.engine.turn = 1
		assert phys.stat["hello"] == "hi"
		assert phys.stat["hi"] == "hello"


def test_updnoderb(handle):
	engine = handle._real
	char0 = engine.new_character("0")
	node0 = char0.new_place("0")

	@node0.rule(always=True)
	def change_rulebook(node):
		node.rulebook = "haha"

	a, b = handle.next_turn()

	delta = engine.unpack(b)

	assert (
		"0" in delta
		and "node_val" in delta["0"]
		and "0" in delta["0"]["node_val"]
		and "0" in delta["0"]["node_val"]
		and "rulebook" in delta["0"]["node_val"]["0"]
		and delta["0"]["node_val"]["0"]["rulebook"] == "haha"
	)


def test_updedgerb(handle):
	engine = handle._real
	char0 = engine.new_character("0")
	node0 = char0.new_place("0")
	node1 = char0.new_place("1")
	edge = node0.new_portal(node1)

	@edge.rule(always=True)
	def change_rulebook(edge):
		edge.rulebook = "haha"

	a, b = handle.next_turn()

	delta = engine.unpack(b)

	assert (
		"0" in delta
		and "edge_val" in delta["0"]
		and "0" in delta["0"]["edge_val"]
		and "1" in delta["0"]["edge_val"]["0"]
		and "rulebook" in delta["0"]["edge_val"]["0"]["1"]
		and delta["0"]["edge_val"]["0"]["1"]["rulebook"] == "haha"
	)


def test_thing_place_iter():
	# set up some world state with things and places, before starting the proxy
	with tempfile.TemporaryDirectory() as tempdir:
		with LiSE.Engine(tempdir) as eng:
			kobold.inittest(eng)
		manager = EngineProcessManager()
		engine = manager.start(tempdir)
		phys = engine.character["physical"]
		for place_name in phys.place:
			assert isinstance(place_name, tuple)
		for thing_name in phys.thing:
			assert isinstance(thing_name, str)
		manager.shutdown()


@patch("LiSE.handle.Engine")
def test_get_slow_delta_overload(eng: MagicMock):
	hand = EngineHandle()
	eng = hand._real
	eng.pack = msgpack.packb
	eng.branch, eng.turn, eng.tick = data.BTT_FROM
	eng._btt.return_value = data.BTT_FROM
	eng._get_kf.side_effect = [data.KF_FROM, data.KF_TO]
	slowd = hand._get_slow_delta(data.BTT_FROM, data.BTT_TO)
	assert slowd == data.SLOW_DELTA


@pytest.mark.parametrize("slow", [True, False])
def test_apply_delta(tempdir, slow):
	with Engine(tempdir) as eng:
		initial_state = nx.DiGraph(
			{
				0: {1: {"omg": "lol"}},
				1: {0: {"omg": "blasphemy"}},
				2: {},
				3: {},
				"it": {},
			}
		)
		initial_state.nodes()[2]["hi"] = "hello"
		initial_state.nodes()["it"]["location"] = 0
		initial_state.graph["wat"] = "nope"
		phys = eng.new_character("physical", initial_state)
		eng.add_character("pointless")
		if slow:
			eng.branch = "b"
		else:
			eng.next_turn()
		del phys.portal[1][0]
		port = phys.new_portal(0, 2)
		port["hi"] = "bye"
		phys.place[1]["wtf"] = "bbq"
		phys.thing["it"].location = phys.place[1]
		del phys.place[3]
		eng.add_character("pointed")
		del eng.character["pointless"]
		assert "pointless" not in eng.character, "Failed to delete character"
		phys.portal[0][1]["meaning"] = 42
		del phys.portal[0][1]["omg"]
		if slow:
			eng.branch = "trunk"
		else:
			eng.turn = 0
			eng.tick = 0
	mang = EngineProcessManager()
	try:
		prox = mang.start(tempdir)
		assert prox.turn == 0
		phys = prox.character["physical"]
		assert 3 in phys.place
		assert phys.portal[1][0]["omg"] == "blasphemy"
		if slow:
			prox.branch = "b"
		else:
			prox.turn = 1
		assert 3 not in phys.place
		assert 0 not in phys.portal[1]
		assert 2 in phys.portal[0]
		assert phys.portal[0][2]["hi"] == "bye"
		assert phys.place[1]["wtf"] == "bbq"
		assert phys.thing["it"].location == phys.place[1]
		assert "pointless" not in prox.character, "Loaded deleted character"
		assert "pointed" in prox.character
		assert phys.portal[0][1]["meaning"] == 42
		assert "omg" not in phys.portal[0][1]
	finally:
		mang.shutdown()
