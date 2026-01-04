import re
from datetime import datetime
from typing import Annotated

from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.functions import func

int_pk = Annotated[int, mapped_column(primary_key=True)]


class Base(DeclarativeBase):
    pass


class TableNameMixin:
    @declared_attr.directive
    def __tablename__(cls) -> str:
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        if name.endswith("y"):
            return name[:-1] + "ies"
        elif name.endswith("s"):
            return name + "es"
        else:
            return name + "s"


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class UpdatedAtMixin:
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
