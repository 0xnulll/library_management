from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import sys

app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(app_dir, "grpc_gen"))

# Configure structured logging before any other import that might log.
from app.core.logging import configure_logging  # noqa: E402

configure_logging()

from app.core.config import get_settings  # noqa: E402
from app.grpc_app.server import build_server, seed_admin  # noqa: E402
from app.infrastructure.db.session import Database  # noqa: E402

logger = logging.getLogger("library")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


async def serve() -> None:
    settings = get_settings()
    logger.info("starting", extra={"env": settings.environment, "bind": settings.grpc_bind})

    try:
        db = Database(settings)
    except Exception:
        logger.exception("failed to initialise database — check DATABASE_URL and migrations")
        raise

    try:
        seed_admin(db, settings, settings.admin_username, settings.admin_password)
    except Exception:
        # seed_admin already rolls back; log the failure with full context and
        # keep going — the server is still usable, admin can be seeded later.
        logger.exception("seed_admin raised an unexpected error; server will still start")

    server = build_server(settings, db.session)
    server.add_insecure_port(settings.grpc_bind)

    try:
        await server.start()
    except Exception:
        logger.exception("gRPC server failed to start")
        raise

    logger.info("listening", extra={"bind": settings.grpc_bind})

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    await stop.wait()
    logger.info("shutdown signal received — draining connections")

    try:
        await server.stop(grace=5)
    except Exception:
        logger.exception("error during server shutdown")
    finally:
        db.engine.dispose()
        logger.info("shutdown complete")


def main() -> None:
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(serve())


if __name__ == "__main__":
    main()
