import unittest
import asyncio
from app.application.commands import AuthenticateUserCommand, RegisterUserCommand
from app.application.services.auth_service import AuthService
from app.core.exceptions import AuthenticationError, EntityAlreadyExistsError
from tests.conftest import FakeUserRepository


class TestAuthService(unittest.IsolatedAsyncioTestCase):
    """Unit tests for AuthService use cases using in-memory FakeUserRepository."""

    async def asyncSetUp(self):
        self.user_repo = FakeUserRepository()
        self.auth_service = AuthService(self.user_repo)

    async def test_register_user_success(self):
        cmd = RegisterUserCommand(
            username="johndoe",
            email="john@example.com",
            password="securePassword123",
        )
        user = await self.auth_service.register(cmd)

        self.assertEqual(user.username, "johndoe")
        self.assertEqual(user.email, "john@example.com")
        self.assertIsNotNone(user.id)
        self.assertNotEqual(user.hashed_password, "securePassword123")
        self.assertTrue(user.is_active)

    async def test_register_duplicate_email_raises_error(self):
        cmd = RegisterUserCommand(username="user1", email="same@example.com", password="password1")
        await self.auth_service.register(cmd)

        cmd2 = RegisterUserCommand(username="user2", email="same@example.com", password="password2")
        with self.assertRaises(EntityAlreadyExistsError) as ctx:
            await self.auth_service.register(cmd2)
        self.assertIn("Email is already registered", str(ctx.exception))

    async def test_register_duplicate_username_raises_error(self):
        cmd = RegisterUserCommand(username="sameuser", email="user1@example.com", password="password1")
        await self.auth_service.register(cmd)

        cmd2 = RegisterUserCommand(username="sameuser", email="user2@example.com", password="password2")
        with self.assertRaises(EntityAlreadyExistsError) as ctx:
            await self.auth_service.register(cmd2)
        self.assertIn("Username is already taken", str(ctx.exception))

    async def test_authenticate_success(self):
        await self.auth_service.register(
            RegisterUserCommand(username="alice", email="alice@example.com", password="alicePassword123")
        )

        auth_res = await self.auth_service.authenticate(
            AuthenticateUserCommand(email="alice@example.com", password="alicePassword123")
        )
        self.assertIsNotNone(auth_res.access_token)
        self.assertEqual(auth_res.token_type, "bearer")

    async def test_authenticate_wrong_password_raises_error(self):
        await self.auth_service.register(
            RegisterUserCommand(username="bob", email="bob@example.com", password="correctPassword")
        )

        with self.assertRaises(AuthenticationError) as ctx:
            await self.auth_service.authenticate(
                AuthenticateUserCommand(email="bob@example.com", password="wrongPassword")
            )
        self.assertIn("Invalid email or password", str(ctx.exception))

    async def test_authenticate_nonexistent_email_raises_error(self):
        with self.assertRaises(AuthenticationError):
            await self.auth_service.authenticate(
                AuthenticateUserCommand(email="notfound@example.com", password="anyPassword")
            )

    async def test_get_user_from_token_success(self):
        await self.auth_service.register(
            RegisterUserCommand(username="carol", email="carol@example.com", password="carolPassword")
        )
        auth_res = await self.auth_service.authenticate(
            AuthenticateUserCommand(email="carol@example.com", password="carolPassword")
        )

        user = await self.auth_service.get_user_from_token(auth_res.access_token)
        self.assertEqual(user.username, "carol")
        self.assertEqual(user.email, "carol@example.com")

    async def test_get_user_from_invalid_token_raises_error(self):
        with self.assertRaises(AuthenticationError):
            await self.auth_service.get_user_from_token("invalid.token.payload")


if __name__ == "__main__":
    unittest.main()
