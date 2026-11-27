"""Main entry point for Malayalam Movie Bot with multi-admin support, user log channel, broadcast recovery, and Railway/Koyeb hosting."""

import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import settings
from database.mongodb import Database
from handlers.add_movie import router as add_movie_router
from handlers.admin_dashboard import router as admin_dashboard_router
from handlers.admin_management import router as admin_management_router
from handlers.broadcast import router as broadcast_router
from handlers.log_channel_settings import router as log_channel_settings_router
from handlers.manage_movies import router as manage_movies_router
from handlers.manage_years import router as manage_years_router
from handlers.menu_settings import router as menu_settings_router
from handlers.movie_catalog import router as movie_catalog_router
from handlers.movie_delivery import router as movie_delivery_router
from handlers.start import router as start_router
from handlers.statistics import router as statistics_router
from handlers.subscription import router as subscription_router
from handlers.user_menu import router as user_menu_router
from middlewares.admin_auth import AdminAuthMiddleware
from middlewares.rate_limit import RateLimitMiddleware
from services.broadcast_service import BroadcastService
from utils.logger import logger


async def start_optional_health_server(port: int):
    """Start lightweight non-blocking HTTP health check responder if PORT is provided by hosting (Railway/Cloud)."""
    async def handle_http(reader, writer):
        try:
            await reader.read(512)
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: 30\r\n"
                "Connection: close\r\n\r\n"
                '{"status":"ok","bot":"active"}'
            )
            writer.write(response.encode("utf-8"))
            await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(handle_http, "0.0.0.0", port)
    logger.info("Railway/Cloud HTTP health-check responder active on 0.0.0.0:%d", port)
    return server


async def main() -> None:
    """Initialize bot, connect to database, register handlers, resume broadcasts, and start long polling."""
    logger.info("Initializing Malayalam Movie Bot with Multi-Cloud Hosting Architecture (Railway + Koyeb)...")

    # Validate essential environment variables
    try:
        settings.validate()
    except ValueError as val_err:
        logger.critical("Configuration validation error:\n%s", val_err)
        sys.exit(1)

    # Initialize Database connection & seed initial administrators
    try:
        await Database.connect()
    except Exception as db_err:
        logger.critical("Could not connect to MongoDB Atlas: %s", db_err)
        sys.exit(1)

    # Initialize Bot and Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register Middlewares
    rate_limiter = RateLimitMiddleware(limit_seconds=0.4)
    admin_auth = AdminAuthMiddleware()

    # Outer middlewares for callback queries and messages
    dp.callback_query.outer_middleware(rate_limiter)
    dp.callback_query.outer_middleware(admin_auth)
    dp.message.outer_middleware(rate_limiter)
    dp.message.outer_middleware(admin_auth)

    # Register Routers
    # Admin Routers first
    dp.include_router(admin_dashboard_router)
    dp.include_router(admin_management_router)
    dp.include_router(log_channel_settings_router)
    dp.include_router(add_movie_router)
    dp.include_router(manage_movies_router)
    dp.include_router(manage_years_router)
    dp.include_router(menu_settings_router)
    dp.include_router(subscription_router)
    dp.include_router(broadcast_router)
    dp.include_router(statistics_router)

    # User Routers
    dp.include_router(start_router)
    dp.include_router(user_menu_router)
    dp.include_router(movie_catalog_router)
    dp.include_router(movie_delivery_router)

    logger.info("Registered all routers and middlewares.")

    # Drop any pending updates on startup to avoid processing outdated messages
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning("Could not drop pending updates: %s", e)

    # Resume any interrupted broadcast jobs from a previous server restart
    try:
        resumed = await BroadcastService.resume_interrupted_broadcasts(bot)
        if resumed:
            logger.info("Resumed %d interrupted broadcast job(s).", resumed)
    except Exception as resume_err:
        logger.error("Error checking for interrupted broadcasts: %s", resume_err)

    # Start optional lightweight health server if Railway/Cloud injected PORT
    health_server = None
    if settings.PORT > 0:
        try:
            health_server = await start_optional_health_server(settings.PORT)
        except Exception as hs_err:
            logger.warning("Could not bind health-check server on port %d: %s", settings.PORT, hs_err)

    # Resolve used update types including chat_join_request
    allowed_updates = dp.resolve_used_update_types()
    if "chat_join_request" not in allowed_updates:
        allowed_updates.append("chat_join_request")

    logger.info("Starting long polling with allowed updates: %s", allowed_updates)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=allowed_updates,
            close_bot_session=True,
        )
    finally:
        logger.info("Shutting down bot...")
        if health_server:
            health_server.close()
            await health_server.wait_closed()
        await Database.close()
        await bot.session.close()
        logger.info("Bot stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot process terminated.")
