from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime


class ShortURL(SQLModel, table=True):
    __tablename__ = "short_urls"

    id: Optional[int] = Field(default=None, primary_key=True)
    original_url: str = Field(index=True)
    short_code: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total_visits: int = Field(default=0)

    visits: List["URLVisit"] = Relationship(back_populates="short_url")


class URLVisit(SQLModel, table=True):
    __tablename__ = "url_visits"

    id: Optional[int] = Field(default=None, primary_key=True)
    short_url_id: int = Field(foreign_key="short_urls.id")
    client_ip: str
    visited_at: datetime = Field(default_factory=datetime.utcnow)

    short_url: Optional[ShortURL] = Relationship(back_populates="visits")
