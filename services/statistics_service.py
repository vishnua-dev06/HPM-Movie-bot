"""Statistics aggregation service for Admin Panel."""

from typing import Any, Dict
from database.broadcasts import BroadcastRepository
from database.movie_messages import MovieMessageRepository
from database.movies import MovieRepository
from database.subscriptions import SubscriptionRepository
from database.users import UserRepository
from database.years import YearRepository


class StatisticsService:
    """Service providing aggregated dashboard metrics."""

    @classmethod
    async def get_overview_statistics(cls) -> Dict[str, Any]:
        """Aggregate all key statistics from actual MongoDB collections."""
        total_users = await UserRepository.get_total_users_count()
        active_users = await UserRepository.get_active_users_count()
        blocked_users = await UserRepository.get_blocked_users_count()
        today_new_users = await UserRepository.get_today_new_users_count()

        total_movies = await MovieRepository.get_total_movies_count()
        latest_movies = await MovieRepository.get_movies_count_by_category("latest")
        dubbed_movies = await MovieRepository.get_movies_count_by_category("dubbed")

        total_years = await YearRepository.get_total_years_count()
        total_media = await MovieMessageRepository.get_total_media_count()
        total_broadcasts = await BroadcastRepository.get_total_broadcasts_count()

        sub2 = await SubscriptionRepository.get_sub2()
        sub2_status = "Not Configured"
        if sub2:
            sub2_status = "🟢 Enabled" if sub2.get("is_enabled", False) else "🔴 Disabled"

        return {
            "total_users": total_users,
            "active_users": active_users,
            "blocked_users": blocked_users,
            "today_new_users": today_new_users,
            "total_movies": total_movies,
            "latest_movies": latest_movies,
            "dubbed_movies": dubbed_movies,
            "total_years": total_years,
            "total_media": total_media,
            "total_broadcasts": total_broadcasts,
            "sub2_status": sub2_status,
        }
