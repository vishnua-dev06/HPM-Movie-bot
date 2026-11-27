"""Tests for Railway and Multi-Cloud deployment compatibility."""

import asyncio
import json
import os
import pytest
from bot import start_optional_health_server
from config import settings


def test_railway_json_configuration():
    """Verify railway.json configuration file is valid and correctly formatted."""
    railway_path = os.path.join(os.path.dirname(__file__), "..", "railway.json")
    assert os.path.exists(railway_path), "railway.json must exist in project root"

    with open(railway_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "build" in data
    assert data["build"]["builder"] == "DOCKERFILE"
    assert "deploy" in data
    assert data["deploy"]["restartPolicyType"] == "ON_FAILURE"


@pytest.mark.asyncio
async def test_health_check_server_responds_200():
    """Verify lightweight HTTP health check server starts and responds 200 OK for Railway health checks."""
    test_port = 18888
    server = await start_optional_health_server(test_port)

    reader, writer = await asyncio.open_connection("127.0.0.1", test_port)
    request = b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
    writer.write(request)
    await writer.drain()

    response = await reader.read(1024)
    writer.close()
    await writer.wait_closed()

    server.close()
    await server.wait_closed()

    response_text = response.decode("utf-8")
    assert "200 OK" in response_text
    assert '{"status":"ok","bot":"active"}' in response_text
