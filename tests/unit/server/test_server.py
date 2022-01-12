from scanomatic.server.server import get_id


def test_get_id():
    id1 = get_id()
    id2 = get_id()
    assert id1 != id2
    assert len(id1) == len(id2) == 32
