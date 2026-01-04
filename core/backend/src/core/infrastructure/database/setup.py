from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def create_engine(db, echo=False):
    engine = create_async_engine(
        db.url,
        query_cache_size=1200,
        pool_size=20,
        max_overflow=200,
        pool_timeout=30,  # Timeout for getting a connection from the pool
        pool_recycle=1800,  # Recycle connections after 30 minutes
        pool_pre_ping=True,  # Verify connections before using them
        future=True,
        echo=echo,
    )
    return engine


def create_session_pool(engine):
    session_pool = async_sessionmaker(bind=engine, expire_on_commit=False)
    return session_pool
