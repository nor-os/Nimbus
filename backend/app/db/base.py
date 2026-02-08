"""
Overview: SQLAlchemy declarative base for all models.
Architecture: Base class for data models (Section 4)
Dependencies: sqlalchemy
Concepts: ORM base, model registry
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
