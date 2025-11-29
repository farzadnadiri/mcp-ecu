import json
import threading
from typing import Optional, List

import typer

from .config import get_settings
from .bus import make_bus, read_frames, shutdown_bus
from .dbc import load_dbc, decode_frame
from .simulator.runner import run_simulator
from .server.fastmcp_server import main as run_server
from .obd import build_request


app = typer.Typer(help="MCP-CAN: simulate, inspect and serve CAN data over MCP.")


@app.command()
def server(port: Optional[int] = typer.Option(None, help="MCP server port (default from env)")) -> None:
    if port is not None:
        # Allow overriding via environment before importing server
        import os
        os.environ["MCP_CAN_MCP_PORT"] = str(port)
    run_server()


@app.command()
def simulate() -> None:
    """Run the ECU simulator using the configured DBC."""
    run_simulator()


@app.command()
def frames(seconds: float = typer.Option(1.0, help="Duration to listen on CAN bus")) -> None:
    """Capture raw CAN frames for a period and print JSON."""
    settings = get_settings()
    bus = make_bus(settings.can_interface, settings.can_channel)
    try:
        frames_list = read_frames(bus, seconds)
        out = [
            {
                "timestamp": f.timestamp,
                "arbitration_id": hex(f.arbitration_id),
                "data": list(f.data),
            }
            for f in frames_list
        ]
        typer.echo(json.dumps(out, indent=2))
    finally:
        shutdown_bus(bus)


@app.command()
def decode(id: str, data: str) -> None:
    """Decode a CAN frame given an ID and data bytes.

    id: CAN ID in hex (e.g. 0x100) or decimal.
    data: comma-separated bytes (e.g. 01,02,03,04) or space-separated hex (e.g. 01 02 03 04)
    """
    settings = get_settings()
    db = load_dbc(settings.dbc_path)
    arb_id = int(id, 16) if id.lower().startswith("0x") else int(id)
    bytes_list: List[int] = []
    if "," in data:
        bytes_list = [int(x.strip(), 16 if x.strip().startswith("0x") else 10) for x in data.split(",") if x.strip()]
    else:
        parts = [p for p in data.replace(",", " ").split(" ") if p]
        bytes_list = [int(x.strip(), 16 if all(c in "0123456789abcdefABCDEF" for c in x) else 10) for x in parts]
    decoded = decode_frame(db, arb_id, bytes(bytes_list))
    typer.echo(json.dumps(decoded, indent=2))


@app.command()
def monitor(signal: str, seconds: float = typer.Option(2.0, help="Duration to listen")) -> None:
    """Monitor a specific signal and print timestamped values."""
    settings = get_settings()
    db = load_dbc(settings.dbc_path)
    bus = make_bus(settings.can_interface, settings.can_channel)
    import time as _t
    end = _t.time() + seconds
    out: List[dict] = []
    try:
        while _t.time() < end:
            msg = bus.recv(timeout=0.1)
            if msg:
                try:
                    decoded = decode_frame(db, msg.arbitration_id, msg.data)
                    if signal in decoded:
                        out.append({"timestamp": msg.timestamp, "value": decoded[signal]})
                except Exception:
                    pass
        typer.echo(json.dumps(out, indent=2))
    finally:
        shutdown_bus(bus)


@app.command("obd-request")
def obd_request(
    service: str = typer.Option(..., "--service", "-s", help="Service ID (hex like 0x01)"),
    pid: Optional[str] = typer.Option(None, "--pid", "-p", help="PID hex like 0x0D"),
    timeout: float = 1.0,
) -> None:
    """Send a basic OBD-II request (single-frame) and print first response as JSON."""
    settings = get_settings()
    bus = make_bus(settings.can_interface, settings.can_channel)
    svc = int(service, 16) if service.lower().startswith("0x") else int(service)
    parsed_pid: Optional[int] = None
    if pid is not None:
        parsed_pid = int(pid, 16) if pid.lower().startswith("0x") else int(pid)
    arb_id, data = build_request(svc, parsed_pid)
    import can
    req = can.Message(arbitration_id=arb_id, data=data, is_extended_id=False)
    bus.send(req)
    msg = bus.recv(timeout=timeout)
    try:
        if not msg:
            typer.echo(json.dumps({"status": "timeout"}))
            raise typer.Exit(code=1)
        out = {
            "arbitration_id": hex(msg.arbitration_id),
            "data": [int(b) for b in msg.data],
        }
        typer.echo(json.dumps(out, indent=2))
    finally:
        shutdown_bus(bus)


@app.command("demo")
def demo(port: Optional[int] = typer.Option(None, help="Run simulator + server in one process (shared virtual bus)")) -> None:
    """Run simulator in a background thread and start the MCP server (helps on Windows with virtual backend)."""
    sim_thread = threading.Thread(target=run_simulator, daemon=True)
    sim_thread.start()
    if port is not None:
        import os
        os.environ["MCP_CAN_MCP_PORT"] = str(port)
    run_server()
