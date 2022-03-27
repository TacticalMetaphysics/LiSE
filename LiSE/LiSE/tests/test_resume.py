from LiSE.examples.polygons import install
from LiSE import Engine


# TODO: use a test sim that does everything in every cache
def test_resume(tempdir):
    with Engine(tempdir) as eng:
        install(eng)
        eng.next_turn()
        last_branch, last_turn, last_tick = eng._btt()
    with Engine(tempdir) as eng:
        # tick gets bumped when we save the state of the randomizer
        assert eng._btt() == (last_branch, last_turn, last_tick + 1)
        curturn = eng.turn
        eng.next_turn()
        assert eng.turn == curturn + 1