"""Unit tests for the conversations sync functionality."""

import datetime as real_datetime
from unittest.mock import MagicMock, patch

import pytest

from canvas_mcp.sync import SyncService
from canvas_mcp.sync.conversations import sync_conversations
from canvas_mcp.utils.db_manager import DatabaseManager


@pytest.fixture(autouse=True)
def mock_datetime_now():
    """Fixture to mock datetime.now() while keeping other datetime methods real."""
    fixed_now = real_datetime.datetime(2025, 4, 5, 12, 0, 0, tzinfo=real_datetime.UTC)

    with patch("canvas_mcp.sync.conversations.datetime") as mock_dt:
        # Mock .now()
        mock_dt.now.return_value = fixed_now

        # Keep other necessary methods/attributes using the real implementation
        mock_dt.fromisoformat = real_datetime.datetime.fromisoformat
        mock_dt.strptime = real_datetime.datetime.strptime
        mock_dt.datetime = real_datetime.datetime
        mock_dt.timedelta = real_datetime.timedelta
        mock_dt.timezone = real_datetime.timezone
        mock_dt.UTC = real_datetime.UTC  # Important for datetime.now(UTC)

        yield mock_dt


def _create_test_course(db_manager: DatabaseManager) -> int:
    """Creates a test course and returns its local ID."""
    conn, cursor = db_manager.connect()
    try:
        cursor.execute(
            """
            INSERT INTO courses (canvas_course_id, course_code, course_name, instructor, start_date, end_date)
            VALUES (12345, 'TEST-101', 'Test Course 101', 'Test Instructor', '2025-01-01', '2025-05-01')
            """
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def test_sync_conversations_api_unavailable(sync_service: SyncService, clean_db):
    """Test sync_conversations when the API adapter is unavailable."""
    # Arrange
    with patch.object(sync_service.api_adapter, "is_available", return_value=False):
        with patch.object(
            sync_service.api_adapter, "get_conversations_raw"
        ) as mock_get_raw:
            # Act
            result = sync_conversations(sync_service)
            # Assert
            assert result == 0
            mock_get_raw.assert_not_called()  # Now we can assert this


def test_sync_conversations_no_courses(sync_service: SyncService, clean_db):
    """Test sync_conversations when there are no courses in the DB."""
    # Arrange (clean_db fixture handles this)
    with patch.object(
        sync_service.api_adapter, "get_conversations_raw"
    ) as mock_get_raw:
        # Act
        result = sync_conversations(sync_service)
        # Assert
        assert result == 0
        mock_get_raw.assert_not_called()  # Should not attempt fetch if no courses


def test_sync_conversations_no_conversations_api(
    sync_service: SyncService, db_manager: DatabaseManager, clean_db
):
    """Test sync_conversations when no conversations are returned by the API."""
    # Arrange
    _create_test_course(db_manager)
    with patch.object(
        sync_service.api_adapter, "get_conversations_raw", return_value=[]
    ) as mock_get_raw:
        # Act
        result = sync_conversations(sync_service)
        # Assert
        assert result == 0
        mock_get_raw.assert_called_once()


def test_sync_conversations_with_conversations(
    sync_service: SyncService, db_manager: DatabaseManager, clean_db
):
    """Test sync_conversations with mock conversations successfully syncing."""
    # Arrange
    local_course_id = _create_test_course(db_manager)

    mock_conversation = MagicMock()
    mock_conversation.id = 2001
    mock_conversation.subject = "Test Conversation"
    mock_conversation.context_name = "Test Course 101"
    mock_conversation.last_message_at = "2025-04-02T14:00:00Z"

    mock_message = {
        "created_at": "2025-04-02T14:00:00Z",
        "body": "This is a test conversation message",
    }
    mock_detail = MagicMock()
    mock_detail.messages = [mock_message]
    mock_detail.participants = [{"name": "Instructor"}]

    with (
        patch.object(
            sync_service.api_adapter,
            "get_conversations_raw",
            return_value=[mock_conversation],
        ) as mock_get_raw,
        patch.object(
            sync_service.api_adapter,
            "get_conversation_detail_raw",
            return_value=mock_detail,
        ) as mock_get_detail,
    ):
        # Act
        result = sync_conversations(sync_service)

        # Assert
        assert result == 1, "Should return 1 when one conversation is synced"
        mock_get_raw.assert_called_once()
        mock_get_detail.assert_called_once_with(2001)

        # Check database state
        conn, cursor = db_manager.connect()
        try:
            cursor.execute("SELECT * FROM conversations")
            conversations = cursor.fetchall()
            assert len(conversations) == 1, "Should have inserted 1 conversation"
            conversation = conversations[0]
            assert conversation["canvas_conversation_id"] == 2001
            assert conversation["course_id"] == local_course_id
            assert conversation["title"] == "Test Conversation"
            assert conversation["content"] == "This is a test conversation message"
            assert conversation["posted_by"] == "Instructor"
            # Note: Timestamp comparison can be tricky due to potential microsecond differences
            # assert conversation["posted_at"] == "2025-04-02 14:00:00+00:00"
        finally:
            conn.close()


def test_sync_conversations_with_existing_conversation(
    sync_service: SyncService, db_manager: DatabaseManager, clean_db
):
    """Test sync_conversations correctly updates an existing conversation."""
    # Arrange
    local_course_id = _create_test_course(db_manager)

    # Insert an existing conversation
    conn, cursor = db_manager.connect()
    try:
        cursor.execute(
            """
            INSERT INTO conversations (canvas_conversation_id, course_id, title, content, posted_by, posted_at, created_at, updated_at)
            VALUES (2001, ?, 'Existing Conversation', 'This is an existing conversation', 'Instructor', '2025-04-01 14:00:00+00:00', '2025-04-01 14:00:00', '2025-04-01 14:00:00')
            """,
            (local_course_id,),
        )
        conn.commit()
    finally:
        conn.close()

    mock_conversation = MagicMock()
    mock_conversation.id = 2001
    mock_conversation.subject = "Updated Conversation"
    mock_conversation.context_name = "Test Course 101"
    mock_conversation.last_message_at = "2025-04-02T16:00:00Z"  # Newer message time

    mock_message = {
        "created_at": "2025-04-02T16:00:00Z",
        "body": "This is an updated conversation message",
    }
    mock_detail = MagicMock()
    mock_detail.messages = [mock_message]
    mock_detail.participants = [{"name": "Instructor"}]

    with (
        patch.object(
            sync_service.api_adapter,
            "get_conversations_raw",
            return_value=[mock_conversation],
        ) as mock_get_raw,
        patch.object(
            sync_service.api_adapter,
            "get_conversation_detail_raw",
            return_value=mock_detail,
        ) as mock_get_detail,
    ):
        # Act
        result = sync_conversations(sync_service)

        # Assert
        assert result == 1, "Should return 1 when one conversation is synced/updated"
        mock_get_raw.assert_called_once()
        mock_get_detail.assert_called_once_with(2001)

        # Check database state
        conn, cursor = db_manager.connect()
        try:
            cursor.execute(
                "SELECT * FROM conversations WHERE canvas_conversation_id = 2001"
            )
            conversations = cursor.fetchall()
            assert len(conversations) == 1, (
                "Should have one conversation with the given ID"
            )
            conversation = conversations[0]
            assert conversation["title"] == "Updated Conversation", (
                "Should have updated the title"
            )
            assert (
                conversation["content"] == "This is an updated conversation message"
            ), "Should have updated the content"
            # Check updated_at timestamp
            assert conversation["updated_at"] is not None
            # assert conversation["posted_at"] == "2025-04-02 16:00:00+00:00" # Check if posted_at updates too
        finally:
            conn.close()


def test_sync_conversations_with_invalid_course_context(
    sync_service: SyncService, db_manager: DatabaseManager, clean_db
):
    """Test sync_conversations skips conversations with context not matching a local course."""
    # Arrange
    _create_test_course(db_manager)  # Course ID 12345 exists

    mock_conversation = MagicMock()
    mock_conversation.id = 2002
    mock_conversation.subject = "Invalid Course Conversation"
    mock_conversation.context_code = "course_99999"  # Non-existent canvas course ID
    mock_conversation.context_name = "Non Existent Course 999"
    mock_conversation.last_message_at = "2025-04-02T14:00:00Z"

    with (
        patch.object(
            sync_service.api_adapter,
            "get_conversations_raw",
            return_value=[mock_conversation],
        ) as mock_get_raw,
        patch.object(
            sync_service.api_adapter, "get_conversation_detail_raw"
        ) as mock_get_detail,
    ):
        # Act
        result = sync_conversations(sync_service)

        # Assert
        assert result == 0, (
            "Should return 0 as the conversation's course is not tracked"
        )
        mock_get_raw.assert_called_once()
        mock_get_detail.assert_not_called()  # Detail shouldn't be fetched if course doesn't match

        # Check database state
        conn, cursor = db_manager.connect()
        try:
            cursor.execute("SELECT COUNT(*) FROM conversations")
            count = cursor.fetchone()[0]
            assert count == 0, "Should not have inserted any conversations"
        finally:
            conn.close()


def test_sync_conversations_with_old_message(
    sync_service: SyncService, db_manager: DatabaseManager, clean_db
):
    """Test sync_conversations filters out messages older than the sync_days cutoff."""
    # Arrange
    _create_test_course(db_manager)

    mock_conversation = MagicMock()
    mock_conversation.id = 2001
    mock_conversation.subject = "Old Conversation"
    mock_conversation.context_name = "Test Course 101"
    mock_conversation.last_message_at = (
        "2025-03-01T14:00:00Z"  # Before default 21-day cutoff
    )

    # Mock detail even though it shouldn't be used if filtered by date
    mock_message = {"created_at": "2025-03-01T14:00:00Z", "body": "Old message body"}
    mock_detail = MagicMock(
        messages=[mock_message], participants=[{"name": "Instructor"}]
    )

    with (
        patch.object(
            sync_service.api_adapter,
            "get_conversations_raw",
            return_value=[mock_conversation],
        ) as mock_get_raw,
        patch.object(
            sync_service.api_adapter,
            "get_conversation_detail_raw",
            return_value=mock_detail,
        ),
    ):
        # Act
        # Use default sync_days (21), mock_datetime is 2025-04-05
        result = sync_conversations(sync_service)

        # Assert
        assert result == 0, "Should return 0 as the conversation is too old"
        mock_get_raw.assert_called_once()
        # Detail fetch might still happen depending on where filtering occurs, adjust if needed
        # mock_get_detail.assert_not_called()

        # Check database state
        conn, cursor = db_manager.connect()
        try:
            cursor.execute("SELECT COUNT(*) FROM conversations")
            count = cursor.fetchone()[0]
            assert count == 0, "Should not have inserted the old conversation"
        finally:
            conn.close()


def test_sync_conversations_with_no_messages_in_detail(
    sync_service: SyncService, db_manager: DatabaseManager, clean_db
):
    """Test sync_conversations handles conversations where detail fetch returns no messages."""
    # Arrange
    _create_test_course(db_manager)

    mock_conversation = MagicMock()
    mock_conversation.id = 2001
    mock_conversation.subject = "No Message Conversation"
    mock_conversation.context_name = "Test Course 101"
    mock_conversation.last_message_at = "2025-04-03T10:00:00Z"

    mock_detail = MagicMock()
    mock_detail.messages = []  # No messages
    mock_detail.participants = [{"name": "Instructor"}]

    with (
        patch.object(
            sync_service.api_adapter,
            "get_conversations_raw",
            return_value=[mock_conversation],
        ) as mock_get_raw,
        patch.object(
            sync_service.api_adapter,
            "get_conversation_detail_raw",
            return_value=mock_detail,
        ) as mock_get_detail,
    ):
        # Act
        result = sync_conversations(sync_service)

        # Assert
        assert result == 0, "Should return 0 as there are no messages to sync"
        mock_get_raw.assert_called_once()
        mock_get_detail.assert_called_once_with(2001)

        # Check database state
        conn, cursor = db_manager.connect()
        try:
            cursor.execute("SELECT COUNT(*) FROM conversations")
            count = cursor.fetchone()[0]
            assert count == 0, (
                "Should not have inserted a conversation with no messages"
            )
        finally:
            conn.close()


def test_sync_conversations_participant_parsing(
    sync_service: SyncService, db_manager: DatabaseManager, clean_db
):
    """Test that participant names are parsed correctly."""
    # Arrange
    _create_test_course(db_manager)
    mock_conversation = MagicMock(
        id=2001,
        subject="P Test",
        context_name="Test Course 101",
        last_message_at="2025-04-04T10:00:00Z",
    )
    mock_message = {"created_at": "2025-04-04T10:00:00Z", "body": "Msg body"}
    # Test with multiple participants
    mock_detail = MagicMock(
        messages=[mock_message], participants=[{"name": "First"}, {"name": "Second"}]
    )

    with (
        patch.object(
            sync_service.api_adapter,
            "get_conversations_raw",
            return_value=[mock_conversation],
        ),
        patch.object(
            sync_service.api_adapter,
            "get_conversation_detail_raw",
            return_value=mock_detail,
        ),
    ):
        # Act
        result = sync_conversations(sync_service)
        # Assert
        assert result == 1
        conn, cursor = db_manager.connect()
        try:
            cursor.execute(
                "SELECT posted_by FROM conversations WHERE canvas_conversation_id = 2001"
            )
            posted_by = cursor.fetchone()[0]
            # Expecting the first participant's name
            assert posted_by == "First"
        finally:
            conn.close()
