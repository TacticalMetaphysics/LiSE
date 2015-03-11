from collections import (
    Callable,
    defaultdict,
    Mapping,
    MutableMapping,
    MutableSequence
)
import os
from multiprocessing import Process, Queue, Lock
from multiprocessing.managers import BaseManager
from .core import Engine
from .character import Facade
from .util import dispatch, listen, listener


class EngineHandle(object):
    def reify(self, args, queue):
        self._real = Engine(*args)
        self._remote = queue.get()

    def listen_to_character(self, char):
        char = self._real.character[char]

        @char.listener
        def dispatch_remote(b, t, char, k, v):
            self._remote.char_stat_changed(b, t, char.name, k, v)

    def listen_to_node(self, char, node):
        node = self._real.character[char].node[node]

        @node.listener
        def dispatch_remote(b, t, node, k, v):
                node.character.name, node.name, k, v
            ))
            self._remote.node_stat_changed(
                b, t, node.character.name, node.name, k, v
            )

    def listen_to_portal(self, char, orig, dest):
        edge = self._real.character[char].portal[orig][dest]

        @edge.listener
        def dispatch_remote(b, t, edge, k, v):
                edge.character.name, edge._origin, edge._destination, k, v
            ))
            self._remote.edge_stat_changed(
                b, t, edge.character.name, edge._origin, edge._destination
            )

    def time_locked(self):
        return hasattr(self._real, 'locktime')

    def advance(self):
        self._real.advance()

    def next_tick(self):
        self._real.next_tick()
        self._q.put(('next_tick', self._real.branch, self._real.tick))

    def add_character(self, name, data, kwargs):
        self._real.add_character(name, data, **kwargs)

    def commit(self):
        self._real.commit()

    def close(self):
        self._real.close()

    def get_branch(self):
        return self._real.branch

    def set_branch(self, v):
        self._real.branch = v

    def get_tick(self):
        return self._real.tick

    def set_tick(self, v):
        self._real.tick = v

    def get_time(self):
        return self._real.time

    def set_time(self, v):
        self._real.time = v

    def get_language(self):
        return self._real.string.language

    def set_language(self, v):
        self._real.string.language = v

    def get_string_ids(self):
        return list(self._real.string)

    def get_string_lang_items(self, lang):
        return list(self._real.string.lang_items(lang))

    def count_strings(self):
        return len(self._real.string)

    def get_string(self, k):
        return self._real.string[k]

    def set_string(self, k, v):
        self._real.string[k] = v

    def del_string(self, k):
        del self._real.string[k]

    def get_eternal(self, k):
        return self._real.eternal[k]

    def set_eternal(self, k, v):
        self._real.eternal[k] = v

    def del_eternal(self, k):
        del self._real.eternal[k]

    def eternal_keys(self):
        return list(self._real.eternal.keys())

    def eternal_len(self):
        return len(self._real.eternal)

    def have_eternal(self, k):
        return k in self._real.eternal

    def get_universal(self, k):
        return self._real.universal[k]

    def set_universal(self, k, v):
        self._real.universal[k] = v

    def del_universal(self, k):
        del self._real.universal[k]

    def universal_keys(self):
        return list(self._real.universal.keys())

    def universal_len(self):
        return len(self._real.universal)

    def init_character(self, char, statdict={}):
        if char in self._real.character:
            raise KeyError("Already have character {}".format(char))
        self._real.character[char] = {}
        self._real.character[char].stat.update(statdict)

    def del_character(self, char):
        del self._real.character[char]

    def get_character_stat(self, char, k):
        return self._real.character[char].stat[k]

    def set_character_stat(self, char, k, v):
        self._real.character[char].stat[k] = v

    def del_character_stat(self, char, k):
        del self._real.character[char].stat[k]

    def character_stats(self, char):
        return list(self._real.character[char].stat.keys())

    def character_stats_len(self, char):
        return len(self._real.character[char].stat)

    def characters(self):
        return list(self._real.character.keys())

    def characters_len(self):
        return len(self._real.character)

    def have_character(self, char):
        return char in self._real.character

    def set_character(self, char, v):
        self._real.character[char] = v

    def get_node_stat(self, char, node, k):
        return self._real.character[char].node[node][k]

    def set_node_stat(self, char, node, k, v):
        self._real.character[char].node[node][k] = v

    def del_node_stat(self, char, node, k):
        del self._real.character[char].node[node][k]

    def on_node_stat(self, char, node, k, v):
        self._q.put(('on_node_stat', char, node, k, v))

    def node_stat_keys(self, char, node):
        return list(self._real.character[char].node[node])

    def node_stat_len(self, char, node):
        return len(self._real.character[char].node[node])

    def node_has_stat(self, char, node, k):
        return k in self._real.character[char].node[node]

    def del_node(self, char, node):
        del self._real.character[char].node[node]

    def character_things(self, char):
        return list(self._real.character[char].thing)

    def character_things_len(self, char):
        return len(self._real.character[char].thing)

    def character_has_thing(self, char, thing):
        return thing in self._real.character[char].thing

    def character_places(self, char):
        return list(self._real.character[char].place)

    def character_places_len(self, char):
        return len(self._real.character[char].place)

    def character_has_place(self, char, place):
        return place in self._real.character[char].place

    def character_nodes(self, char):
        return list(self._real.character[char].node.keys())

    def character_predecessor_nodes(self, char):
        return list(self._real.character[char].adj.keys())

    def node_has_predecessor(self, char, node):
        return node in self._real.character[char].pred.keys()

    def node_predecessors_len(self, char, node):
        return len(self._real.character[char].pred[node])

    def node_predecessors(self, char, node):
        return list(self._real.character[char].pred[node].keys())

    def node_precedes(self, char, nodeB, nodeA):
        return nodeA in self._real.character[char].pred[nodeB]

    def character_nodes_with_predecessors(self, char):
        return list(self._real.character[char].pred.keys())

    def character_nodes_with_predecessors_len(self, char):
        return len(self._real.character[char].pred)

    def character_set_node_predecessors(self, char, node, preds):
        self._real.character[char].pred[node] = preds

    def character_del_node_predecessors(self, char, node):
        del self._real.character[char].pred[node]

    def character_nodes_len(self, char):
        return len(self._real.character[char].node)

    def character_has_node(self, char, node):
        return node in self._real.character[char].node

    def character_nodes_with_successors(self, char):
        return list(self._real.character[char].adj.keys())

    def character_node_successors(self, char, node):
        return list(self._real.character[char].adj[node].keys())

    def character_node_successors_len(self, char, node):
        return len(self._real.character[char].adj[node])

    def character_set_node_successors(self, char, node, val):
        self._real.character[char].adj[node] = val

    def character_del_node_successors(self, char, node):
        del self._real.character[char].adj[node]

    def character_nodes_connected(self, char, nodeA, nodeB):
        return nodeB in self._real.character[char].portal[nodeA]

    def character_len_node_successors(self, char, nodeA):
        return len(self._real.character[char].node[nodeA])

    def init_thing(self, char, thing, statdict={}):
        if thing in self._real.character[char].thing:
            raise KeyError(
                'Already have thing in character {}: {}'.format(
                    char, thing
                )
            )
        self.set_thing(char, thing, statdict)

    def set_thing(self, char, thing, statdict):
        self._real.character[char].thing[thing] = statdict

    def add_thing(self, char, thing, location, next_location, statdict):
        self._real.character[char].add_thing(
            thing, location, next_location, **statdict
        )

    def place2thing(self, char, name, location, next_location=None):
        self._real.character[char].place2thing(name, location, next_location)

    def thing2place(self, char, name):
        self._real.character[char].thing2place(name)

    def add_things_from(self, char, seq):
        self._real.character[char].add_things_from(seq)

    def get_thing_location(self, char, th):
        return self._real.character[char].thing[th]['location']

    def set_thing_location(self, char, th, loc):
        self._real.character[char].thing[th]['location'] = loc

    def get_thing_next_location(self, char, th):
        return self._real.character[char].thing[th]['next_location']

    def set_thing_next_location(self, char, th, loc):
        self._real.character[char].thing[th]['next_location'] = loc

    def thing_follow_path(self, char, th, path, weight):
        self._real.character[char].thing[th].follow_path(path, weight)

    def thing_go_to_place(self, char, th, place, weight):
        self._real.character[char].thing[th].go_to_place(place, weight)

    def thing_travel_to(self, char, th, dest, weight, graph):
        self._real.character[char].thing[th].travel_to(dest, weight, graph)

    def thing_travel_to_by(self, char, th, dest, arrival_tick, weight, graph):
        self._real.character[char].thing[th].travel_to_by(
            dest, arrival_tick, weight, graph
        )

    def init_place(self, char, place, statdict={}):
        if place in self._real.character[char].place:
            raise KeyError(
                'Already have place in character {}: {}'.format(
                    char, place
                )
            )
        self.set_place(char, place, statdict)

    def set_place(self, char, place, statdict):
        self._real.character[char].place[place] = statdict

    def add_places_from(self, char, seq):
        self._real.character[char].add_places_from(seq)

    def init_portal(self, char, o, d, statdict={}):
        if (
                o in self._real.character[char].portal and
                d in self._real.character[char].portal[o]
        ):
            raise KeyError(
                'Already have portal in character {}: {}->{}'.format(
                    char, o, d
                )
            )
        self.set_portal(char, o, d, statdict)

    def set_portal(self, char, o, d, statdict):
        self._real.character[char].portal[o][d] = statdict

    def character_portals(self, char):
        return list(self._real.character[char].portals())

    def add_portal(self, char, o, d, symmetrical, statdict):
        self._real.character[char].add_portal(o, d, symmetrical, **statdict)

    def add_portals_from(self, char, seq, symmetrical):
        self._real.character[char].add_portals_from(seq, symmetrical)

    def del_portal(self, char, o, d):
        del self._real.character[char].portal[o][d]

    def get_portal_stat(self, char, o, d, k):
        return self._real.character[char].portal[o][d][k]

    def set_portal_stat(self, char, o, d, k, v):
        self._real.character[char].portal[o][d][k] = v

    def del_portal_stat(self, char, o, d, k):
        del self._real.character[char][o][d][k]

    def portal_stats(self, char, o, d):
        return list(self._real.character[char][o][d].keys())

    def len_portal_stats(self, char, o, d):
        return len(self._real.character[char][o][d])

    def character_avatars(self, char):
        return list(self._real.character[char].avatars())

    def add_avatar(self, char, a, b):
        self._real.character[char].add_avatar(a, b)

    def del_avatar(self, char, a, b):
        self._real.character[char].del_avatar(a, b)

    def get_rule_actions(self, rule):
        return self._real.rule.db.rule_actions(rule)

    def set_rule_actions(self, rule, l):
        self._real.rule.db.set_rule_actions(rule, l)

    def get_rule_triggers(self, rule):
        return self._real.rule.db.rule_triggers(rule)

    def set_rule_triggers(self, rule, l):
        self._real.rule.db.set_rule_triggers(rule, l)

    def get_rule_prereqs(self, rule):
        return self._real.rule.db.rule_prereqs(rule)

    def set_rule_prereqs(self, rule, l):
        self._real.rule.db.set_rule_prereqs(rule, l)

    def get_rulebook_rules(self, rulebook):
        return list(self._real.db.rulebook_rules(rulebook))

    def set_rulebook_rule(self, rulebook, i, rule):
        self._real.db.rulebook_set(rulebook, i, rule)

    def ins_rulebook_rule(self, rulebook, i, rule):
        self._real.db.rulebook_decr(rulebook, i)
        self.set_rulebook_rule(rulebook, i, rule)

    def del_rulebook_rule(self, rulebook, i):
        self._real.db.rulebook_del(rulebook, i)

    def get_character_rulebook(self, character):
        return self._real.db.get_rulebook_char(
            "character",
            character
        )

    def get_node_rulebook(self, character, node):
        return self._real.db.node_rulebook(character, node)

    def get_portal_rulebook(self, char, nodeA, nodeB):
        return self._real.db.portal_rulebook(
            char, nodeA, nodeB, 0
        )

    def rulebooks(self):
        return list(self._real.rulebook.keys())

    def len_rulebooks(self):
        return len(self._real.rulebook)

    def have_rulebook(self, k):
        return k in self._real.rulebook

    def keys_in_store(self, store):
        return list(getattr(self._real, store).keys())

    def len_store(self, store):
        return len(getattr(self._real, store))

    def plain_items_in_store(self, store):
        return list(getattr(self._real, store).iterplain())

    def plain_source(self, store, k):
        return getattr(self._real, store).plain(k)


