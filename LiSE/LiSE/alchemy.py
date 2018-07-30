# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) Zachary Spector,  public@zacharyspector.com
"""A script to generate the SQL needed for LiSE's database backend,
and output it in JSON form.

This uses sqlalchemy to describe the queries. It extends the module of
the same name in the ``allegedb`` package. If you change anything here,
you won't be able to use your changes until you put the generated JSON
where LiSE will look for it, as in:

``python3 sqlalchemy.py >sqlite.json``

"""
from functools import partial
from sqlalchemy import (
    Table,
    Column,
    ForeignKeyConstraint,
    select,
    bindparam,
    func,
    and_,
    or_,
    INT,
    TEXT,
    BOOLEAN
)
from sqlalchemy.sql.ddl import CreateTable, CreateIndex


BaseColumn = Column
Column = partial(BaseColumn, nullable=False)


from json import dumps

from allegedb.alchemy import tables_for_meta as alch_tab_meta
from allegedb.alchemy import (
    queries_for_table_dict,
    branch_query_until,
    branch_query_window
)


def tables_for_meta(meta):
    """Return a dictionary full of all the tables I need for LiSE. Use the
    provided metadata object.

    """
    alch_tab_meta(meta)

    # Table for global variables that are not sensitive to sim-time.
    Table(
        'universals', meta,
        Column('key', TEXT, primary_key=True),
        Column(
            'branch', TEXT, primary_key=True, default='trunk'
        ),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('prev', TEXT),
        Column('value', TEXT)
    )

    Table(
        'rules', meta,
        Column('rule', TEXT, primary_key=True)
    )

    # Table grouping rules into lists called rulebooks.
    Table(
        'rulebooks', meta,
        Column('rulebook', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('prev', TEXT),
        Column('rules', TEXT)
    )

    # Table for rules' triggers, those functions that return True only
    # when their rule should run.
    Table(
        'rule_triggers', meta,
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('prev', TEXT),
        Column('triggers', TEXT),
        ForeignKeyConstraint(
            ['rule'], ['rules.rule']
        )
    )

    # Table for rules' prereqs, functions that decide whether it's
    # possible for a rule to run
    Table(
        'rule_prereqs', meta,
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('prev', TEXT),
        Column('prereqs', TEXT),
        ForeignKeyConstraint(
            ['rule'], ['rules.rule']
        )
    )

    # Table for rules' actions, the functions that do what the rule
    # does.
    Table(
        'rule_actions', meta,
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('prev', TEXT),
        Column('actions', TEXT),
        ForeignKeyConstraint(
            ['rule'], ['rules.rule']
        )
    )

    # The top level of the LiSE world model, the character. Includes
    # rulebooks for the character itself, its avatars, and all the things,
    # places, and portals it contains--though those may have their own
    # rulebooks as well.

    for name in (
        'character_rulebook',
        'avatar_rulebook',
        'character_thing_rulebook',
        'character_place_rulebook',
        'character_portal_rulebook'
    ):
        Table(
            name, meta,
            Column('character', TEXT, primary_key=True),
            Column('branch', TEXT, primary_key=True, default='trunk'),
            Column('turn', INT, primary_key=True, default=0),
            Column('tick', INT, primary_key=True, default=0),
            Column('prev', TEXT),
            Column('rulebook', TEXT),
            ForeignKeyConstraint(
                ['character'], ['graphs.graph']
            ),
            ForeignKeyConstraint(
                ['rulebook'], ['rulebooks.rulebook']
            )
        )

    # Rules handled within the rulebook associated with one node in
    # particular.
    Table(
        'node_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('node', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT),
        ForeignKeyConstraint(
            ['character', 'node'], ['nodes.graph', 'nodes.node']
        )
    )

    # Rules handled within the rulebook associated with one portal in
    # particular.
    Table(
        'portal_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('orig', TEXT, primary_key=True),
        Column('dest', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT),
        ForeignKeyConstraint(
            ['character', 'orig', 'dest'], ['edges.graph', 'edges.orig', 'edges.dest']
        )
    )

    # The function to use for a given sense.
    #
    # Characters use senses to look at other characters. To model this,
    # sense functions are called with a facade representing the
    # character under observation; the function munges this facade to
    # make it look as it does through the sense in question, and returns
    # that.
    Table(
        'senses', meta,
        # null character field means all characters have this sense
        Column(
            'character', TEXT, primary_key=True, nullable=True
        ),
        Column('sense', TEXT, primary_key=True),
        Column(
            'branch', TEXT, primary_key=True, default='trunk'
        ),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('prev', TEXT, nullable=True),
        Column('function', TEXT, nullable=True),
        ForeignKeyConstraint(['character'], ['graphs.graph'])
    )

    # Table for Things, being those nodes in a Character graph that have
    # locations.
    #
    # A Thing's location can be either a Place or another Thing, as long
    # as it's in the same Character. Things also have a
    # ``next_location``, defaulting to ``None``, which when set
    # indicates that the thing is in transit to that location.
    Table(
        'things', meta,
        Column('character', TEXT, primary_key=True),
        Column('thing', TEXT, primary_key=True),
        Column(
            'branch', TEXT, primary_key=True, default='trunk'
        ),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        # when location is null, this node is not a thing, but a place
        Column('prev_location', TEXT),
        Column('location', TEXT),
        # when next_location is not null, thing is en route between
        # location and next_location
        Column('prev_next_location', TEXT),
        Column('next_location', TEXT),
        ForeignKeyConstraint(
            ['character', 'thing'], ['nodes.graph', 'nodes.node']
        ),
        ForeignKeyConstraint(
            ['character', 'location'], ['nodes.graph', 'nodes.node']
        ),
        ForeignKeyConstraint(
            ['character', 'next_location'], ['nodes.graph', 'nodes.node']
        )
    )

    # The rulebook followed by a given node.
    nrb = Table(
        'node_rulebook', meta,
        Column('character', TEXT, primary_key=True),
        Column('node', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('prev', TEXT),
        Column('rulebook', TEXT)
    )
    nodes = meta.tables['nodes']
    nrb.append_constraint(ForeignKeyConstraint(
        (nrb.c.character, nrb.c.node), (nodes.c.graph, nodes.c.node)
    ))

    # The rulebook followed by a given Portal.
    #
    # "Portal" is LiSE's term for an edge in any of the directed
    # graphs it uses. The name is different to distinguish them from
    # Edge objects, which exist in an underlying object-relational
    # mapper called allegedb, and have a different API.
    porb = Table(
        'portal_rulebook', meta,
        Column('character', TEXT, primary_key=True),
        Column('orig', TEXT, primary_key=True),
        Column('dest', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('prev', TEXT),
        Column('rulebook', TEXT)
    )
    edges = meta.tables['edges']
    porb.append_constraint(ForeignKeyConstraint(
        (porb.c.character, porb.c.orig, porb.c.dest),
        (edges.c.graph, edges.c.orig, edges.c.dest)
    ))

    # The avatars representing one Character in another.
    #
    # In the common situation where a Character, let's say Alice has her
    # own stats and skill tree and social graph, and also has a location
    # in physical space, you can represent this by creating a Thing in
    # the Character that represents physical space, and then making that
    # Thing an avatar of Alice. On its own this doesn't do anything,
    # it's just a convenient way of indicating the relation -- but if
    # you like, you can make rules that affect all avatars of some
    # Character, irrespective of what Character the avatar is actually
    # *in*.
    avs = Table(
        'avatars', meta,
        Column('character_graph', TEXT, primary_key=True),
        Column('avatar_graph', TEXT, primary_key=True),
        Column('avatar_node', TEXT, primary_key=True),
        Column(
            'branch', TEXT, primary_key=True, default='trunk'
        ),
        Column('turn', INT, primary_key=True, default=0),
        Column('tick', INT, primary_key=True, default=0),
        Column('is_avatar', BOOLEAN)
    )
    graphs = meta.tables['graphs']
    avs.append_constraint(ForeignKeyConstraint(
        (avs.c.character_graph,), (graphs.c.graph,)
    ))
    avs.append_constraint(ForeignKeyConstraint(
        (avs.c.avatar_graph, avs.c.avatar_node), (nodes.c.graph, nodes.c.node)
    ))

    Table(
        'character_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True),
        Column('tick', INT),
        ForeignKeyConstraint(
            ['character', 'rulebook'], ['character_rulebook.character', 'character_rulebook.rulebook']
        )
    )

    Table(
        'avatar_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('graph', TEXT, primary_key=True),
        Column('avatar', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True),
        Column('tick', INT),
        ForeignKeyConstraint(
            ['character', 'rulebook'], ['avatar_rulebook.character', 'avatar_rulebook.rulebook']
        )
    )

    Table(
        'character_thing_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('thing', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True),
        Column('tick', INT),
        ForeignKeyConstraint(
            ['character', 'rulebook'], ['character_thing_rulebook.character', 'character_thing_rulebook.rulebook']
        ),
        ForeignKeyConstraint(
            ['character', 'thing'], ['things.character', 'things.thing']
        )
    )

    Table(
        'character_place_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('place', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True),
        Column('tick', INT),
        ForeignKeyConstraint(
            ['character', 'rulebook'], ['character_place_rulebook.character', 'character_place_rulebook.rulebook']
        ),
        ForeignKeyConstraint(
            ['character', 'place'], ['nodes.graph', 'nodes.node']
        )
    )

    Table(
        'character_portal_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('orig', TEXT, primary_key=True),
        Column('dest', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('turn', INT, primary_key=True),
        Column('tick', INT),
        ForeignKeyConstraint(
            ['character', 'rulebook'], ['character_portal_rulebook.character', 'character_portal_rulebook.rulebook']
        ),
        ForeignKeyConstraint(
            ['character', 'orig', 'dest'], ['edges.graph', 'edges.orig', 'edges.dest']
        )
    )

    return meta.tables


def indices_for_table_dict(table):
    return {}


def queries(table):
    """Given dictionaries of tables and view-queries, return a dictionary
    of all the rest of the queries I need.

    """
    r = queries_for_table_dict(table)

    for t in table.values():
        r[t.name + '_dump'] = select(list(t.c.values())).order_by(*t.primary_key)
        r[t.name + '_insert'] = t.insert().values(tuple(bindparam(cname) for cname in t.c.keys()))
        r[t.name + '_count'] = select([func.COUNT('*')]).select_from(t)

    r['del_char_things'] = table['things'].delete().where(
        table['things'].c.character == bindparam('character')
    )

    r['del_char_avatars'] = table['avatars'].delete().where(
        table['avatars'].c.character_graph == bindparam('character')
    )
    things = table['things']
    r['del_things_after'] = things.delete().where(and_(
        things.c.character == bindparam('character'),
        things.c.thing == bindparam('thing'),
        things.c.branch == bindparam('branch'),
        or_(
            things.c.turn > bindparam('turn'),
            and_(
                things.c.turn == bindparam('turn'),
                things.c.tick >= bindparam('tick')
            )
        )
    ))
    avatars = table['avatars']
    r['del_avatars_after'] = avatars.delete().where(and_(
        avatars.c.character_graph == bindparam('character'),
        avatars.c.avatar_graph == bindparam('graph'),
        avatars.c.avatar_node == bindparam('avatar'),
        avatars.c.branch == bindparam('branch'),
        or_(
            avatars.c.turn > bindparam('turn'),
            and_(
                avatars.c.turn == bindparam('turn'),
                avatars.c.tick >= bindparam('tick')
            )
        )
    ))
    u = table['universals']
    ugb = r['universals_get_branch'] = select([
        u.c.key,
        u.c.turn,
        u.c.tick,
        u.c.prev,
        u.c.value
    ]).where(u.c.branch == bindparam('branch')).order_by(u.c.turn, u.c.tick)
    r['universals_get_branch_until'] = branch_query_until(u, ugb)
    r['universals_get_branch_window'] = branch_query_window(u, ugb)
    rbs = table['rulebooks']
    rbsb = r['rules_get_branch'] = select([
        rbs.c.rulebook,
        rbs.c.turn,
        rbs.c.tick,
        rbs.c.prev,
        rbs.c.rules
    ]).where(rbs.c.branch == bindparam('branch')).order_by(rbs.c.turn, rbs.c.tick)
    r['rulebooks_get_branch_until'] = branch_query_until(rbs, rbsb)
    r['rulebooks_get_branch_window'] = branch_query_window(rbs, rbsb)
    rts = table['rule_triggers']
    rtsb = r['rule_triggers_get_branch'] = select([
        rts.c.rule,
        rts.c.turn,
        rts.c.tick,
        rts.c.prev,
        rts.c.triggers
    ]).where(rts.c.branch == bindparam('branch')).order_by(rts.c.turn, rts.c.tick)
    r['rule_triggers_get_branch_until'] = branch_query_until(rts, rtsb)
    r['rule_triggers_get_branch_window'] = branch_query_window(rts, rtsb)
    rps = table['rule_prereqs']
    rpsb = r['rule_prereqs_get_branch'] = select([
        rps.c.rule,
        rps.c.turn,
        rps.c.tick,
        rps.c.prev,
        rps.c.prereqs
    ]).where(rps.c.branch == bindparam('branch')).order_by(rps.c.turn, rps.c.tick)
    r['rule_prereqs_get_branch_until'] = branch_query_until(rps, rpsb)
    r['rule_prereqs_get_branch_window'] = branch_query_window(rps, rpsb)
    ras = table['rule_actions']
    rasb = r['rule_actions_get_branch'] = select([
        ras.c.rule,
        ras.c.turn,
        ras.c.tick,
        ras.c.prev,
        ras.c.actions
    ]).where(ras.c.branch == bindparam('branch')).order_by(ras.c.turn, ras.c.tick)
    r['rule_actions_get_branch_until'] = branch_query_until(ras, rasb)
    r['rule_actions_get_branch_window'] = branch_query_window(ras, rasb)
    for name in (
        'character_rulebook',
        'avatar_rulebook',
        'character_thing_rulebook',
        'character_place_rulebook',
        'character_portal_rulebook'
    ):
        tab = table[name]
        q = r[name + '_get_branch'] = select([
            tab.c.character,
            tab.c.turn,
            tab.c.tick,
            tab.c.rulebook
        ]).where(tab.c.branch == bindparam('branch')).order_by(tab.c.turn, tab.c.tick)
        r[name + '_get_branch_until'] = branch_query_until(tab, q)
        r[name + '_get_branch_window'] = branch_query_window(tab, q)
    nrh = table['node_rules_handled']
    nrhb = r['node_rules_handled_get_branch'] = select([
        nrh.c.character,
        nrh.c.node,
        nrh.c.rulebook,
        nrh.c.rule,
        nrh.c.turn,
        nrh.c.tick
    ]).where(nrh.c.branch == bindparam('branch')).order_by(nrh.c.turn, nrh.c.tick)
    r['node_rules_handled_get_branch_until'] = branch_query_until(nrh, nrhb)
    r['node_rules_handled_get_branch_window'] = branch_query_window(nrh, nrhb)
    prh = table['portal_rules_handled']
    prhb = r['portal_rules_handled_get_branch'] = select([
        prh.c.character,
        prh.c.orig,
        prh.c.dest,
        prh.c.rulebook,
        prh.c.rule,
        prh.c.turn,
        prh.c.tick
    ]).where(prh.c.branch == bindparam('branch')).order_by(prh.c.turn, prh.c.tick)
    r['portal_rules_handled_get_branch_until'] = branch_query_until(prh, prhb)
    r['portal_rules_handled_get_branch_window'] = branch_query_window(prh, prhb)
    avs = table['avatars']
    avsb = r['avatars_get_branch'] = select([
        avs.c.character_graph,
        avs.c.avatar_graph,
        avs.c.avatar_node,
        avs.c.turn,
        avs.c.tick,
        avs.c.is_avatar
    ]).where(avs.c.branch == bindparam('branch'))
    r['avatars_get_branch_until'] = branch_query_until(avs, avsb)
    r['avatars_get_branch_window'] = branch_query_window(avs, avsb)
    crh = table['character_rules_handled']
    crhb = r['character_rules_handled_get_branch'] = select([
        crh.c.character,
        crh.c.rulebook,
        crh.c.rule,
        crh.c.turn,
        crh.c.tick
    ]).where(crh.c.branch == bindparam('branch')).order_by(crh.c.turn, crh.c.tick)
    r['character_rules_handled_get_branch_until'] = branch_query_until(crh, crhb)
    r['character_rules_handled_get_branch_window'] = branch_query_window(crh, crhb)
    avrh = table['avatar_rules_handled']
    avrhb = r['avatar_rules_handled_get_branch'] = select([
        avrh.c.character,
        avrh.c.rulebook,
        avrh.c.rule,
        avrh.c.graph,
        avrh.c.avatar,
        avrh.c.turn,
        avrh.c.tick
    ]).where(avrh.c.branch == bindparam('branch')).order_by(
        avrh.c.turn, avrh.c.tick
    )
    r['avatar_rules_handled_get_branch_until'] = branch_query_until(avrh, avrhb)
    r['avatar_rules_handled_get_branch_window'] = branch_query_window(avrh, avrhb)
    ctrh = table['character_thing_rules_handled']
    ctrhb = r['character_thing_rules_handled_get_branch'] = select([
        ctrh.c.character,
        ctrh.c.rulebook,
        ctrh.c.rule,
        ctrh.c.thing,
        ctrh.c.turn,
        ctrh.c.tick
    ]).where(ctrh.c.branch == bindparam('branch')).order_by(
        ctrh.c.turn, ctrh.c.tick
    )
    r['character_thing_rules_handled_get_branch_until'] = branch_query_until(ctrh, ctrhb)
    r['character_thing_rules_handled_get_branch_window'] = branch_query_window(ctrh, ctrhb)
    cplrh = table['character_place_rules_handled']
    cplrhb = r['character_place_rules_handled_get_branch'] = select([
        cplrh.c.character,
        cplrh.c.rulebook,
        cplrh.c.rule,
        cplrh.c.place,
        cplrh.c.turn,
        cplrh.c.tick
    ]).where(cplrh.c.branch == bindparam('branch')).order_by(
        cplrh.c.turn, cplrh.c.tick
    )
    r['character_place_rules_handled_get_branch_until'] = branch_query_until(cplrh, cplrhb)
    r['character_place_rules_handled_get_branch_window'] = branch_query_window(cplrh, cplrhb)
    cporh = table['character_portal_rules_handled']
    cporhb = r['character_portal_rules_handled_get_branch'] = select([
        cporh.c.character,
        cporh.c.rulebook,
        cporh.c.rule,
        cporh.c.orig,
        cporh.c.dest,
        cporh.c.turn,
        cporh.c.tick
    ]).where(cporh.c.branch == bindparam('branch')).order_by(
        cporh.c.turn, cporh.c.tick
    )
    r['character_portal_rules_handled_get_branch_until'] = branch_query_until(cporh, cporhb)
    r['character_portal_rules_handled_get_branch_window'] = branch_query_window(cporh, cporhb)


    branches = table['branches']

    r['branch_children'] = select(
        [branches.c.branch]
    ).where(
        branches.c.parent == bindparam('branch')
    )

    return r


if __name__ == '__main__':
    from sqlalchemy import MetaData
    from sqlalchemy.dialects.sqlite.pysqlite import SQLiteDialect_pysqlite
    meta = MetaData()
    r = {}
    table = tables_for_meta(meta)
    dia = SQLiteDialect_pysqlite()
    for (n, t) in table.items():
        r["create_" + n] = str(
            CreateTable(t).compile(dialect=dia)
        )
    index = indices_for_table_dict(table)
    for (n, x) in index.items():
        r["index_" + n] = str(
            CreateIndex(x).compile(dialect=dia)
        )
    query = queries(table)
    for (n, q) in query.items():
        r[n] = str(q.compile(dialect=dia))
    print(dumps(r, sort_keys=True, indent=4))
