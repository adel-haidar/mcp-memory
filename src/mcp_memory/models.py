from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Memory:
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    memory_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
