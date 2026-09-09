# Real-time Chat API

A production-ready, enterprise-grade real-time chat backend built with **FastAPI**, **Clean Architecture**, **Async SQLAlchemy 2.0**, **Redis Pub/Sub**, and **WebSockets**.

---

## Architecture

This project strictly follows **Clean Architecture** (Uncle Bob) with clear layer boundaries enforced by Python `Protocol` interfaces and a single Composition Root for Dependency Injection.

```text
app/
├── core/                                        # Cross-cutting concerns
│   ├── config.py                                # Type-safe settings via Pydantic BaseSettings
│   ├── security.py                              # JWT creation/validation, password hashing
│   ├── database.py                              # Async SQLAlchemy 2.0 engine and session
│   ├── redis.py                                 # Redis connection pool with lifespan management
│   └── exceptions.py                            # Domain exceptions and global HTTP handlers
│
├── domain/                                      # Innermost circle — zero framework dependencies
│   ├── entities/                                # Pure Python dataclasses
│   │   ├── user.py                              # UserEntity
│   │   ├── room.py                              # RoomEntity, RoomMemberEntity
│   │   └── message.py                           # MessageEntity
│   └── ports/                                   # Abstract contracts (Python Protocol)
│       ├── repositories.py                      # IUserRepository, IRoomRepository, IMessageRepository
│       └── message_broker.py                    # IMessageBroker
│
├── application/                                 # Use cases — depends only on domain
│   ├── commands.py                              # Immutable Command and Result objects
│   └── services/
│       ├── auth_service.py                      # AuthService — registration and authentication
│       ├── room_service.py                      # RoomService — room lifecycle and membership
│       └── chat_service.py                      # ChatService — messaging and broadcasting
│
├── infrastructure/                              # Concrete adapters implementing domain ports
│   ├── persistence/
│   │   ├── models/                              # SQLAlchemy ORM models (isolated here only)
│   │   │   ├── base.py
│   │   │   ├── user_model.py
│   │   │   ├── room_model.py
│   │   │   └── message_model.py
│   │   └── repositories/                        # Concrete repository implementations
│   │       ├── base.py                          # Shared async SQLAlchemy helpers
│   │       ├── user_repository.py               # Implements IUserRepository
│   │       ├── room_repository.py               # Implements IRoomRepository
│   │       └── message_repository.py            # Implements IMessageRepository (cursor pagination)
│   └── messaging/
│       └── redis_broker.py                      # Implements IMessageBroker via Redis Pub/Sub
│
├── presentation/                                # Outermost circle — FastAPI adapters
│   ├── schemas/                                 # Pydantic DTOs (HTTP boundary only)
│   ├── routers/                                 # Thin controllers mapping HTTP to commands
│   ├── websocket/
│   │   ├── connection_manager.py                # Local WebSocket registry per room
│   │   └── pubsub_manager.py                    # Single-subscriber Redis multiplexer
│   └── dependencies.py                          # Composition Root — binds ports to adapters
│
└── main.py                                      # Application entry point with lifespan hooks
```

### Layer dependency rules

```
domain       <-- no external dependencies
application  <-- domain only
infrastructure <-- domain + core
presentation   <-- application + infrastructure + domain + core
```

---

## Design Decisions

**Single-subscriber Redis multiplexing**

The previous implementation created one Redis subscription per WebSocket connection, causing N-squared message delivery (N connections in a room receiving the same message N times). This project maintains at most one background subscriber task per active room per server node. When the last client disconnects, the task is cancelled.

**Dependency Inversion Principle**

Application services depend on `IMessageBroker`, `IUserRepository`, `IRoomRepository`, and `IMessageRepository` — all Python `Protocol` types. No service imports `redis_client`, SQLAlchemy models, or any infrastructure class. The composition root in `presentation/dependencies.py` is the only place where ports are bound to their concrete adapters.

**Cursor-based pagination**

Message history uses `before_id` cursor pagination backed by a composite index on `(room_id, id)`. Queries are bounded in complexity regardless of message count.

**Async throughout**

SQLAlchemy 2.0 with `asyncpg`, pooled Redis connections, and FastAPI lifespan hooks ensure no blocking I/O reaches the event loop.

---

## Tech Stack

| Component | Technology |
| :--- | :--- |
| Web framework | FastAPI |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 (async) |
| DB driver | asyncpg |
| Cache / Pub-Sub | Redis 7 |
| Migrations | Alembic |
| Auth | JWT (HS256) |
| Password hashing | bcrypt via passlib |
| Containerization | Docker + Docker Compose |
| Runtime | Python 3.10+ |

---

## API Reference

### Authentication

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| POST | `/auth/register` | Register a new user account | No |
| POST | `/auth/login` | Authenticate and receive a JWT token | No |
| GET | `/auth/me` | Retrieve the authenticated user profile | Bearer |

### Rooms

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| POST | `/rooms/` | Create a new chat room | Bearer |
| GET | `/rooms/` | List all public rooms | Bearer |
| GET | `/rooms/{id}` | Get details of a specific room | Bearer |
| POST | `/rooms/{id}/join` | Join a room | Bearer |
| GET | `/rooms/{id}/members` | List all members of a room | Bearer |

### Chat

| Method | Endpoint | Description | Auth |
| :--- | :--- | :--- | :--- |
| GET | `/chat/{id}/messages` | Paginated message history (`limit`, `before_id`) | Bearer |
| WS | `/chat/ws/{room_id}?token=...` | Real-time WebSocket connection (preferred) | Query param |
| WS | `/chat/ws/{room_id}/{token}` | Real-time WebSocket connection (compat) | Path param |

### Monitoring

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| GET | `/health` | Readiness probe checking database and Redis |

---

## WebSocket Protocol

Connect to `/chat/ws/{room_id}?token=<JWT>`.

**Send a message:**

```json
{
  "content": "Hello, world."
}
```

**Receive a message:**

```json
{
  "id": 42,
  "content": "Hello, world.",
  "room_id": 1,
  "sender_id": 7,
  "username": "alice",
  "created_at": "2026-09-10T01:00:00+00:00"
}
```

---

## Running Locally

### With Docker Compose

```bash
docker-compose up --build
```

### Without Docker

```bash
# Clone and enter the project
git clone <repository-url>
cd fastapi-realtime-chat

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database and Redis credentials

# Apply database migrations
python -m alembic upgrade head

# Start the development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation is available at `http://localhost:8000/docs`.

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL async connection string | See `.env.example` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing secret (min 32 chars) | — |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes | `1440` |
| `PROJECT_NAME` | API title shown in docs | `Real-time Chat API` |
| `DEBUG` | Enable SQLAlchemy query logging | `False` |
| `CORS_ORIGINS` | JSON array of allowed CORS origins | `["*"]` |

---

## Project Structure Notes

The domain and application layers contain zero references to FastAPI, SQLAlchemy, Redis, or Pydantic. This is verified by an AST-based import scanner that runs as part of the test suite. Any violation causes a test failure.