"""Unit and integration tests for movie catalog and forward-based media storage."""

from unittest.mock import MagicMock
import pytest
from aiogram.types import Message, PhotoSize, Video
from database.movie_messages import MovieMessageRepository
from database.movies import MovieRepository
from database.years import YearRepository
from services.media_manager import MediaManager


@pytest.mark.asyncio
async def test_create_movie_and_query_by_category_year():
    """Verify movie creation and retrieval filtered by category and year."""
    movie_id = await MovieRepository.create_movie(
        title="Manjummel Boys",
        category="latest",
        year=2024,
    )
    assert movie_id is not None

    # Fetch movie
    movie = await MovieRepository.get_movie_by_id(movie_id)
    assert movie is not None
    assert movie["title"] == "Manjummel Boys"
    assert movie["category"] == "latest"
    assert movie["year"] == 2024

    # Count movies
    count = await MovieRepository.get_movies_count_by_category_and_year("latest", 2024)
    assert count == 1

    # Empty count for other category/year
    empty_count = await MovieRepository.get_movies_count_by_category_and_year("dubbed", 2024)
    assert empty_count == 0


@pytest.mark.asyncio
async def test_years_with_movies_dynamic_query():
    """Verify that user interface queries only return years with available movies."""
    await MovieRepository.create_movie("Aavesham", "latest", 2024)
    await MovieRepository.create_movie("Premalu", "latest", 2024)
    await MovieRepository.create_movie("Drishyam", "latest", 2013)
    await MovieRepository.create_movie("KGF Malayalam Dub", "dubbed", 2018)

    # Years for 'latest'
    latest_years = await YearRepository.get_years_with_movies("latest", only_enabled=False)
    assert latest_years == [2024, 2013]

    # Years for 'dubbed' must be completely separate
    dubbed_years = await YearRepository.get_years_with_movies("dubbed", only_enabled=False)
    assert dubbed_years == [2018]


@pytest.mark.asyncio
async def test_forward_based_media_extraction_and_storage():
    """Test extracting media attributes from Telegram message and storing references."""
    # Create fake Telegram photo message
    mock_message = MagicMock(spec=Message)
    mock_message.chat.id = 987654321
    mock_message.message_id = 42
    mock_message.media_group_id = "album_123"
    mock_message.caption = "Official Poster"
    mock_message.text = None

    fake_photo = MagicMock(spec=PhotoSize)
    fake_photo.file_id = "photo_file_id_xyz"
    fake_photo.file_unique_id = "photo_uniq_xyz"
    mock_message.photo = [fake_photo]
    mock_message.video = None
    mock_message.document = None
    mock_message.audio = None
    mock_message.animation = None

    # Extract media info
    extracted = MediaManager.extract_media_info(mock_message)
    assert extracted["source_chat_id"] == 987654321
    assert extracted["source_message_id"] == 42
    assert extracted["media_type"] == "photo"
    assert extracted["file_id"] == "photo_file_id_xyz"
    assert extracted["caption"] == "Official Poster"
    assert extracted["media_group_id"] == "album_123"

    # Create movie and store media references
    movie_id = await MovieRepository.create_movie("Bramayugam", "latest", 2024)
    stored_count = await MovieMessageRepository.add_movie_messages(movie_id, [extracted])
    assert stored_count == 1

    # Verify retrieval
    stored_msgs = await MovieMessageRepository.get_messages_by_movie_id(movie_id)
    assert len(stored_msgs) == 1
    assert stored_msgs[0]["source_message_id"] == 42
    assert stored_msgs[0]["source_chat_id"] == 987654321


@pytest.mark.asyncio
async def test_cascading_movie_deletion():
    """Verify deleting a movie also cascades and deletes its media messages."""
    movie_id = await MovieRepository.create_movie("Lucifer", "latest", 2019)
    fake_media = [
        {
            "source_chat_id": 123,
            "source_message_id": 1,
            "media_type": "photo",
            "file_id": "f1",
            "order": 0,
        },
        {
            "source_chat_id": 123,
            "source_message_id": 2,
            "media_type": "video",
            "file_id": "f2",
            "order": 1,
        },
    ]
    await MovieMessageRepository.add_movie_messages(movie_id, fake_media)

    messages_before = await MovieMessageRepository.get_messages_by_movie_id(movie_id)
    assert len(messages_before) == 2

    # Delete movie
    deleted = await MovieRepository.delete_movie(movie_id)
    assert deleted is True

    # Movie must no longer exist
    assert await MovieRepository.get_movie_by_id(movie_id) is None

    # Stored media messages must be gone
    messages_after = await MovieMessageRepository.get_messages_by_movie_id(movie_id)
    assert len(messages_after) == 0
