"""
Overview: Authentication service package.
Architecture: Service layer for auth operations (Section 3.1, 5.1)
Dependencies: app.services.auth.service, app.services.auth.jwt, app.services.auth.password
Concepts: Authentication, JWT, session management
"""

from app.services.auth.service import AuthService

__all__ = ["AuthService"]
