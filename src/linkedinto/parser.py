"""LinkedIn ZIP export parser.

Handles a single large CSV file inside a ZIP archive where every row
is prefixed with its filename (e.g. ``Positions.csv,Company Name,...``).
Rows are grouped by filename prefix; within each group the first row
provides column headers and subsequent rows provide data.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from linkedinto.constants import CSV_EXTENSION, UTF8_SIG_ENCODING
from linkedinto.domain import (
    AwardHonorRow,
    CertificationRow,
    EducationRow,
    InterestRow,
    LanguageRow,
    LinkedInData,
    PositionRow,
    ProfileRow,
    ProjectRow,
    PublicationRow,
    RecommendationRow,
    SkillRow,
    VolunteerRow,
)
from linkedinto.exceptions import LinkedInParserError
from linkedinto.url_extractor import extract_url

RECOMMENDATION_VISIBLE = "visible"
RECOMMENDATION_SHOWN = "shown"
RECOMMENDATION_EMPTY = ""

FIELD_ALIASES: dict[str, str] = {
    "firstname": "FirstName",
    "lastname": "LastName",
    "maidenname": "MaidenName",
    "companyname": "Company",
    "company_name": "Company",
    "startedon": "Started",
    "startdate": "Started",
    "start_date": "Started",
    "finishedon": "Ended",
    "endedon": "Ended",
    "enddate": "Ended",
    "end_date": "Ended",
    "schoolname": "School",
    "school_name": "School",
    "degreename": "Degree",
    "degree_name": "Degree",
    "title": "Position",
    "jobtitle": "Position",
    "phonenumber": "Phone",
    "emailaddress": "Email",
    "zipcode": "ZipCode",
    "geolocation": "GeoLocation",
    "countrycode": "CountryCode",
    "linkedin": "LinkedIn",
    "twitterhandles": "Twitter",
    "twitter_url": "Twitter",
}


def normalize_field_name(name: str) -> str:
    """Normalize a header name: remove internal spaces, apply aliases."""
    stripped = name.strip()
    lower = stripped.lower().replace(" ", "")
    alias = FIELD_ALIASES.get(lower)
    if alias is not None:
        return alias
    # No alias: remove internal spaces so "First Name" becomes "FirstName"
    return stripped.replace(" ", "")


def row_to_map(headers: list[str], values: list[str]) -> dict[str, str]:
    """Combine normalized headers with values into a dict."""
    result: dict[str, str] = {}
    for header, value in zip(headers, values, strict=False):
        key = normalize_field_name(header)
        result[key] = value.strip() if value else ""
    return result


def _group_rows_by_section(
    reader: Any,
) -> dict[str, tuple[list[str], list[list[str]]]]:
    """Group CSV rows by filename prefix section.

    The first row of each section group provides column headers;
    subsequent rows in that group provide data.
    """
    groups: dict[str, list[list[str]]] = defaultdict(list)

    for row in reader:
        if not row or not row[0].strip():
            continue
        groups[row[0].strip()].append(row[1:])

    result: dict[str, tuple[list[str], list[list[str]]]] = {}
    for section, rows in groups.items():
        if rows:
            headers = rows[0]
            data_rows = rows[1:]
            result[section] = (headers, data_rows)

    return result


class LinkedinZipParser:
    """Parse a LinkedIn export ZIP into a LinkedInData container."""

    def parse(self, zip_path: str | Path) -> LinkedInData:
        """Parse a LinkedIn export ZIP file.

        Args:
            zip_path: Path to the LinkedIn export ZIP file.

        Returns:
            A LinkedInData container with all parsed sections.

        Raises:
            LinkedInParserError: If the ZIP is invalid or missing data.
        """
        path = Path(zip_path)
        if not path.is_file():
            msg = f"Input file '{path}' does not exist"
            raise LinkedInParserError(msg)

        try:
            with zipfile.ZipFile(path, "r") as zf:
                csv_files = [n for n in zf.namelist() if n.endswith(CSV_EXTENSION)]
                if not csv_files:
                    msg = "No CSV file found in the ZIP archive"
                    raise LinkedInParserError(msg)

                data = LinkedInData()
                for csv_name in csv_files:
                    with zf.open(csv_name) as f:
                        content = f.read().decode(UTF8_SIG_ENCODING)
                        reader = csv.reader(io.StringIO(content))
                        rows = list(reader)
                        if len(rows) < 2:
                            continue  # skip files with only headers

                    # Detect format: single-CSV has rows prefixed with ".csv" names
                    # in the first column; multi-CSV has plain data in the first col.
                    is_single_format = any(
                        row and ".csv" in row[0].strip().lower() for row in rows[1:]
                    )

                    if is_single_format:
                        # Single-CSV: rows prefixed with section name
                        sections = _group_rows_by_section(iter(rows))
                        self._process_sections(data, sections)
                    else:
                        # Multi-CSV: this file is one section
                        headers = rows[0]
                        data_rows = rows[1:]
                        section_key = Path(csv_name).name
                        sections = {section_key: (headers, data_rows)}
                        self._process_sections(data, sections)

                return data
        except zipfile.BadZipFile:
            msg = f"The ZIP file '{path}' is malformed or not a valid ZIP archive"
            raise LinkedInParserError(msg) from None

    def _process_sections(
        self,
        data: LinkedInData,
        sections: dict[str, tuple[list[str], list[list[str]]]],
    ) -> None:
        """Route each section group to the correct handler."""
        for section, (headers, rows) in sections.items():
            section_lower = section.lower()
            for row in rows:
                row_data = row_to_map(headers, row)
                match section_lower:
                    case "profile.csv":
                        self._handle_profile(data, row_data)
                    case "position.csv" | "positions.csv":
                        self._handle_position(data, row_data)
                    case "education.csv":
                        self._handle_education(data, row_data)
                    case "skills.csv":
                        self._handle_skill(data, row_data)
                    case "languages.csv":
                        self._handle_language(data, row_data)
                    case "projects.csv":
                        self._handle_project(data, row_data)
                    case "publications.csv":
                        self._handle_publication(data, row_data)
                    case "certifications.csv" | "certificates.csv":
                        self._handle_certification(data, row_data)
                    case "honors.csv":
                        self._handle_honor(data, row_data)
                    case (
                        "recommendations received.csv" | "recommendations_received.csv"
                    ):
                        self._handle_recommendation(data, row_data)
                    case "interests.csv":
                        self._handle_interest(data, row_data)
                    case "volunteering.csv" | "organizations.csv":
                        self._handle_volunteer(data, row_data)

    def _handle_profile(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.profile = ProfileRow(
            first_name=row.get("FirstName"),
            last_name=row.get("LastName"),
            address=row.get("Address"),
            zip_code=row.get("ZipCode"),
            geo_location=row.get("GeoLocation"),
            occupation=row.get("Occupation"),
            summary=row.get("Summary"),
            industry=row.get("Industry"),
            country=row.get("Country"),
            country_code=row.get("CountryCode"),
            email_address=row.get("Email"),
            phone_number=row.get("Phone"),
            twitter=row.get("Twitter"),
            linkedin=extract_url(row.get("LinkedIn")),
            websites=row.get("Websites"),
            headline=row.get("Headline"),
        )

    def _handle_position(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.positions.append(
            PositionRow(
                company=row.get("Company"),
                position=row.get("Position"),
                location=row.get("Location"),
                url=extract_url(row.get("Url")),
                started=row.get("Started"),
                ended=row.get("Ended"),
                description=row.get("Description"),
            )
        )

    def _handle_education(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.education.append(
            EducationRow(
                school=row.get("School"),
                degree=row.get("Degree"),
                field=row.get("Field"),
                started=row.get("Started"),
                ended=row.get("Ended"),
                grade=row.get("Grade"),
                activities=row.get("Activities"),
                notes=row.get("Notes"),
            )
        )

    def _handle_skill(self, data: LinkedInData, row: dict[str, str]) -> None:
        count_raw = row.get("Count")
        count = int(count_raw) if count_raw and count_raw.isdigit() else None
        data.skills.append(
            SkillRow(
                name=row.get("Name"),
                proficiency=row.get("Proficiency"),
                count=count,
            )
        )

    def _handle_language(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.languages.append(
            LanguageRow(
                name=row.get("Name"),
                proficiency=row.get("Proficiency"),
            )
        )

    def _handle_project(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.projects.append(
            ProjectRow(
                title=row.get("Title"),
                name=row.get("Name"),
                description=row.get("Description"),
                url=extract_url(row.get("Url")),
                started=row.get("Started"),
                ended=row.get("Ended"),
            )
        )

    def _handle_publication(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.publications.append(
            PublicationRow(
                name=row.get("Name") or row.get("Title"),
                publisher=row.get("Publisher"),
                date=row.get("Date"),
                url=extract_url(row.get("Url")),
                description=row.get("Description"),
            )
        )

    def _handle_certification(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.certifications.append(
            CertificationRow(
                name=row.get("Name"),
                issuer=row.get("Issuer"),
                date=row.get("Date"),
                url=extract_url(row.get("Url")),
            )
        )

    def _handle_honor(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.honors.append(
            AwardHonorRow(
                title=row.get("Title") or row.get("Name"),
                awarder=row.get("Awarder") or row.get("Issuer") or row.get("Company"),
                date=row.get("Date"),
                description=row.get("Description"),
            )
        )

    def _handle_recommendation(self, data: LinkedInData, row: dict[str, str]) -> None:
        status = row.get("Status", "").strip().lower()
        if status in (
            RECOMMENDATION_VISIBLE,
            RECOMMENDATION_SHOWN,
            RECOMMENDATION_EMPTY,
        ):
            data.recommendations.append(
                RecommendationRow(
                    recommender=row.get("Recommender"),
                    recommendation_body=row.get("RecommendationBody"),
                    status=row.get("Status"),
                )
            )

    def _handle_interest(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.interests.append(InterestRow(name=row.get("Name")))

    def _handle_volunteer(self, data: LinkedInData, row: dict[str, str]) -> None:
        data.volunteer.append(
            VolunteerRow(
                name=row.get("Name") or row.get("Company"),
                position=row.get("Position") or row.get("Role"),
                started=row.get("Started"),
                ended=row.get("Ended"),
                description=row.get("Description"),
            )
        )
