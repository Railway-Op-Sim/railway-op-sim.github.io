import datetime
from typing import Annotated
import pycountry
import pydantic as pd
import semver

MODEL_CONFIG = pd.ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class FileStorage(pd.BaseModel):
    scheme: str
    netloc: str
    path: str
    sha256_hash: str | None = None

    def __str__(self) -> str:
        return f"{self.scheme}://{self.netloc}{self.path}"


class Installer(pd.BaseModel):
    semantic_version: semver.Version
    download_url: FileStorage
    model_config = MODEL_CONFIG


class Version(pd.BaseModel):
    semantic_version: semver.Version
    release_date: datetime.date
    image_url: str
    has_session_file: bool = False
    minimum_required_railos: semver.Version | None = None
    contributors: list[str] = pd.Field(default_factory=list[str])
    download_url: FileStorage
    project_name: str
    download_hash: str
    model_config = MODEL_CONFIG

    def __str__(self) -> str:
        return f"{self.project_name} ({self.semantic_version})"


class Project(pd.BaseModel):
    name: str
    display_name: str
    factual: bool
    description: str | None = None
    year: Annotated[pd.PositiveInt, pd.conint(ge=1700)]
    country_code: str
    author: str
    versions: dict[semver.Version, Version]
    model_config = MODEL_CONFIG

    @pd.field_validator("country_code", mode="before")
    @classmethod
    def check_country_code(cls, country_code: str) -> str:
        """Check valid country code."""
        _country_codes: list[str] = ["FN"] + [c.alpha_2 for c in pycountry.countries]
        if country_code not in _country_codes:
            raise AssertionError(f"Invalid country code '{country_code}'")
        return country_code

    @property
    def websafe_name(self) -> str:
        return (
            self.display_name.replace("-", "")
            .replace(".", "")
            .replace("\\", "")
            .replace("/", "")
            .replace(", ", "")
            .replace(",", "")
            .replace("&", "and")
            .replace("!", "")
            .replace(" ", "_")
            .lower()
        )

    def __str__(self) -> str:
        return f"{self.name}"


class ProgramVersion(pd.BaseModel):
    semantic_version: semver.Version
    release_date: datetime.date
    author: str
    download_url_32bit: FileStorage
    download_url_64bit: FileStorage | None = None
    model_config = MODEL_CONFIG

    def __str__(self) -> str:
        return f"Railway Operation Simulator ({self.semantic_version})"
