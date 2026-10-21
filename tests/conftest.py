"""Shared deterministic fixtures; required imports must fail rather than skip."""

import asyncio
import sys

import pytest
from fastapi.testclient import TestClient

from evaluate import fit_model
from generate_data import generate_customers, generate_interactions, generate_services_df
from main import create_app
from settings import Settings

TEST_KEY = "local-test-only-secret-42"


@pytest.fixture(scope="session")
def dataset():
    customers = generate_customers(60, region="both")
    interactions = generate_interactions(customers, 360)
    return customers, interactions, generate_services_df()


@pytest.fixture(scope="session")
def engine(dataset):
    return fit_model(*dataset)


@pytest.fixture
def api_client(engine, tmp_path):
    with TestClient(create_app(Settings(api_key=TEST_KEY, log_dir=tmp_path), engine)) as client:
        yield client


@pytest.fixture
def auth():
    return {"X-API-Key": TEST_KEY}


@pytest.fixture
def anyio_backend():
    if sys.platform == "win32":
        # Use the SDK's supported Popen fallback when overlapped named pipes are
        # unavailable in a restricted Windows runner. No protocol behavior is mocked.
        return "asyncio", {"loop_factory": asyncio.SelectorEventLoop}
    return "asyncio"
