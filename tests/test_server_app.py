import os

from mcp_can.server.fastmcp_server import create_app


def test_create_app_returns_fastmcp():
    # Ensure DBC path is resolvable during CI/test runs
    dbc_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vehicle.dbc"))
    os.environ["MCP_CAN_DBC_PATH"] = dbc_path
    app = create_app()
    # Avoid running the server; just ensure creation works
    assert hasattr(app, "tool") and hasattr(app, "run")


