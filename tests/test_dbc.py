import os

from mcp_can.dbc import load_dbc


def test_dbc_loads_and_has_messages():
    db_path = os.path.join(os.path.dirname(__file__), "..", "vehicle.dbc")
    db_path = os.path.abspath(db_path)
    db = load_dbc(db_path)
    assert db is not None
    names = {m.name for m in db.messages}
    assert {"ENGINE_STATUS", "ABS_STATUS", "AIRBAG_STATUS", "BODY_STATUS"}.issubset(names)


