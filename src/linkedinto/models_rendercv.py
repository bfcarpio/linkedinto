"""Pydantic models for RenderCV YAML output structure."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SocialNetwork(BaseModel):
    network: str
    username: str


class ExperienceEntry(BaseModel):
    company: str
    position: str
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    summary: str | None = None
    highlights: list[str] = []


class EducationEntry(BaseModel):
    institution: str
    area: str
    degree: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    summary: str | None = None
    highlights: list[str] = []


class NormalEntry(BaseModel):
    name: str
    date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    summary: str | None = None
    highlights: list[str] = []


class PublicationEntry(BaseModel):
    title: str
    authors: list[str]
    date: str | None = None
    journal: str | None = None
    doi: str | None = None
    url: str | None = None
    summary: str | None = None


class OneLineEntry(BaseModel):
    label: str
    details: str


class BulletEntry(BaseModel):
    bullet: str


class Cv(BaseModel):
    name: str | None = None
    headline: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
    social_networks: list[SocialNetwork] = []
    sections: dict[str, list[Any]] = Field(default_factory=dict)


class RenderCV(BaseModel):
    """Top-level RenderCV YAML model."""

    cv: Cv = Field(default_factory=Cv)
    design: dict[str, object] | None = None
    locale: str | None = None
    settings: dict[str, object] | None = None
