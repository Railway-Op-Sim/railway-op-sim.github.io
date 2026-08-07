import semver
from requests.compat import _ver
import logging
import typing
import re
import os
import urllib.parse
import zipfile
import pathlib
import tempfile
import json
import requests
from railos_static_website.models import ProgramVersion, FileStorage
from railos_static_website.utilities import hash_file

GITHUB_RESTAPI_ENDPOINT: str = "https://api.github.com"
RAILOS_ABALL_USER: str = "AlbertBall"
RAILOS_REPOSITORY: str = "railway-dot-exe"


class GitHubRailOSReleaseData:
    """Retrieve RailOS latest releases."""

    def __init__(
        self,
        destination: pathlib.Path,
        user_name: str,
        *,
        hash_files: bool = True,
        token: str | None = None,
    ) -> None:
        super().__init__()
        self._hash_files: bool = hash_files
        self._release_list: dict[str, dict[str, typing.Any]] = {}
        self._params: dict[str, int] = {"per_page": 100}
        self._headers: dict[str, str] = {}
        self._token: str | None = token
        self.program_versions: dict[semver.Version, ProgramVersion] = {}
        _cache_file: pathlib.Path = destination.joinpath("railos_release.json")
        if not (
            _entries := self._retrieve_latest_release(user_name, cache_file=_cache_file)
        ):
            return

        for entry in _entries.values():
            _version = self._store_release(entry)
            if _version:
                self.program_versions[_version.semantic_version] = _version

    def _retrieve_latest_release(
        self, user_name: str, cache_file: pathlib.Path
    ) -> dict[str, typing.Any]:
        _latest = {}
        if cache_file.exists():
            print("Using cache for Repository Listings...")
            with cache_file.open() as in_f:
                return json.load(in_f)
        _railos_releases_url: str = "/".join(
            (
                GITHUB_RESTAPI_ENDPOINT,
                "repos",
                RAILOS_ABALL_USER,
                RAILOS_REPOSITORY,
                "releases",
            )
        )

        self._headers = {"User-Agent": user_name}

        if self._token:
            self._headers["Authorization"] = f"Bearer {self._token}"

        _latest_info = requests.get(
            _railos_releases_url, params=self._params, headers=self._headers
        ).json()

        _latest_info = {entry["tag_name"]: entry for entry in _latest_info}

        _new_entries = {k: v for k, v in _latest_info.items() if k not in _latest}

        with open(cache_file, "w") as out_f:
            json.dump(_latest | _latest_info, out_f, indent=2)

        return _new_entries

    def _store_release(
        self, release_entry: dict[str, typing.Any]
    ) -> ProgramVersion | None:
        _semantic_version_re: str = re.findall(
            r"\d+\.\d+\.\d+", release_entry["tag_name"]
        )
        if not _semantic_version_re:
            print(
                f"Failed to retrieve semantic version from {release_entry['tag_name']}"
            )
            return
        _release_date: str = release_entry["published_at"].split("T")[0]
        _download_url_32_bit: str | None = None
        _download_url_64_bit: str | None = None
        _hash_32_bit: str | None = None
        _hash_64_bit: str | None = None
        try:
            if "RailOS" not in release_entry["assets"][0].get("name"):
                _download_url_32_bit = release_entry["assets"][0][
                    "browser_download_url"
                ]
                _hash_32_bit = release_entry["assets"][0]["digest"]
            elif "RailOS32" in release_entry["assets"][0].get("name"):
                _download_url_32_bit = release_entry["assets"][0][
                    "browser_download_url"
                ]
                _hash_32_bit = release_entry["assets"][0]["digest"]
                _download_url_64_bit = release_entry["assets"][1][
                    "browser_download_url"
                ]
                _hash_64_bit = release_entry["assets"][1]["digest"]
            else:
                _download_url_64_bit = release_entry["assets"][0][
                    "browser_download_url"
                ]
                _hash_64_bit = release_entry["assets"][0]["digest"]
                _download_url_32_bit = release_entry["assets"][1][
                    "browser_download_url"
                ]
                _hash_32_bit = release_entry["assets"][1]["digest"]
        except IndexError:
            print(f"WARNING: No files found for tag '{release_entry['tag_name']}'")
            return None

        _download_url_dat_32 = urllib.parse.urlparse(_download_url_32_bit)
        _download_url_dat_64 = None

        if _download_url_64_bit:
            _download_url_dat_64 = urllib.parse.urlparse(_download_url_64_bit)

        _file_storage_32 = FileStorage(
            netloc=_download_url_dat_32.netloc,
            path=_download_url_dat_32.path,
            sha256_hash=_hash_32_bit,
            scheme=_download_url_dat_32.scheme,
        )

        if _download_url_64_bit:
            _file_storage_64 = FileStorage(
                netloc=_download_url_dat_64.netloc,
                path=_download_url_dat_64.path,
                sha256_hash=_hash_64_bit,
                scheme=_download_url_dat_64.scheme,
            )

        _release_args: dict[str, typing.Any] = {
            "semantic_version": semver.Version.parse(_semantic_version_re[0]),
            "release_date": _release_date,
            "download_url_32bit": _file_storage_32,
            "author": "Albert Ball",
        }

        if _download_url_64_bit:
            _release_args["download_url_64bit"] = _file_storage_64

        _release = ProgramVersion(**_release_args)

        return _release
