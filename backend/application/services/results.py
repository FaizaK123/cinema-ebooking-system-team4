"""Application results returned to the presentation layer."""
from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceResult:
    data: Any = None
    status: int = 200
    meta: Any = None  # extra data for the presenter (e.g. showtimes to attach to movies)
