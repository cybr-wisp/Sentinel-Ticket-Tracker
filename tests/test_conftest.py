


def test_fixture_wiring(ticket, regular_user):
    assert ticket.created_by == regular_user
    assert ticket.project is not None