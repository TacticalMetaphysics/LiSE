# This file is part of LiSE, a framework for life simulation games.
# Copyright (c) Zachary Spector,  zacharyspector@gmail.com
"""A script to generate the SQL needed for LiSE's database backend,
and output it in JSON form.

This uses sqlalchemy to describe the queries. It extends the module of
the same name in the ``allegedb`` package. If you change anything here,
you won't be able to use your changes until you put the generated JSON
where LiSE will look for it, as in:

``python3 sqlalchemy.py >sqlite.json``

"""
from collections import OrderedDict
from functools import partial
from sqlalchemy import *
from sqlalchemy.sql.ddl import CreateTable, CreateIndex


BaseColumn = Column
Column = partial(BaseColumn, nullable=False)


from json import dumps

import allegedb.alchemy

# Constants

TEXT = String(50)


def tables_for_meta(meta):
    """Return a dictionary full of all the tables I need for LiSE. Use the
    provided metadata object.

    """
    allegedb.alchemy.tables_for_meta(meta)

    # Table for global variables that are not sensitive to sim-time.
    Table(
        'universals', meta,
        Column('key', TEXT, primary_key=True),
        Column(
            'branch', TEXT, primary_key=True, default='trunk'
        ),
        Column('tick', Integer, primary_key=True, default=0),
        Column('value', TEXT, nullable=True)
    )

    Table(
        'rules', meta,
        Column('rule', TEXT, primary_key=True),
        Column('type', TEXT, default='character'),
        CheckConstraint("type IN ('character', 'node', 'portal')")
    )

    # Table grouping rules into lists called rulebooks.
    Table(
        'rulebooks', meta,
        Column('rulebook', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('tick', Integer, primary_key=True, default=0),
        Column('rules', TEXT, default='[]')
    )

    # Table for rules' triggers, those functions that return True only
    # when their rule should run (or at least check its prereqs).
    Table(
        'rule_triggers', meta,
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('tick', Integer, primary_key=True, default=0),
        Column('triggers', TEXT, default='[]'),
        ForeignKeyConstraint(
            ['rule'], ['rules.rule']
        )
    )

    # Table for rules' prereqs, functions with veto power over a rule
    # being followed
    Table(
        'rule_prereqs', meta,
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True, default='trunk'),
        Column('tick', Integer, primary_key=True, default=0),
        Column('prereqs', TEXT, default='[]'),
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
        Column('tick', Integer, primary_key=True, default=0),
        Column('actions', TEXT, default='[]'),
        ForeignKeyConstraint(
            ['rule'], ['rules.rule']
        )
    )

    # The top level of the LiSE world model, the character. Includes
    # rulebooks for the character itself, its avatars, and all the things,
    # places, and portals it contains--though those may have their own
    # rulebooks as well.

    def char_rb_tab(name):
        Table(
            name, meta,
            Column('character', TEXT, primary_key=True),
            Column('branch', TEXT, primary_key=True),
            Column('tick', INT, primary_key=True),
            Column('rulebook', TEXT),
            ForeignKeyConstraint(
                ['character'], ['graphs.graph']
            ),
            ForeignKeyConstraint(
                ['rulebook'], ['rulebooks.rulebook']
            )
        )

    char_rb_tab('character_rulebook')
    char_rb_tab('character_portal_rulebook')

    for rb in (
        'avatar_rulebook',
        'character_thing_rulebook',
        'character_place_rulebook',
    ):
        char_rb_tab(rb)

    # Rules handled within the rulebook associated with one node in
    # particular.
    Table(
        'node_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('node', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True),
        Column('tick', Integer, primary_key=True),
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
        Column('branch', TEXT, primary_key=True),
        Column('tick', Integer, primary_key=True),
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
        Column('tick', Integer, primary_key=True, default=0),
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
        Column('tick', Integer, primary_key=True, default=0),
        # when location is null, this node is not a thing, but a place
        Column('location', TEXT, nullable=True),
        # when next_location is not null, thing is en route between
        # location and next_location
        Column('next_location', TEXT, nullable=True),
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
    Table(
        'node_rulebook', meta,
        Column('character', TEXT, primary_key=True),
        Column('node', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True),
        Column('tick', INT, primary_key=True),
        Column('rulebook', TEXT),
        ForeignKeyConstraint(
            ['character', 'node'], ['nodes.graph', 'nodes.node']
        )
    )

    # The rulebook followed by a given Portal.
    #
    # "Portal" is LiSE's term for an edge in any of the directed
    # graphs it uses. The name is different to distinguish them from
    # Edge objects, which exist in an underlying object-relational
    # mapper called allegedb, and have a different API.
    Table(
        'portal_rulebook', meta,
        Column('character', TEXT, primary_key=True),
        Column('orig', TEXT, primary_key=True),
        Column('dest', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True),
        Column('tick', INT, primary_key=True),
        Column('rulebook', TEXT),
        ForeignKeyConstraint(
            ['character', 'orig', 'dest'],
            ['edges.graph', 'edges.orig', 'edges.dest']
        )
    )

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
    Table(
        'avatars', meta,
        Column('character_graph', TEXT, primary_key=True),
        Column('avatar_graph', TEXT, primary_key=True),
        Column('avatar_node', TEXT, primary_key=True),
        Column(
            'branch', TEXT, primary_key=True, default='trunk'
        ),
        Column('tick', Integer, primary_key=True, default=0),
        Column('is_avatar', Boolean),
        ForeignKeyConstraint(['character_graph'], ['graphs.graph']),
        ForeignKeyConstraint(
            ['avatar_graph', 'avatar_node'],
            ['nodes.graph', 'nodes.node']
        )
    )

    Table(
        'character_rules_handled', meta,
        Column('character', TEXT, primary_key=True),
        Column('rulebook', TEXT, primary_key=True),
        Column('rule', TEXT, primary_key=True),
        Column('branch', TEXT, primary_key=True),
        Column('tick', INT, primary_key=True),
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
        Column('branch', TEXT, primary_key=True),
        Column('tick', INT, primary_key=True),
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
        Column('branch', TEXT, primary_key=True),
        Column('tick', INT, primary_key=True),
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
        Column('branch', TEXT, primary_key=True),
        Column('tick', INT, primary_key=True),
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
        Column('branch', TEXT, primary_key=True),
        Column('tick', INT, primary_key=True),
        ForeignKeyConstraint(
            ['character', 'rulebook'], ['character_portal_rulebook.character', 'character_portal_rulebook.rulebook']
        ),
        ForeignKeyConstraint(
            ['character', 'orig', 'dest'], ['edges.graph', 'edges.orig', 'edges.dest']
        )
    )

    return meta.tables


def indices_for_table_dict(table):
    """Given the dictionary of tables returned by ``tables_for_meta``,
    return a dictionary of indices for the tables.

    """
    def handled_idx(prefix):
        """Return an index for the _rules_handled table with the given
        prefix.

        """
        t = table['{}_rules_handled'.format(prefix)]
        return Index(
            "{}_rules_handled_idx".format(prefix),
            t.c.character,
            t.c.rulebook,
            t.c.rule
        )

    r = allegedb.alchemy.indices_for_table_dict(table)

    for idx in (
            Index(
                'senses_idx',
                table['senses'].c.character,
                table['senses'].c.sense
            ),
            Index(
                'things_idx',
                table['things'].c.character,
                table['things'].c.thing
            ),
            Index(
                'avatars_idx',
                table['avatars'].c.character_graph,
                table['avatars'].c.avatar_graph,
                table['avatars'].c.avatar_node
            ),
            handled_idx('character'),
            handled_idx('avatar'),
            handled_idx('character_thing'),
            handled_idx('character_place'),
            handled_idx('character_portal'),
            Index(
                'node_rules_handled_idx',
                table['node_rules_handled'].c.character,
                table['node_rules_handled'].c.node,
                table['node_rules_handled'].c.rulebook,
                table['node_rules_handled'].c.rule
            ),
            Index(
                'portal_rules_handled_idx',
                table['portal_rules_handled'].c.character,
                table['portal_rules_handled'].c.orig,
                table['portal_rules_handled'].c.dest,
                table['portal_rules_handled'].c.rulebook,
                table['portal_rules_handled'].c.rule
            )
    ):
        r[idx.table.name] = idx

    return r


def queries(table):
    """Given dictionaries of tables and view-queries, return a dictionary
    of all the rest of the queries I need.

    """
    def update_where(updcols, wherecols):
        """Return an ``UPDATE`` statement that updates the columns ``updcols``
        when the ``wherecols`` match. Every column has a bound parameter of
        the same name.

        updcols are strings, wherecols are column objects

        """
        vmap = OrderedDict()
        for col in updcols:
            vmap[col] = bindparam(col)
        wheres = [
            c == bindparam(c.name) for c in wherecols
        ]
        tab = wherecols[0].table
        return tab.update().values(**vmap).where(and_(*wheres))

    r = allegedb.alchemy.queries_for_table_dict(table)

    for t in table.values():
        r[t.name + '_dump'] = select(list(t.c.values()))
        r[t.name + '_insert'] = t.insert().values(tuple(bindparam(cname) for cname in t.c.keys()))
        r[t.name + '_count'] = select([func.COUNT('*')]).select_from(t)

    univ = table['universals']
    r['universal_update'] = update_where(
        ['value'],
        [univ.c.key, univ.c.branch, univ.c.tick]
    )

    rulebooks = table['rulebooks']

    pr = table['portal_rulebook']

    r['portal_rulebook_update'] = update_where(
        ['rulebook'],
        [pr.c.character, pr.c.orig, pr.c.dest, pr.c.branch, pr.c.tick]
    )

    nr = table['node_rulebook']

    r['node_rulebook_update'] = update_where(
        ['rulebook'],
        [nr.c.character, nr.c.node, nr.c.branch, nr.c.tick]
    )

    r['del_char_things'] = table['things'].delete().where(
        table['things'].c.character == bindparam('character')
    )

    r['del_char_avatars'] = table['avatars'].delete().where(
        table['avatars'].c.character_graph == bindparam('character')
    )

    things = table['things']

    avatars = table['avatars']

    r['things_update'] = update_where(
        ['location', 'next_location'],
        [things.c.character, things.c.thing, things.c.branch, things.c.tick]
    )

    senses = table['senses']

    r['sense_update'] = update_where(
        ['function'],
        [senses.c.character, senses.c.sense, senses.c.branch, senses.c.tick]
    )

    r['avatar_update'] = update_where(
        ['is_avatar'],
        [
            avatars.c.character_graph,
            avatars.c.avatar_graph,
            avatars.c.avatar_node,
            avatars.c.branch,
            avatars.c.tick
        ]
    )

    rule_triggers = table['rule_triggers']
    rule_prereqs = table['rule_prereqs']
    rule_actions = table['rule_actions']
    r['rule_triggers'] = select([rule_triggers.c.triggers]).where(and_(
        rule_triggers.c.rule == bindparam('rule'),
        rule_triggers.c.branch == bindparam('branch'),
        rule_triggers.c.tick == bindparam('tick')
    ))
    r['rule_triggers_update'] = update_where(
        ['triggers'],
        [rule_triggers.c.rule, rule_triggers.c.branch, rule_triggers.c.tick]
    )
    r['rule_prereqs'] = select([rule_prereqs.c.prereqs]).where(and_(
        rule_prereqs.c.rule == bindparam('rule'),
        rule_prereqs.c.branch == bindparam('branch'),
        rule_triggers.c.tick == bindparam('tick')
    ))
    r['rule_prereqs_update'] = update_where(
        ['prereqs'],
        [rule_prereqs.c.rule, rule_prereqs.c.branch, rule_prereqs.c.tick]
    )
    r['rule_actions'] = select([rule_actions.c.actions]).where(and_(
        rule_actions.c.rule == bindparam('rule'),
        rule_actions.c.branch == bindparam('branch'),
        rule_actions.c.tick == bindparam('tick')
    ))
    r['rule_actions_update'] = update_where(
        ['actions'],
        [rule_actions.c.rule, rule_actions.c.branch, rule_actions.c.tick]
    )

    rules = table['rules']
    r['rules_update'] = update_where(
        ['type'],
        [rules.c.rule]
    )

    r['rulebooks'] = select([rulebooks.c.rulebook])

    r['rulebook_rules'] = select(
        [rulebooks.c.rules]
    ).where(and_(
        rulebooks.c.rulebook == bindparam('rulebook'),
        rulebooks.c.branch == bindparam('branch'),
        rulebooks.c.tick == bindparam('tick')
    ))

    r['rulebooks_update'] = update_where(
        ['rules'],
        [
            rulebooks.c.rulebook,
            rulebooks.c.branch,
            rulebooks.c.tick
        ]
    )

    for rbtabn in (
        'character_rulebook',
        'avatar_rulebook',
        'character_thing_rulebook',
        'character_place_rulebook',
        'character_portal_rulebook'
    ):
        t = table[rbtabn]
        r[rbtabn+'_update'] = update_where(
            ['rulebook'],
            [
                t.c.character,
                t.c.branch,
                t.c.tick
            ]
        )

    branches = table['branches']

    r['branch_children'] = select(
        [branches.c.branch]
    ).where(
        branches.c.parent == bindparam('branch')
    )

    return r


if __name__ == '__main__':
    e = create_engine('sqlite:///:memory:')
    meta = MetaData()
    r = {}
    table = tables_for_meta(meta)
    for (n, t) in table.items():
        r["create_" + n] = str(
            CreateTable(t).compile(
                dialect=e.dialect
            )
        )
        t.create(e)
    index = indices_for_table_dict(table)
    for (n, x) in index.items():
        r["index_" + n] = str(
            CreateIndex(x).compile(
                dialect=e.dialect
            )
        )
        x.create(e)
    query = queries(table)
    for (n, q) in query.items():
        r[n] = str(q.compile(dialect=e.dialect))
    print(dumps(r, sort_keys=True, indent=4))
