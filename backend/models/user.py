from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base
from backend.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole))