class EngineManager(BaseManager):
    pass


EngineManager.register('EngineHandle', EngineHandle)
EngineManager.register('Queue', Queue)
EngineManager.register('Lock', Lock)


class NodeProxy(MutableMapping):
    @property
    def character(self):
        return CharacterProxy(self._engine, self._charname)

    @property
    def rulebook(self):
        if not hasattr(self, '_rulebook'):
            self._rulebook = self._get_rulebook()
        return self._rulebook

    def _get_rulebook(self):
        return RuleBookProxy(self._engine, self._get_rulebook_name())

    def _get_rulebook_name(self):
        return self._engine._handle.get_node_rulebook(
            self._charname, self._name
        )

    def __init__(self, engine_proxy, charname, nodename):
        self._engine = engine_proxy
        self._charname = charname
        self._name = self.name = nodename

    def __iter__(self):
        yield from self._engine._handle.node_stat_keys(self._charname, self._name)

    def __len__(self):
        return self._engine._handle.node_stat_len(self._charname, self._name)

    def __contains__(self, k):
        return self._engine._handle.node_has_stat(self._charname, self._name, k)

    def __getitem__(self, k):
        return self._engine._handle.get_node_stat(self._charname, self._name, k)

    def __setitem__(self, k, v):
        self._engine._handle.set_node_stat(self._charname, self._name, k, v)

    def __delitem__(self, k):
        self._engine._handle.del_node_stat(self._charname, self._name, k)

    def listener(self, fun):
        self._engine.node_stat_listener(
            self._charname, self._name, fun
        )


