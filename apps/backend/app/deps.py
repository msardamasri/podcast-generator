"""FastAPI dependencies."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db


def get_current_user_id(request: Request) -> uuid.UUID:
    """Returns the demo user's UUID.

    Take-home stub. In production this would parse a JWT, look up a session,
    etc. — but the signature stays the same, so swapping is trivial.
    """
    return request.app.state.demo_user_id


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]
DBSession = Annotated[AsyncSession, Depends(get_db)]