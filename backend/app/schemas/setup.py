"""
Overview: Pydantic schemas for the first-run setup wizard.
Architecture: Setup wizard API schemas (Section 7.1)
Dependencies: pydantic
Concepts: First-run setup, admin creation
"""

from pydantic import BaseModel, EmailStr


class SetupStatusResponse(BaseModel):
    is_complete: bool


class SetupInitializeRequest(BaseModel):
    admin_email: EmailStr
    admin_password: str
    organization_name: str