class PlaceProxy(NodeProxy):
    pass


class ThingProxy(NodeProxy):
    @property
    def location(self):
        ln = self['location']
        if ln in self._engine._handle.character_things(self._charname):
            return ThingProxy(self._engine, self._charname, ln)
        else:
            return PlaceProxy(self._engine, self._charname, ln)

    @location.setter
    def location(self, v):
        self._engine._handle.set_thing_location(self._charname, self._name, v._name)

    @property
    def next_location(self):
        ln = self['next_location']
        if ln in self._engine._handle.character_things(self._charname):
            return ThingProxy(self._engine, self._charname, ln)
        else:
            return PlaceProxy(self._engine, self._charname, ln)

    @next_location.setter
    def next_location(self, v):
        self._engine._handle.set_thing_next_location(
            self._charname, self._name, v._name
        )

    def follow_path(self, path, weight=None):
        self._engine._handle.thing_follow_path(
            self._charname, self._name, path, weight
        )

    def go_to_place(self, place, weight=''):
        self._engine._handle.thing_go_to_place(
            self._charname, self._name, place, weight
        )

    def travel_to(self, dest, weight=None, graph=None):
        self._engine._handle.thing_travel_to(
            self._charname, self._name, dest, weight, graph
        )

    def travel_to_by(self, dest, arrival_tick, weight=None, graph=None):
        self._engine._handle.thing_travel_to_by(
            self._charname, self._name, dest, arrival_tick, weight, graph
        )


