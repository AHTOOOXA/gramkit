from app.infrastructure.database.repo.requests import RequestsRepo
from app.infrastructure.database.setup import create_engine, create_session_pool
from core.infrastructure.config import settings

engine = create_engine(settings.db)
session_pool = create_session_pool(engine)


async def get_repo():
    """
    Provides a RequestsRepo with a session in a transaction.

    Transaction lifecycle:
    1. Request starts → session created → transaction begins
    2. Business logic executes (all operations in same transaction)
    3. Request ends → transaction commits (or rolls back on error)

    Usage:
        @router.post("/users")
        async def create_user(
            data: UserCreateSchema,
            repo: RequestsRepo = Depends(get_repo),
        ):
            user = await repo.users.create(data.model_dump())
            return UserSchema.model_validate(user)
            # Transaction commits here automatically
    """
    async with session_pool() as session:
        async with session.begin():
            yield RequestsRepo(session)
            # Automatic commit on exit (rollback on exception)
