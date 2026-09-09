"""RedFox MCP 共享 server 工厂与启动入口"""

import argparse
import os

from fastmcp import FastMCP
from starlette.responses import JSONResponse

from redfox_mcp_core.runtime import set_transport


def create_server(name: str, version: str) -> FastMCP:
    """创建一个带 /health 路由的 FastMCP 实例，各平台 server 共用"""
    mcp = FastMCP(name)

    @mcp.custom_route("/health", methods=["GET"])
    async def _health(_request):
        return JSONResponse({"status": "ok", "server": name, "version": version})

    return mcp


def serve(mcp: FastMCP, prog: str, description: str) -> None:
    """启动 MCP server：默认 stdio；--transport http|sse 切换为远程多租户模式"""
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default=os.getenv("REDFOX_MCP_TRANSPORT", "stdio"),
        help="stdio=本地单用户；http=Streamable HTTP 多租户；sse=SSE 多租户（兼容旧客户端）",
    )
    parser.add_argument("--host", default=os.getenv("REDFOX_MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("REDFOX_MCP_PORT", "8000")))
    parser.add_argument(
        "--path",
        default=os.getenv("REDFOX_MCP_PATH"),
        help="HTTP/SSE 端点路径（http 默认 /mcp，sse 默认 /sse）",
    )
    args = parser.parse_args()
    if args.transport == "http":
        set_transport("http")
        mcp.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
            path=args.path or "/mcp",
        )
    elif args.transport == "sse":
        # SSE 同样走 HTTP 请求头鉴权与多租户 client 缓存
        set_transport("http")
        mcp.run(
            transport="sse",
            host=args.host,
            port=args.port,
            path=args.path or "/sse",
        )
    else:
        mcp.run()