class PortalProxy(MutableMapping):
    @property
    def rulebook(self):
        if not hasattr(self, '_rulebook'):
            self._rulebook = self._get_rulebook()
        return self._rulebook

    def _get_rulebook_name(self):
        return self._engine._handle.get_portal_rulebook(
            self._charname, self._nodeA, self._nodeB
        )

    def _get_rulebook(self):
        return RuleBookProxy(self._engine, self._get_rulebook_name())

    def __init__(self, engine_proxy, charname, nodeAname, nodeBname):
        self._engine = engine_proxy
        self._charname = charname
        self._nodeA = nodeAname
        self._nodeB = nodeBname
        self._stat_listeners = defaultdict(list)

    def __iter__(self):
        yield from self._engine._handle.portal_stats(
            self._charname, self._nodeA, self._nodeB
        )

    def __len__(self):
        return self._engine._handle.len_portal_stats(
            self._charname, self._nodeA, self._nodeB
        )

    def __getitem__(self, k):
        return self._engine._handle.get_portal_stat(
            self._charname, self._nodeA, self._nodeB, k
        )

    def __setitem__(self, k, v):
        self._engine._handle.set_portal_stat(
            self._charname, self._nodeA, self._nodeB, k, v
        )

    def __delitem__(self, k):
        self._engine._handle.del_portal_stat(
            self._charname, self._nodeA, self._nodeB, k
        )

    def listener(self, fun):
        self._engine.edge_stat_listener(
            self._charname, self._nodeA, self._nodeB, fun
        )


class NodeMapProxy(MutableMapping):
    def __init__(self, engine_proxy, charname):
        self._engine = engine_proxy
        self._charname = charname
        self._cache = {}

    def __iter__(self):
        yield from self._engine._handle.character_nodes(self._charname)

    def __len__(self):
        return self._engine._handle.character_nodes_len(self._charname)

    def __contains__(self, k):
        if k in self._cache:
            return True
        return self._engine._handle.character_has_node(self._charname, k)

    def __getitem__(self, k):
        if k in self._cache:
            return self._cache[k]
        if k not in self:
            raise KeyError("No such node: {}".format(k))
        if self._engine._handle.character_has_thing(self._name, k):
            return ThingProxy(self._name, k)
        else:
            return PlaceProxy(self._name, k)

    def __setitem__(self, k, v):
        self._engine._handle.set_place(self._charname, k, v)

    def __delitem__(self, k):
        self._engine._handle.del_node(self._charname, k)
        if k in self._cache:
            del self._cache[k]


class ThingMapProxy(MutableMapping):
    @property
    def character(self):
        return self._engine.character[self._name]

    def __init__(self, engine_proxy, charname):
        self._engine = engine_proxy
        self._name = charname

    def __iter__(self):
        yield from self._engine._handle.character_things(self._name)

    def __len__(self):
        return self._engine._handle.character_things_len(self._name)

    def __contains__(self, k):
        if (
                k in self.character.node._cache and
                isinstance(
                    self.character.node._cache[k],
                    ThingProxy
                )
        ):
            return True
        return self._engine._handle.character_has_thing(self._name, k)

    def __getitem__(self, k):
        if k in self.character.node._cache:
            r = self.character.node._cache[k]
            if isinstance(r, ThingProxy):
                return r
            else:
                raise TypeError(
                    '{} is a Place, not a Thing'.format(
                        k
                    )
                )
        if k not in self:
            raise KeyError("No such Thing: {}".format(k))
        r = ThingProxy(self._engine, self._name, k)
        self.character.node._cache[k] = r
        return r

    def __setitem__(self, k, v):
        self._engine._handle.set_thing(self._name, k, v)

    def __delitem__(self, k):
        if k in self.character.node._cache:
            del self.character.node._cache[k]
        self._engine._handle.del_node(self._name, k)


class PlaceMapProxy(MutableMapping):
    @property
    def character(self):
        return self._engine.character[self._name]

    def __init__(self, engine_proxy, character):
        self._engine = engine_proxy
        self._name = character

    def __iter__(self):
        yield from self._engine._handle.character_places(self._name)

    def __len__(self):
        return self._engine._handle.character_places_len(self._name)

    def __contains__(self, k):
        if (
                k in self.character.node._cache and
                isinstance(
                    self.character.node._cache[k],
                    PlaceProxy
                )
        ):
            return True
        return self._engine._handle.character_has_place(self._name, k)

    def __getitem__(self, k):
        if k not in self:
            raise KeyError("No such place: {}".format(k))
        if k in self.character.node._cache:
            r = self.character.node._cache[k]
            if isinstance(r, ThingProxy):
                raise TypeError(
                    '{} is a Thing, not a Place'.format(k)
                )
            return r
        r = PlaceProxy(self._engine, self._name, k)
        self.character.node._cache[k] = r
        return r

    def __setitem__(self, k, v):
        self._engine._handle.set_place(self._name, k, v)

    def __delitem__(self, k):
        if k in self.character.node._cache:
            del self.character.node._cache[k]
        self._engine._handle.del_node(self._name, k)


