from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import sys

app_dir = os.path.dirname(os.path.abspath(__file__))
grpc_gen_dir = os.path.join(app_dir, "grpc_gen")
sys.path.insert(0, grpc_gen_dir)

from app.core.config import get_settings  # noqa: E402
from app.grpc_app.server import build_server, seed_admin  # noqa: E402
from app.infrastructure.db.session import Database  # noqa: E402

logger = logging.getLogger("library")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


async def serve() -> None:
    settings = get_settings()
    db = Database(settings)

    server = build_server(settings, db.session)
    bind = settings.grpc_bind
    
    # Ensure default admin user is created
    seed_admin(db, settings, settings.admin_username, settings.admin_password)

    server.add_insecure_port(settings.grpc_bind)
    await server.start()
    logger.info("library gRPC server listening on %s", bind)

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()

    logger.info("shutting down...")
    await server.stop(grace=5)
    db.engine.dispose()


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve())


if __name__ == "__main__":
    main()
