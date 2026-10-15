import argparse
import asyncio
import selectors
import sys
from collections.abc import Callable

import uvicorn


def _windows_selector_loop() -> asyncio.AbstractEventLoop:
    """创建 psycopg 异步连接所需的 Windows Selector 事件循环。"""

    return asyncio.SelectorEventLoop(selectors.SelectSelector())


def main() -> None:
    """启动 TravelMind API 服务。"""

    parser = argparse.ArgumentParser(description="启动 TravelMind API 服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    loop: str | Callable[[], asyncio.AbstractEventLoop]
    loop = _windows_selector_loop if sys.platform == "win32" else "auto"

    uvicorn.run(
        "travel_mind.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        loop=loop,
    )


if __name__ == "__main__":
    main()