class SuccessorsProxy(MutableMapping):
    def __init__(self, engine_proxy, charname, nodeAname):
        self._engine = engine_proxy
        self._charname = charname
        self._nodeA = nodeAname
        self._cache = {}

    def __iter__(self):
        yield from self._engine._handle.character_node_successors(
            self._charname, self._nodeA
        )

    def __contains__(self, nodeB):
        if nodeB in self._cache:
            return True
        return self._engine._handle.character_nodes_connected(
            self._charname, self._nodeA, nodeB
        )

    def __len__(self):
        return self._engine._handle.character_len_node_successors(
            self._charname, self._nodeA
        )

    def __getitem__(self, nodeB):
        if nodeB not in self:
            raise KeyError(
                'No portal from {} to {}'.format(
                    self._nodeA, nodeB
                )
            )
        if nodeB not in self._cache:
            self._cache[nodeB] = PortalProxy(
                self._engine, self._charname, self._nodeA, nodeB
            )
        return self._cache[nodeB]

    def __setitem__(self, nodeB, value):
        self._engine._handle.set_portal(
            self._character, self._nodeA, nodeB, value
        )

    def __delitem__(self, nodeB):
        if nodeB in self._cache:
            del self._cache[nodeB]
        self._engine._handle.del_portal(self._character, self._nodeA, nodeB)


class CharSuccessorsMappingProxy(MutableMapping):
    def __init__(self, engine_proxy, charname):
        self._engine = engine_proxy
        self._charname = charname
        self._cache = {}

    def __iter__(self):
        yield from self._engine._handle.character_nodes_with_successors(
            self._charname
        )

    def __len__(self):
        return self._engine._handle.character_node_successors_len(
            self._charname
        )

    def __contains__(self, nodeA):
        if nodeA in self._cache:
            return True
        return self._engine._handle.character_has_node(self._charname, nodeA)

    def __getitem__(self, nodeA):
        if nodeA not in self:
            raise KeyError("No such node: {}".format(nodeA))
        if nodeA not in self._cache:
            self._cache[nodeA] = SuccessorsProxy(
                self._engine, self._charname, nodeA
            )
        return self._cache[nodeA]

    def __setitem__(self, nodeA, val):
        self._engine._handle.character_set_node_successors(
            self._charname, nodeA, val
        )

    def __delitem__(self, nodeA):
        if nodeA in self._cache:
            del self._cache[nodeA]
        self._engine._handle.character_del_node_successors(
            self._charname, nodeA
        )


class PredecessorsProxy(MutableMapping):
    @property
    def character(self):
        return self._engine.character[self._charname]

    def __init__(self, engine_proxy, charname, nodeBname):
        self._engine = engine_proxy
        self._charname = charname
        self._name = nodeBname

    def __iter__(self):
        yield from self._engine._handle.node_predecessors(
            self._charname, self._name
        )

    def __len__(self):
        return self._engine._handle.node_predecessors_len(
            self._charname, self._name
        )

    def __contains__(self, k):
        if (
            k in self.character.portal._cache and
            self._name in self.character.portal._cache[k]
        ):
            return True
        return self._engine._handle.node_precedes(
            self._charname, self._name, k
        )

    def __getitem__(self, k):
        if k not in self:
            raise KeyError(
                "{} does not precede {}".format(k, self._name)
            )
        if k not in self.character.portal._cache:
            self.character.portal._cache[k] = {}
        if self._name not in self.character.portal._cache[k]:
            self.character.portal._cache[k][self._name] = PortalProxy(
                self._engine, self._charname, k, self._name
            )
        return self.character.portal._cache[k][self._name]

    def __setitem__(self, k, v):
        self._engine._handle.set_place(self._charname, k, v)
        self._engine._handle.set_portal(self._charname, k, self._name)

    def __delitem__(self, k):
        if k not in self:
            raise KeyError(
                "{} does not precede {}".format(k, self._name)
            )
        if (
            k in self.character.portal._cache and
            self._name in self.character.portal._cache[k]
        ):
            del self.character.portal._cache[k][self._name]
        self._engine._handle.del_portal(self._charname, k, self._name)


class CharPredecessorsMappingProxy(MutableMapping):
    def __init__(self, engine_proxy, charname):
        self._engine = engine_proxy
        self._name = charname
        self._cache = {}

    def __contains__(self, k):
        if k in self._cache:
            return True
        return self._engine._handle.node_has_predecessor(self._name, k)

    def __iter__(self):
        yield from self._engine._handle.character_nodes_with_predecessors(
            self._name
        )

    def __len__(self):
        return self._engine._handle.character_nodes_with_predecessors_len(
            self._name
        )

    def __getitem__(self, k):
        if k not in self:
            raise KeyError(
                "No predecessors to {} (if it even exists)".format(k)
            )
        if k not in self._cache:
            self._cache[k] = PredecessorsProxy(self._engine, self._name, k)
        return self._cache[k]

    def __setitem__(self, k, v):
        self._engine._handle.character_set_node_predecessors(self._name, k, v)

    def __delitem__(self, k):
        if k not in self:
            raise KeyError(
                "No predecessors to {} (if it even exists)".format(k)
            )
        if k in self._cache:
            del self._cache[k]
        self._engine._handle.character_del_node_predecessors(self._name, k)


