"""
Overview: System configuration model for setup wizard state and global settings.
Architecture: Stores system-wide configuration (Section 3.1)
Dependencies: sqlalchemy, app.db.base
Concepts: First-run setup, system configuration
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class SystemConfig(Base, IDMixin, TimestampMixin):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
