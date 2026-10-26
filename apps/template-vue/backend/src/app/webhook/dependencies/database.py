from collections.abc import AsyncGenerator

from app.infrastructure.database.repo.requests import RequestsRepo
from app.infrastructure.database.setup import create_engine, create_session_pool
from core.infrastructure.config import settings

engine = create_engine(settings.db)
session_pool = create_session_pool(engine)


async def get_repo() -> AsyncGenerator[RequestsRepo]:
    """Open the request session: one session, one transaction, committed when this dependency exits
    (rolled back on an exception).

    When it exits is decided where it is used, by the ``Depends`` scope:

    - ``get_services`` (``app.webhook.dependencies.service``) uses ``scope="function"``, the
      default for every endpoint: the commit runs when the endpoint returns, **before the
      response is sent**. A client that refetches right after a 200 reads committed data, and a
      failing commit becomes a 500 instead of a 200 for data that was never saved.
    - ``get_services_streaming`` uses ``scope="request"``: the commit runs **after the response
      is sent**. Only for endpoints returning a ``StreamingResponse`` whose body generator still
      writes through the services (e.g. saves the generated result or stores chat messages).

    Endpoints take ``services`` (``Depends(get_services)``), not ``get_repo``. If one really needs
    the repo, use ``Depends(get_repo, scope="function")``: a bare ``Depends(get_repo)`` is
    request scope, and FastAPI caches the two scopes apart, so the endpoint would open a second
    session next to ``get_user``'s (and can block on its own row locks).
    """
    async with session_pool() as session:
        async with session.begin():
            yield RequestsRepo(session)