class CharStatProxy(MutableMapping):
    def __init__(self, engine_proxy, character):
        self._engine = engine_proxy
        self._name = character

    def __iter__(self):
        yield from self._engine._handle.character_stats(self._name)

    def __len__(self):
        return self._engine._handle.character_stats_len(self._name)

    def __getitem__(self, k):
        return self._engine._handle.get_character_stat(self._name, k)

    def __setitem__(self, k, v):
        self._engine._handle.set_character_stat(self._name, k, v)

    def __delitem__(self, k):
        self._engine._handle.del_character_stat(self._name, k)

    def listener(self, fun):
        self._engine.char_stat_listener(
            self._name, fun
        )


class RuleProxy(object):
    @property
    def triggers(self):
        return self._engine._handle.get_rule_triggers(self.name)

    @triggers.setter
    def triggers(self, v):
        self._engine._handle.set_rule_triggers(self.name, v)

    @property
    def prereqs(self):
        return self._engine._handle.get_rule_prereqs(self.name)

    @prereqs.setter
    def prereqs(self, v):
        self._engine._handle.set_rule_prereqs(self.name, v)

    @property
    def actions(self):
        return self._engine._handle.get_rule_actions(self.name)

    @actions.setter
    def actions(self, v):
        self._engine._handle.set_rule_actions(self.name, v)

    def __init__(self, engine_proxy, rulename):
        self._engine = engine_proxy
        self.name = rulename


class RuleBookProxy(MutableSequence):
    def __init__(self, engine_proxy, bookname):
        self._engine = engine_proxy
        self._name = bookname
        self._cache = self._engine._handle.get_rulebook_rules(self._name)
        self._proxy_cache = {}

    def __iter__(self):
        for k in self._cache:
            if k not in self._proxy_cache:
                self._proxy_cache[k] = RuleProxy(self._engine, k)
            yield self._proxy_cache[k]

    def __len__(self):
        return len(self._cache)

    def __getitem__(self, i):
        k = self._cache[i]
        if k not in self._proxy_cache:
            self._proxy_cache[k] = RuleProxy(self._engine, k)
        return self._proxy_cache[k]

    def __setitem__(self, i, v):
        if isinstance(v, RuleProxy):
            v = v._name
        self._cache[i] = v
        self._engine._handle.set_rulebook_rule(self._name, i, v)
        for fun in self._listeners:
            fun(self)

    def __delitem__(self, i):
        del self._cache[i]
        self._engine._handle.del_rulebook_rule(self._name, i)
        for fun in self._listeners:
            fun(self)

    def insert(self, i, v):
        if isinstance(v, RuleProxy):
            v = v._name
        self._cache.insert(i, v)
        self._engine._handle.ins_rulebook_rule(self._name, i, v)
        for fun in self._listeners:
            fun(self)

    def listener(self, f):
        self._engine.rulebook_listener(self._name, f)


class CharacterProxy(MutableMapping):
    @property
    def rulebook(self):
        if not hasattr(self, '_rulebook'):
            self._upd_rulebook()
        return self._rulebook

    def _upd_rulebook(self):
        self._rulebook = self._get_rulebook()

    def _get_rulebook(self):
        return RuleBookProxy(
            self._engine,
            self._engine._handle.get_character_rulebook(self._name)
        )

    def __init__(self, engine_proxy, charname):
        self._engine = engine_proxy
        self._name = self.name = charname
        self.adj = self.succ = self.portal = CharSuccessorsMappingProxy(
            self._engine, self._name
        )
        self.pred = self.preportal = CharPredecessorsMappingProxy(
            self._engine, self._name
        )
        self.node = NodeMapProxy(self._engine, self._name)
        self.thing = ThingMapProxy(self._engine, self._name)
        self.place = PlaceMapProxy(self._engine, self._name)
        self.stat = CharStatProxy(self._engine, self._name)

    def __iter__(self):
        yield from self._engine._handle.character_nodes(self._name)

    def __len__(self):
        return self._engine._handle.character_nodes_len(self._name)

    def __contains__(self, k):
        return k in self.node

    def __getitem__(self, k):
        return self.node[k]

    def __setitem__(self, k, v):
        self.node[k] = v

    def __delitem__(self, k):
        del self.node[k]

    def add_place(self, name, **kwargs):
        self[name] = kwargs

    def add_places_from(self, seq):
        self._engine._handle.add_places_from(self._name, seq)

    def add_nodes_from(self, seq):
        self.add_places_from(seq)

    def add_thing(self, name, location, next_location=None, **kwargs):
        self._engine._handle.add_thing(
            self._name, name, location, next_location, kwargs
        )

    def add_things_from(self, seq):
        self._engine._handle.add_things_from(self._name, seq)

    def new_place(self, name, **kwargs):
        self.add_place(name, **kwargs)
        return self.place[name]

    def new_thing(self, name, location, next_location=None, **kwargs):
        self.add_thing(name, location, next_location, **kwargs)
        return self.thing[name]

    def place2thing(self, name, location, next_location=None):
        self._engine._handle.place2thing(self._name, name, location, next_location)

    def add_portal(self, origin, destination, symmetrical=False, **kwargs):
        self._engine._handle.add_portal(
            self._name, origin, destination, symmetrical, kwargs
        )

    def add_portals_from(self, seq, symmetrical=False):
        self._engine._handle.add_portals_from(self._name, seq, symmetrical)

    def portals(self):
        yield from self._engine._handle.character_portals(self._name)

    def add_avatar(self, a, b=None):
        self._engine._handle.add_avatar(self._name, a, b)

    def del_avatar(self, a, b=None):
        self._engine._handle.del_avatar(self._name, a, b)

    def avatars(self):
        yield from self._engine._handle.character_avatars(self._name)

    def facade(self):
        return Facade(self)


