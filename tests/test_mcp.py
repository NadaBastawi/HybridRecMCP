"""Real SDK client -> stdio subprocess -> authenticated HTTP -> model."""

import os
import socket
import sys
import threading
import time
from pathlib import Path

import anyio
import pytest
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from main import create_app
from settings import Settings

KEY = "local-test-only-secret-42"


@pytest.fixture
def live_api(engine, tmp_path):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    app = create_app(Settings(api_key=KEY, log_dir=tmp_path), engine)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 20
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started, "Required local API failed to start"
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()


@pytest.mark.anyio
@pytest.mark.parametrize("key,expected_error", [(KEY, False), ("incorrect-key-long-enough", True)])
async def test_real_stdio_tools(live_api, key, expected_error):
    env = {**os.environ, "API_BASE": live_api, "API_KEY": key, "PYTHONUTF8": "1"}
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).resolve().parents[1] / "server.py")],
        env=env,
    )
    with anyio.fail_after(40):
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = await client.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "recommend_for_customer",
                    "recommend_for_new_customer",
                    "list_services",
                }
                requests = [
                    ("recommend_for_customer", {"customer_id": "C0001"}),
                    (
                        "recommend_for_new_customer",
                        {
                            "property_type": "residential_house",
                            "zip_code": "85743",
                            "building_age_years": 30,
                            "days_since_last_service": None,
                        },
                    ),
                    ("list_services", {}),
                ]
                for name, args in requests:
                    result = await client.call_tool(name, args)
                    assert bool(result.isError) == expected_error
                    text = " ".join(getattr(c, "text", "") for c in result.content)
                    assert key not in text
                    if expected_error:
                        assert "authentication" in text
                    else:
                        assert "illustrative" in text and "price_usd" in text
                        if name != "list_services":
                            assert "urgency_score" in text and "score" in text
                        if name == "recommend_for_new_customer":
                            assert "UNKNOWN" in text and "follow_up_question" in text
                if not expected_error:
                    missing = await client.call_tool(
                        "recommend_for_customer", {"customer_id": "C9999"}
                    )
                    assert missing.isError
                    invalid = await client.call_tool(
                        "recommend_for_new_customer",
                        {"property_type": "castle", "zip_code": "bad", "building_age_years": -1},
                    )
                    assert invalid.isError
