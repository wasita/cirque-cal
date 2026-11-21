from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Session:
    """One scheduled class/open session, normalized across platforms."""

    uid: str                      # stable across runs -> calendar updates in place
    studio: str                   # studio key from studios.yaml
    studio_name: str
    title: str
    start: datetime               # timezone-aware (UTC)
    end: datetime
    instructors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)   # platform tags, if any
    description: str = ""         # plain text
    url: str = ""                 # booking link
    address: str = ""
    cancelled: bool = False
    spots_left: int | None = None
    # filled in by normalize.enrich()
    apparatus: list[str] = field(default_factory=list)
    kind: str = "class"           # "class" | "open"
    level: float | None = None    # common scale: 0 = intro/101, 1, 1.5, 2, ...

    def to_json(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat()
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Session":
        d = dict(d)
        d["start"] = datetime.fromisoformat(d["start"])
        d["end"] = datetime.fromisoformat(d["end"])
        return cls(**d)