class CharacterMapProxy(MutableMapping):
    def __init__(self, engine_proxy):
        self._engine = engine_proxy

    def __iter__(self):
        yield from self._engine._handle.characters()

    def __contains__(self, k):
        return self._engine._handle.have_character(k)

    def __len__(self):
        return self._engine._handle.characters_len()

    def __getitem__(self, k):
        if not self._engine._handle.have_character(k):
            raise KeyError("No character: {}".format(k))
        return CharacterProxy(self._engine, k)

    def __setitem__(self, k, v):
        if isinstance(v, CharacterProxy):
            return
        self._engine._handle.set_character(k, v)

    def __delitem__(self, k):
        self._engine._handle.del_character(k)


class StringStoreProxy(MutableMapping):
    @property
    def language(self):
        return self._proxy._handle.get_language()

    @language.setter
    def language(self, v):
        self._proxy._handle.set_language(v)
        self._dispatch_lang(v)

    def __init__(self, engine_proxy):
        self._proxy = engine_proxy
        self._str_listeners = defaultdict(list)
        self._lang_listeners = []

    def __iter__(self):
        yield from self._proxy._handle.get_string_ids()

    def __len__(self):
        return self._proxy._handle.count_strings()

    def __getitem__(self, k):
        return self._proxy._handle.get_string(k)

    def __setitem__(self, k, v):
        self._proxy._handle.set_string(k, v)

    def __delitem__(self, k):
        self._proxy._handle.del_string(k)

    def _dispatch_lang(self, v):
        for f in self._lang_listeners:
            f(self, v)

    def _dispatch_str(self, k, v):
        dispatch(self._str_listeners, k, self, k, v)

    def lang_listener(self, f):
        listen(self._lang_listeners, f)

    def listener(self, fun=None, string=None):
        return listener(self._str_listeners, fun, string)

    def lang_items(self, lang=None):
        yield from self._proxy._handle.get_string_lang_items(lang)


class EternalVarProxy(MutableMapping):
    def __init__(self, engine_proxy):
        self._engine = engine_proxy

    def __contains__(self, k):
        return self._engine._handle.have_eternal(k)

    def __iter__(self):
        yield from self._engine._handle.eternal_keys()

    def __len__(self):
        return self._engine._handle.eternal_len()

    def __getitem__(self, k):
        return self._engine._handle.get_eternal(k)

    def __setitem__(self, k, v):
        self._engine._handle.set_eternal(k, v)

    def __delitem__(self, k):
        self._engine._handle.del_eternal(k)


class GlobalVarProxy(MutableMapping):
    def __init__(self, engine_proxy):
        self._proxy = engine_proxy
        self._listeners = defaultdict(list)

    def __iter__(self):
        yield from self._proxy.universal_keys()

    def __len__(self):
        return self._proxy.universal_len()

    def __getitem__(self, k):
        return self._proxy.get_universal(k)

    def __setitem__(self, k, v):
        self._proxy.set_universal(k, v)

    def __delitem__(self, k):
        self._proxy.del_universal(k)

    def _dispatch(self, k, v):
        dispatch(self._listeners, k, self, k, v)

    def listener(self, f=None, key=None):
        return listener(self._listeners, f, key)


class AllRuleBooksProxy(Mapping):
    def __init__(self, engine_proxy):
        self._engine = engine_proxy
        self._cache = {}

    def __iter__(self):
        yield from self._engine._handle.rulebooks()

    def __len__(self):
        return self._engine._handle.len_rulebooks()

    def __contains__(self, k):
        if k in self._cache:
            return True
        return self._engine._handle.have_rulebook(k)

    def __getitem__(self, k):
        if k not in self:
            raise KeyError("No rulebook: {}".format(k))
        if k not in self._cache:
            self._cache[k] = RuleBookProxy(self._engine, k)
        return self._cache[k]


class FuncStoreProxy(object):
    def __init__(self, engine_proxy, store):
        self._engine = engine_proxy
        self._store = store

    def __iter__(self):
        yield from self._engine._handle.keys_in_store(self._store)

    def __len__(self):
        return self._engine._handle.len_store(self._store)

    def plain(self, k):
        return self._engine._handle.plain_source(self._store, k)

    def iterplain(self):
        yield from self._engine._handle.plain_items_in_store(self._store)


