"""Movie verification and media delivery handler."""

from aiogram import Bot, F, Router, types
from config import settings
from database.activity_logs import ActivityLogRepository
from database.movies import MovieRepository
from database.users import UserRepository
from keyboards.user import build_force_sub_keyboard
from services.force_sub import ForceSubService
from services.media_manager import MediaManager
from utils.helpers import escape_html
from utils.logger import logger

router = Router(name="movie_delivery_router")


@router.callback_query(F.data.startswith("mov:"))
async def handle_movie_selection(callback: types.CallbackQuery, bot: Bot) -> None:
    """Handle movie selection by user: mov:{movie_id}."""
    movie_id = callback.data.split(":")[1]
    user = callback.from_user
    if not user:
        return

    # Fresh user activity update
    await UserRepository.update_last_active(user.id)

    # Fetch movie document
    movie = await MovieRepository.get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("❌ Movie not found or has been removed.", show_alert=True)
        return

    # Perform fresh subscription check
    check_result = await ForceSubService.verify_user_subscription(bot=bot, user_id=user.id)

    if not check_result.is_fully_satisfied:
        await _show_force_sub_prompt(callback, check_result, movie_id, movie)
        return

    # Subscription verified: deliver movie media
    await _deliver_movie_content(callback, bot, user.id, movie_id, movie)


@router.callback_query(F.data.startswith("try_sub:"))
async def handle_try_again_verification(callback: types.CallbackQuery, bot: Bot) -> None:
    """Handle TRY AGAIN verification button: try_sub:{movie_id}."""
    movie_id = callback.data.split(":")[1]
    user = callback.from_user
    if not user:
        return

    await UserRepository.update_last_active(user.id)

    movie = await MovieRepository.get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("❌ Movie not found or has been removed.", show_alert=True)
        return

    # Perform fresh subscription verification
    check_result = await ForceSubService.verify_user_subscription(bot=bot, user_id=user.id)

    if not check_result.is_fully_satisfied:
        missing_channels = []
        if not check_result.sub1_satisfied:
            missing_channels.append("Main Movie Channel")
        if not check_result.sub2_satisfied:
            missing_channels.append("Additional Channel")

        missing_str = " & ".join(missing_channels)
        alert_text = (
            f"❌ Verification failed! You still need to join: {missing_str}.\n\n"
            "Please join the channel(s) using the buttons below, then tap TRY AGAIN."
        )
        await callback.answer(alert_text, show_alert=True)
        return

    # Verification successful!
    await callback.answer("✅ Verification successful! Delivering your movie...", show_alert=False)

    # Deliver media
    await _deliver_movie_content(callback, bot, user.id, movie_id, movie)


async def _show_force_sub_prompt(
    callback: types.CallbackQuery,
    check_result,
    movie_id: str,
    movie: dict,
) -> None:
    """Display the Join Required Channels prompt with invite buttons."""
    movie_title = escape_html(movie.get("title", "Movie"))

    text = (
        "🔒 <b>JOIN REQUIRED CHANNELS</b>\n\n"
        f"To access and download <b>{movie_title}</b>, you must join our official channel(s) below.\n\n"
        "1️⃣ Tap each channel link below and join/request to join.\n"
        "2️⃣ Tap the <b>🔄 TRY AGAIN</b> button to verify and receive the movie instantly!"
    )

    keyboard = build_force_sub_keyboard(
        sub1_url=settings.SUB1_INVITE_URL,
        sub2_info=check_result.sub2_info,
        movie_id=movie_id,
    )

    if callback.message:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")

    await callback.answer()


async def _deliver_movie_content(
    callback: types.CallbackQuery,
    bot: Bot,
    user_id: int,
    movie_id: str,
    movie: dict,
) -> None:
    """Deliver stored media messages for the requested movie."""
    movie_title = escape_html(movie.get("title", "Movie"))
    year = movie.get("year", "N/A")

    if callback.message:
        await callback.message.answer(
            f"📥 <b>Preparing media files for:</b> {movie_title} ({year})...\n"
            "Sending files below:",
            parse_mode="HTML",
        )

    # Deliver media via copyMessage / copyMessages
    delivered_count, err = await MediaManager.deliver_movie_media(
        bot=bot,
        user_id=user_id,
        movie_id=movie_id,
    )

    if err:
        logger.warning("Delivery error for movie %s to user %d: %s", movie_id, user_id, err)
        if callback.message:
            await callback.message.answer(f"⚠️ Notice: {err}")
    else:
        logger.info(
            "Successfully delivered %d media message(s) for movie %s to user %d",
            delivered_count,
            movie_id,
            user_id,
        )

    # Log audit entry
    await ActivityLogRepository.log_activity(
        user_id=user_id,
        action="movie_download",
        details={"movie_id": str(movie_id), "title": movie.get("title"), "delivered": delivered_count},
    )
