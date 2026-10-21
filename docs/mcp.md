# MCP integration

The server uses the official Model Context Protocol Python SDK, pinned to tested
`mcp==1.30.0` on its supported 1.x maintenance line. Protocol framing and initialization
are handled by the SDK. This deliberately retains the ClientSession/FastMCP interface;
a future 2.x migration requires a separate compatibility test.

## Setup

1. Install `requirements-api.txt` (or the dev/demo superset).
2. Set a strong local API_KEY in `.env`; generate/evaluate/train as described in README.
3. Start `python -m uvicorn main:app --host 127.0.0.1 --port 8000`.
4. Configure a stdio-capable MCP client to launch the server with absolute paths.

Example client configuration (replace every placeholder locally; never commit a real key):

```json
{
  "mcpServers": {
    "hybrid-recommendations": {
      "command": "C:/path/to/HybridRecMCP/.venv/Scripts/python.exe",
      "args": ["C:/path/to/HybridRecMCP/server.py"],
      "env": {
        "API_BASE": "http://127.0.0.1:8000",
        "API_KEY": "REPLACE_WITH_YOUR_LOCAL_SECRET"
      }
    }
  }
}
```

On Linux/macOS use the absolute `.venv/bin/python` path. Environment variables take
precedence over the repository-root `.env`; client working directory does not matter.
Secrets belong in the client's private configuration, not a checked-in example.
API_BASE must be HTTPS for remote hosts. The bridge does not train or import the model.

## Tools

- `recommend_for_customer`: customer_id, season, days_since_last_service, top_n.
- `recommend_for_new_customer`: property_type, zip_code, building_age_years, region,
  season, days_since_last_service, top_n.
- `list_services`: no arguments; returns a services list and independent-demo disclaimer.

New-customer timing may be explicit null when unknown, returning null urgency and
UNKNOWN priority without fabricating a previous service date. Omitting it preserves
the existing numeric default. Service-specific context and follow_up_question are
rule-grounded discussion prompts, not feature-attribution claims.

Responses contain structured JSON and readable SDK text content. Recommendations use
`score`, not `recommendation_score`. Prices always include their illustrative basis.
The bridge validates API responses and forwards X-API-Key on every request, including
catalog calls. HTTP/auth/validation failures surface as MCP error results. There are
no booking, messaging, infestation-diagnosis or CRM tools.

## Example agent interaction

User: “For synthetic customer C0001 in summer, show five service ideas and make clear
that prices and priority estimates are illustrative.”

Expected tool call:

```json
{"name":"recommend_for_customer","arguments":{"customer_id":"C0001","season":"summer","top_n":5}}
```

The agent should summarize the actual tool output and limitations rather than invent
an infestation, appointment, treatment requirement, partnership or financial benefit.

## Verification

`python -m pytest tests/test_mcp.py -v` launches an authenticated local Uvicorn service,
starts the stdio server as a subprocess, connects the actual SDK ClientSession,
initializes it, lists tools and invokes all three. It verifies correct contracts,
price qualifiers, missing-customer/invalid-input errors and wrong-key errors. This is
protocol/client compatibility verification; no particular commercial AI desktop client
or live LLM conversation is claimed to have been tested.

On this restricted Windows verification runner, overlapped named-pipe creation is
unavailable. Tests select a SelectorEventLoop so the official SDK uses its documented
Popen fallback. The actual stdio bytes, client handshake and HTTP calls remain real;
no essential test is skipped and protocol behavior is not mocked.
