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
    parser.add_argument(
        "--root-path",
        default=os.getenv("REDFOX_MCP_ROOT_PATH", ""),
        help="反向代理前缀（如 /tiktok）。SSE 会据此下发 /{prefix}/messages，"
             "否则客户端会 POST 到域名根路径 /messages",
    )
    args = parser.parse_args()
    uvicorn_config = {}
    if args.root_path:
        root_path = args.root_path if args.root_path.startswith("/") else f"/{args.root_path}"
        uvicorn_config["root_path"] = root_path.rstrip("/") or "/"
        uvicorn_config["proxy_headers"] = True
    run_kwargs = {"host": args.host, "port": args.port}
    if uvicorn_config:
        run_kwargs["uvicorn_config"] = uvicorn_config
    if args.transport == "http":
        set_transport("http")
        mcp.run(
            transport="streamable-http",
            path=args.path or "/mcp",
            **run_kwargs,
        )
    elif args.transport == "sse":
        # SSE 同样走 HTTP 请求头鉴权与多租户 client 缓存
        set_transport("http")
        mcp.run(
            transport="sse",
            path=args.path or "/sse",
            **run_kwargs,
        )
    else:
        mcp.run()
