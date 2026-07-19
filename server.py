#!/usr/bin/env python3
"""Run Market Swarm API server.

Usage:
    python server.py
    python server.py --port 8001 --host 0.0.0.0
    python server.py --reload    # Auto-reload on code changes
"""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Market Swarm API Server")
    parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on changes")
    args = parser.parse_args()

    uvicorn.run(
        "market_swarm.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
