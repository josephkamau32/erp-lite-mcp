import os
import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, SalesOrder, InventoryItem
from src.server import mcp
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession

# Setup in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TEST_MCP_KEY = "test-mcp-secret-key-456"
TEST_ADMIN_KEY = "test-admin-secret-key-789"

@pytest.fixture(scope="function", autouse=True)
def setup_db(monkeypatch):
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr("src.tools.orders.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("src.tools.inventory.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("src.tools.requisitions.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr("src.server.SessionLocal", TestingSessionLocal)
    
    # Ensure fresh session manager for each test
    mcp._session_manager = None
    
    db = TestingSessionLocal()
    from datetime import date
    db.add(SalesOrder(order_id="SO-TEST-1", customer_name="Test Corp", status="open", order_date=date(2026, 8, 1), total_value=100.0))
    db.add(InventoryItem(material_id="MAT-TEST-1", description="Test Item", quantity_on_hand=50, reorder_point=100, warehouse="WH-1"))
    db.commit()
    yield db
    db.close()
    mcp._session_manager = None
    Base.metadata.drop_all(bind=engine)

@pytest.mark.anyio
async def test_mcp_rejects_missing_credentials(monkeypatch):
    """Requests to /mcp without credentials must be rejected with HTTP 401."""
    monkeypatch.setenv("MCP_API_KEY", TEST_MCP_KEY)
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        r = await client.post("http://127.0.0.1:8000/mcp")
        assert r.status_code == 401
        assert r.json() == {"error": "Unauthorized"}

@pytest.mark.anyio
async def test_mcp_rejects_invalid_token(monkeypatch):
    """Requests to /mcp with invalid Bearer token must be rejected with HTTP 401."""
    monkeypatch.setenv("MCP_API_KEY", TEST_MCP_KEY)
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
        headers={"Authorization": "Bearer wrong-token"}
    ) as client:
        r = await client.post("http://127.0.0.1:8000/mcp")
        assert r.status_code == 401
        assert r.json() == {"error": "Unauthorized"}

@pytest.mark.anyio
async def test_mcp_fails_closed_when_key_unset(monkeypatch):
    """If MCP_API_KEY is unset in the environment, /mcp must fail closed with HTTP 500."""
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
        headers={"Authorization": f"Bearer {TEST_MCP_KEY}"}
    ) as client:
        r = await client.post("http://127.0.0.1:8000/mcp")
        assert r.status_code == 500
        assert "MCP_API_KEY not set" in r.json().get("error", "")

@pytest.mark.anyio
async def test_mcp_succeeds_with_bearer_token(monkeypatch):
    """A valid Bearer token enables full MCP protocol communication and tool invocation."""
    monkeypatch.setenv("MCP_API_KEY", TEST_MCP_KEY)
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
        headers={"Authorization": f"Bearer {TEST_MCP_KEY}"}
    ) as client:
        async with mcp.session_manager.run():
            async with streamable_http_client("http://127.0.0.1:8000/mcp", http_client=client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    tool_names = [t.name for t in tools.tools]
                    assert "get_open_orders" in tool_names
                    assert "check_inventory" in tool_names
                    
                    # Call tool
                    res = await session.call_tool("check_inventory", {"material_id": "MAT-TEST-1"})
                    assert "MAT-TEST-1" in res.content[0].text

@pytest.mark.anyio
async def test_mcp_succeeds_with_x_mcp_api_key_header(monkeypatch):
    """A valid X-MCP-API-Key header also enables full MCP protocol communication."""
    monkeypatch.setenv("MCP_API_KEY", TEST_MCP_KEY)
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
        headers={"X-MCP-API-Key": TEST_MCP_KEY}
    ) as client:
        async with mcp.session_manager.run():
            async with streamable_http_client("http://127.0.0.1:8000/mcp", http_client=client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    tool_names = [t.name for t in tools.tools]
                    assert "get_open_orders" in tool_names

@pytest.mark.anyio
async def test_admin_routes_unaffected_by_mcp_api_key(monkeypatch):
    """Admin routes require ADMIN_API_KEY via X-Admin-Key and are not governed by MCP_API_KEY."""
    monkeypatch.setenv("MCP_API_KEY", TEST_MCP_KEY)
    monkeypatch.setenv("ADMIN_API_KEY", TEST_ADMIN_KEY)
    app = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        # Admin route without admin key (even if bearer token provided) -> 401 Unauthorized
        r1 = await client.get(
            "http://127.0.0.1:8000/admin/pending-requisitions",
            headers={"Authorization": f"Bearer {TEST_MCP_KEY}"}
        )
        assert r1.status_code == 401
        
        # Admin route with correct X-Admin-Key -> 200 OK
        r2 = await client.get(
            "http://127.0.0.1:8000/admin/pending-requisitions",
            headers={"X-Admin-Key": TEST_ADMIN_KEY}
        )
        assert r2.status_code == 200
        assert "pending_requisitions" in r2.json()

@pytest.mark.anyio
async def test_stdio_transport_unaffected_by_mcp_api_key(monkeypatch):
    """Stdio transport and internal server instance do not require MCP_API_KEY."""
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    # Stdio transport communicates directly through the underlying MCPServer,
    # completely bypassing streamable_http_app and MCPAuthMiddleware.
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "get_open_orders" in tool_names
    assert "check_inventory" in tool_names
    assert "create_requisition" in tool_names
