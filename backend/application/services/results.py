"""Application results returned to the presentation layer."""
from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceResult:
    data: Any = None
    status: int = 200
