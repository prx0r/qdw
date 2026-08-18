import asyncio
from mcp import Client
from qdw.interfaces.mcp_server import mcp

def test_mcp_real_protocol():
    async def run():
        async with Client(mcp) as client:
            tools=await client.list_tools()
            values=getattr(tools,"tools",tools)
            names={getattr(t,"name",None) for t in values}
            assert "qdw_get_status" in names
            result=await client.call_tool("qdw_get_status",{})
            assert result is not None
    asyncio.run(run())
