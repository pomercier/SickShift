from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TVShow(Base):
    __tablename__ = "tv_shows"

    show_id = Column(Integer, primary_key=True)
    indexer_id = Column(Integer, index=True)
    indexer = Column(Integer, index=True)
    show_name = Column(String)
    location = Column(String)
    network = Column(String)
    genre = Column(String)
    classification = Column(String)
    status = Column(String)
    airs = Column(String)
    startyear = Column(Integer)
    paused = Column(Integer)
    air_by_date = Column(Integer)
    subtitles = Column(Integer)
    quality = Column(Integer)


class TVEpisode(Base):
    __tablename__ = "tv_episodes"

    episode_id = Column(Integer, primary_key=True)
    showid = Column(Integer, index=True)
    indexerid = Column(Integer, index=True)
    indexer = Column(Integer, index=True)
    name = Column(String)
    season = Column(Integer)
    episode = Column(Integer)
    description = Column(String)
    airdate = Column(Integer)
    hasnfo = Column(Integer)
    hastbn = Column(Integer)
    status = Column(Integer)
    location = Column(String)
    file_size = Column(Integer)
    subtitles = Column(String)
    is_proper = Column(Integer)
    scene_season = Column(Integer)
    scene_episode = Column(Integer)
    scene_absolute_number = Column(Integer)
    version = Column(Integer)
    release_name = Column(String)


class Show(BaseModel):
    show_name: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    ep_name: Optional[str] = None
    network: Optional[str] = None
    location: Optional[str] = None
    showid: Optional[str] = None
    show_id: Optional[int] = None
    indexer_id: Optional[int] = None
    thumbnail: Optional[str] = None


class MissingEpisode(BaseModel):
    missing: Optional[str] = None
    show_name: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    ep_name: Optional[str] = None
    show_id: Optional[int] = None
    indexer_id: Optional[int] = None
    thumbnail: Optional[str] = None
    airdate: Optional[int] = None


class MissingGroup(BaseModel):
    show_name: str
    show_id: Optional[int] = None
    indexer_id: Optional[int] = None
    thumbnail: Optional[str] = None
    episodes: list[MissingEpisode] = Field(default_factory=list)


class EndedShowData(BaseModel):
    urls: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)


class UpcomingShow(BaseModel):
    show_name: str
    airdate: str
    image: str
    indexer_id: Optional[str] = None
    show_id: Optional[str] = None


class DashboardSnapshot(BaseModel):
    """Immutable snapshot of dashboard view data."""

    version: str
    generated_at: datetime
    shows: list[dict[str, Any]] = Field(default_factory=list)
    missing: list[dict[str, Any]] = Field(default_factory=list)
    missing_groups: list[dict[str, Any]] = Field(default_factory=list)
    ended: dict[str, list[str]] = Field(default_factory=lambda: {"urls": [], "links": []})
    upcoming: list[dict[str, Any]] = Field(default_factory=list)
    etag: str
