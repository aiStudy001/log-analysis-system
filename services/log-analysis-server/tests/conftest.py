"""
Test Configuration and Fixtures
"""
import asyncio
import pytest
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_db_pool():
    """Mock database connection pool"""
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    pool.close = AsyncMock()

    # Mock connection
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock()
    conn.close = AsyncMock()

    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None

    return pool


@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_query_repo():
    """Mock QueryRepository"""
    repo = AsyncMock()
    repo.execute_sql = AsyncMock(return_value=([], 0.0))
    repo.execute_query = AsyncMock(return_value=[])
    return repo