class EngineProxy(object):
    def __init__(self, handle):
        self._handle = handle
        self.eternal = EternalVarProxy(self)
        self.universal = GlobalVarProxy(self)
        self.character = CharacterMapProxy(self)
        self.string = StringStoreProxy(self)
        self.rulebook = AllRuleBooksProxy(self)
        for funstore in ('action', 'prereq', 'trigger', 'sense', 'function'):
            setattr(self, funstore, FuncStoreProxy(self, funstore))
        self._rulebook_listeners = defaultdict(list)
        self._time_listeners = []
        self._char_stat_listeners = {}
        self._node_stat_listeners = {}
        self._edge_stat_listeners = {}

    def char_stat_listener(self, char, fun):
        # only call from host process
        if char not in self._char_stat_listeners:
            self._char_stat_listeners[char] = []
            self._handle.listen_to_character(char)
        if fun not in self._char_stat_listeners[char]:
            self._char_stat_listeners[char].append(fun)

    def node_stat_listener(self, char, node, fun):
        # only call from host process
        if char not in self._node_stat_listeners:
            self._node_stat_listeners[char] = {}
        if node not in self._node_stat_listeners[char]:
            self._node_stat_listeners[char][node] = []
            self._handle.listen_to_node(char, node)
        if fun not in self._node_stat_listeners[char][node]:
            self._node_stat_listeners[char][node].append(fun)

    def edge_stat_listener(self, char, orig, dest, fun):
        # only call from host process
        if char not in self._edge_stat_listeners:
            self._edge_stat_listeners[char] = {}
        if orig not in self._edge_stat_listeners[char]:
            self._edge_stat_listeners[char][orig] = {}
        if dest not in self._edge_stat_listeners[char][orig]:
            self._edge_stat_listeners[char][orig][dest] = []
            self._handle.listen_to_portal(char, orig, dest)
        if fun not in self._edge_stat_listeners[char][orig][dest]:
            self._edge_stat_listeners[char][orig][dest].append(fun)

    def char_stat_changed(self, b, t, char, k, v):
        if char not in self._char_stat_listeners:
            return
        for fun in self._char_stat_listeners[char]:
            fun(
                b, t,
                self.character[char],
                k, v
            )

    def node_stat_changed(self, b, t, char, node, k, v):
        if (
                char not in self._node_stat_listeners or
                node not in self._node_stat_listeners[char]
        ):
            return
        for fun in self._node_stat_listeners[char][node]:
            fun(
                b, t,
                self.character[char].node[node],
                k, v
            )

    def edge_stat_changed(self, b, t, char, o, d, k, v):
        if (
                char not in self._edge_stat_listeners or
                o not in self._edge_stat_listeners[char] or
                d not in self._edge_stat_listeners[char][o]
        ):
            return
        for fun in self._edge_stat_listeners[char][o][d]:
            fun(
                b, t,
                self.character[char].portal[o][d],
                k, v
            )

    @property
    def branch(self):
        return self._handle.get_branch()

    @branch.setter
    def branch(self, v):
        self._handle.set_branch(v)
        if not self._handle.time_locked():
            (branch, tick) = self.time
            for f in self._time_listeners:
                f(self, branch, tick, v, tick)

    @property
    def tick(self):
        return self._handle.get_tick()

    @tick.setter
    def tick(self, v):
        self._handle.set_tick(v)
        if not self._handle.time_locked():
            (b, t) = self.time
            for f in self._time_listeners:
                f(self, b, t, b, v)

    @property
    def time(self):
        return self._handle.get_time()

    @time.setter
    def time(self, v):
        self._handle.set_time(v)
        if not self._handle.time_locked():
            (b, t) = self.time
            (branch, tick) = v
            for f in self._time_listeners:
                f(self, b, t, branch, tick)

    def on_time(self, f):
        if not isinstance(f, Callable):
            raise TypeError('on_time is a decorator')
        if f not in self._time_listeners:
            self._time_listeners.append(f)

    def add_character(self, name, data=None, **kwargs):
        self._handle.add_character(name, data, kwargs)

    def new_character(self, name, **kwargs):
        self.add_character(name, **kwargs)
        return CharacterProxy(self._handle, name)

    def del_character(self, name):
        self._handle.del_character(name)

    def commit(self):
        self._handle.commit()

    def close(self):
        self._handle.close()

    def rulebook_listener(self, rulebook, f):
        self._rulebook_listeners[rulebook].append(f)


class RemoteEngineProxy(object):
    def reify(self, engine):
        self._real = engine

    def char_stat_changed(self, b, t, char, k, v):
        self._real.char_stat_changed(b, t, char, k, v)

    def node_stat_changed(self, b, t, char, node, k, v):
        self._real.node_stat_changed(b, t, char, node, k, v)

    def edge_stat_changed(self, b, t, char, o, d, k, v):
        self._real.edge_stat_changed(b, t, char, o, d, k, v)


EngineManager.register('RemoteEngineProxy', RemoteEngineProxy)


def create_handle(manager, queue):
    handle = manager.EngineHandle()
    print('engine handle created in process {}'.format(os.getpid()))
    queue.put(handle)


class LiSERemoteControl(object):
    def __init__(self):
        self._manager = EngineManager()

    def start(
            self,
            worlddb,
            codedb,
            connect_args={},
            alchemy=False,
            caching=True,
            commit_modulus=None,
            random_seed=None
    ):
        self._manager.start()
        q = self._manager.Queue()
        self._p = Process(
            target=create_handle,
            args=(
                self._manager,
                q
            )
        )
        self._p.start()
        self._handle = q.get()
        print('got handle in process {}'.format(os.getpid()))
        self._proxy = EngineProxy(self._handle)
        remote = self._manager.RemoteEngineProxy()
        remote.reify(self._proxy)
        q.put(remote)
        self._handle.reify(
            (
                worlddb,
                codedb,
                connect_args,
                alchemy,
                caching,
                commit_modulus,
                random_seed
            ),
            q
        )
        return self._proxy

    def shutdown(self):
        self.engine.close()
        self._p.join()
        self._manager.shutdown()
