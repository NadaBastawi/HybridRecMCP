"""Post-deployment verification without disclosing or distributing the API key."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


def check(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("A valid HTTPS deployment URL is required")
    base = url.rstrip("/")
    for attempt in range(30):
        try:
            with urllib.request.urlopen(base + "/health", timeout=10) as response:
                data = json.load(response)
            if data.get("status") == "ok" and data.get("model_loaded") is True:
                break
        except (OSError, ValueError):
            pass
        if attempt == 29:
            raise RuntimeError("Deployed API did not become ready")
        time.sleep(5)
    try:
        urllib.request.urlopen(base + "/services", timeout=10)
    except urllib.error.HTTPError as error:
        if error.code == 401:
            print("Health verified; unauthenticated service access rejected (401).")
            return
        raise RuntimeError("Unexpected protected-route response") from None
    raise RuntimeError("Protected route accepted an unauthenticated request")


if __name__ == "__main__":
    check(os.environ["WEBAPP_URL"])
