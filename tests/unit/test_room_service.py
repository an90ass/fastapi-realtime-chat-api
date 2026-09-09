import unittest
from app.application.commands import CreateRoomCommand
from app.application.services.room_service import RoomService
from app.core.exceptions import AuthorizationError, EntityAlreadyExistsError, EntityNotFoundError
from tests.conftest import FakeRoomRepository


class TestRoomService(unittest.IsolatedAsyncioTestCase):
    """Unit tests for RoomService use cases using in-memory FakeRoomRepository."""

    async def asyncSetUp(self):
        self.room_repo = FakeRoomRepository()
        self.room_service = RoomService(self.room_repo)

    async def test_create_room_success_and_auto_joins_creator(self):
        cmd = CreateRoomCommand(
            name="General Discussion",
            description="A place to discuss anything",
            is_private=False,
            creator_id=42,
        )
        room = await self.room_service.create_room(cmd)

        self.assertEqual(room.name, "General Discussion")
        self.assertIsNotNone(room.id)
        # Verify creator was automatically joined
        is_creator_joined = await self.room_repo.is_member(room.id, 42)
        self.assertTrue(is_creator_joined)

    async def test_create_duplicate_room_name_raises_error(self):
        cmd = CreateRoomCommand(name="Backend Engineers", creator_id=1)
        await self.room_service.create_room(cmd)

        with self.assertRaises(EntityAlreadyExistsError) as ctx:
            await self.room_service.create_room(cmd)
        self.assertIn("already exists", str(ctx.exception))

    async def test_list_public_rooms_filters_private_rooms(self):
        await self.room_service.create_room(CreateRoomCommand(name="Public 1", is_private=False, creator_id=1))
        await self.room_service.create_room(CreateRoomCommand(name="Private 1", is_private=True, creator_id=1))
        await self.room_service.create_room(CreateRoomCommand(name="Public 2", is_private=False, creator_id=1))

        public_rooms = await self.room_service.list_public_rooms()
        names = [r.name for r in public_rooms]
        self.assertIn("Public 1", names)
        self.assertIn("Public 2", names)
        self.assertNotIn("Private 1", names)

    async def test_join_room_success(self):
        room = await self.room_service.create_room(CreateRoomCommand(name="DevOps", creator_id=1))
        member = await self.room_service.join_room(room_id=room.id, user_id=99)

        self.assertEqual(member.room_id, room.id)
        self.assertEqual(member.user_id, 99)

    async def test_join_room_duplicate_membership_raises_error(self):
        room = await self.room_service.create_room(CreateRoomCommand(name="Security", creator_id=1))
        # Creator is already member, joining again must raise
        with self.assertRaises(EntityAlreadyExistsError):
            await self.room_service.join_room(room_id=room.id, user_id=1)

    async def test_join_nonexistent_room_raises_not_found(self):
        with self.assertRaises(EntityNotFoundError):
            await self.room_service.join_room(room_id=9999, user_id=1)

    async def test_check_membership(self):
        room = await self.room_service.create_room(CreateRoomCommand(name="Architecture", creator_id=1))

        # Member should not raise
        await self.room_service.check_membership(room.id, 1)

        # Non-member should raise AuthorizationError
        with self.assertRaises(AuthorizationError):
            await self.room_service.check_membership(room.id, 999)


if __name__ == "__main__":
    unittest.main()
