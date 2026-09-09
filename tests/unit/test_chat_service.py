import unittest
from app.application.services.chat_service import ChatService
from app.core.exceptions import AuthorizationError
from app.domain.entities.room import RoomEntity
from tests.conftest import FakeMessageBroker, FakeMessageRepository, FakeRoomRepository


class TestChatService(unittest.IsolatedAsyncioTestCase):
    """Unit tests for ChatService use cases using in-memory Fakes."""

    async def asyncSetUp(self):
        self.message_repo = FakeMessageRepository()
        self.room_repo = FakeRoomRepository()
        self.broker = FakeMessageBroker()
        self.chat_service = ChatService(self.message_repo, self.room_repo, self.broker)

        # Setup room with members 10 and 20
        self.room = await self.room_repo.create(RoomEntity(name="General Chat", is_private=False))
        await self.room_repo.add_member(self.room.id, 10)
        await self.room_repo.add_member(self.room.id, 20)

    async def test_send_message_success_and_publishes_to_broker(self):
        msg = await self.chat_service.send_message(
            content="Hello world!",
            room_id=self.room.id,
            sender_id=10,
            sender_username="user10",
        )

        self.assertEqual(msg.content, "Hello world!")
        self.assertEqual(msg.room_id, self.room.id)
        self.assertEqual(msg.sender_id, 10)
        self.assertEqual(msg.sender_username, "user10")

        # Verify message was published through abstract broker
        self.assertEqual(len(self.broker.published), 1)
        channel, payload = self.broker.published[0]
        self.assertEqual(channel, f"room:{self.room.id}")
        self.assertEqual(payload["content"], "Hello world!")
        self.assertEqual(payload["username"], "user10")

    async def test_send_message_non_member_raises_authorization_error(self):
        # User 99 is not in the room
        with self.assertRaises(AuthorizationError):
            await self.chat_service.send_message(
                content="Sneaky message",
                room_id=self.room.id,
                sender_id=99,
                sender_username="intruder",
            )
        # Ensure nothing was published
        self.assertEqual(len(self.broker.published), 0)

    async def test_get_messages_cursor_pagination(self):
        # Populate 5 messages
        for i in range(1, 6):
            await self.chat_service.send_message(
                content=f"Message {i}",
                room_id=self.room.id,
                sender_id=10,
                sender_username="user10",
            )

        # Fetch first page with limit=2 (most recent)
        page1 = await self.chat_service.get_messages(
            room_id=self.room.id,
            user_id=10,
            limit=2,
        )
        self.assertEqual(len(page1.items), 2)
        self.assertTrue(page1.has_more)
        self.assertIsNotNone(page1.next_cursor)

        # Fetch second page using next_cursor
        page2 = await self.chat_service.get_messages(
            room_id=self.room.id,
            user_id=10,
            limit=2,
            before_id=page1.next_cursor,
        )
        self.assertEqual(len(page2.items), 2)
        self.assertTrue(page2.has_more)

        # Ensure no overlapping messages between pages
        p1_ids = {m.id for m in page1.items}
        p2_ids = {m.id for m in page2.items}
        self.assertEqual(p1_ids & p2_ids, set())

    async def test_get_messages_non_member_raises_authorization_error(self):
        with self.assertRaises(AuthorizationError):
            await self.chat_service.get_messages(room_id=self.room.id, user_id=99)


if __name__ == "__main__":
    unittest.main()
