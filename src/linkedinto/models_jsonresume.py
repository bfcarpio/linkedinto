"""Pydantic models for the JSON Resume v1.0.0 schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Location(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country_code: str | None = None
    region: str | None = None


class Profile(BaseModel):
    network: str | None = None
    username: str | None = None
    url: str | None = None


class Basics(BaseModel):
    name: str | None = None
    label: str | None = None
    image: str | None = None
    email: str | None = None
    phone: str | None = None
    url: str | None = None
    summary: str | None = None
    location: Location | None = None
    profiles: list[Profile] = []


class Work(BaseModel):
    name: str | None = None
    position: str | None = None
    url: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = None
    highlights: list[str] = []
    location: str | None = None


class Education(BaseModel):
    institution: str | None = None
    url: str | None = None
    area: str | None = None
    study_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    score: str | None = None
    courses: list[str] = []


class Skill(BaseModel):
    name: str | None = None
    level: str | None = None
    keywords: list[str] = []


class Language(BaseModel):
    language: str | None = None
    fluency: str | None = None


class Project(BaseModel):
    name: str | None = None
    description: str | None = None
    highlights: list[str] = []
    keywords: list[str] = []
    start_date: str | None = None
    end_date: str | None = None
    url: str | None = None
    roles: list[str] = []
    entity: str | None = None
    type: str | None = None


class Publication(BaseModel):
    name: str | None = None
    publisher: str | None = None
    release_date: str | None = None
    url: str | None = None
    summary: str | None = None
    authors: list[str] = []


class Certificate(BaseModel):
    name: str | None = None
    date: str | None = None
    url: str | None = None
    issuer: str | None = None


class Award(BaseModel):
    title: str | None = None
    date: str | None = None
    awarder: str | None = None
    summary: str | None = None


class Reference(BaseModel):
    name: str | None = None
    reference: str | None = None


class Volunteer(BaseModel):
    organization: str | None = None
    position: str | None = None
    url: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = None
    highlights: list[str] = []


class Interest(BaseModel):
    name: str | None = None
    keywords: list[str] = []


class JsonResume(BaseModel):
    """Top-level JSON Resume v1.0.0 model."""

    basics: Basics | None = None
    work: list[Work] = []
    education: list[Education] = []
    skills: list[Skill] = []
    languages: list[Language] = []
    projects: list[Project] = []
    publications: list[Publication] = []
    certificates: list[Certificate] = []
    awards: list[Award] = []
    references: list[Reference] = []
    volunteer: list[Volunteer] = []
    interests: list[Interest] = []
