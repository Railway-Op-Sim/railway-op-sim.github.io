import pycountry
from requests.models import Response


import http
import datetime
import semver
from railos_static_website.models import Project, Version, FileStorage
from railos_static_website.utilities import hash_file

import requests
import typing
import re
import os
import pathlib
import hashlib
import tempfile
import toml
import json
import glob
import shutil
import zipfile
import urllib.parse

from pycountry import countries

from railostools.metadata.validation import validate

GITHUB_RESTAPI_ENDPOINT: str = "https://api.github.com"
RAILOS_GITHUB_ORGANISATION: str = "Railway-Op-Sim"
MEDIA_DIRECTORY: pathlib.Path = (
    pathlib.Path(__file__).parents[1].joinpath("dist", "media", "project_images")
)


class GitHubRailOSProjectData:
    """Retrieve RailOS project repositories and populate database."""

    def __init__(
        self, destination: pathlib.Path, user_name: str, api_token: str | None
    ) -> None:
        super().__init__()
        self._error_log: pathlib.Path = pathlib.Path(__file__).parent.joinpath(
            "project_errors.log"
        )
        self._error_log.unlink(missing_ok=True)
        self._repo_list: list[dict[str, str]] = []
        self._release_list: dict[str, list[str]] = {}
        self._params: dict[str, int] = {"per_page": 100}
        self._headers: dict[str, str] = {}
        self._api_token: str | None = api_token

        _cache_file: pathlib.Path = destination.joinpath("restapi_cache.json")
        _data_cache: pathlib.Path = destination.joinpath("gh_data_cache")
        _data_cache.mkdir(exist_ok=True)

        self._retrieve_or_get_metadata(user_name, _cache_file)
        self._filter_to_project_repos()
        self._filter_to_released_projects(_data_cache)
        self.projects: dict[str, dict[str, Project]] = self._build_versions()

    def error(self, msg: str) -> None:
        print(f"WARNING: {msg}")
        with self._error_log.open("a") as out_f:
            _ = out_f.write(msg)

    def _retrieve_or_get_metadata(
        self, user_name: str, cache_file: pathlib.Path
    ) -> None:
        if cache_file.exists():
            print("Using cache for Repository Listings...")
            with cache_file.open() as in_f:
                self._repo_list = json.load(in_f)
            return

        _org_repos_url: str = "/".join(
            (GITHUB_RESTAPI_ENDPOINT, "orgs", RAILOS_GITHUB_ORGANISATION, "repos")
        )

        self._headers = {"User-Agent": user_name}

        if self._api_token:
            print("Using API Token")
            self._headers = {"Authorization": f"Bearer {self._api_token}"}
        page = 0
        next_page: str = f"{_org_repos_url}?page=1"

        while True:
            print(f"Getting page {next_page}")

            _org_repos: Response = requests.get(
                next_page,
                params=self._params | {"page": page},
                headers=self._headers,
            )
            _new_page = _org_repos.links.get("next", {}).get("url")
            if _new_page == next_page:
                break
            next_page = _new_page

            if _org_repos.status_code != 200:
                raise RuntimeError(
                    "Failed to retrieve data from GitHub, "
                    + f"request to '{_org_repos_url}' "
                    + f"returned status code {_org_repos.status_code}"
                )

            cache_file.parent.mkdir(exist_ok=True)

            with cache_file.open("w") as out_file:
                json.dump(_org_repos.json(), out_file, indent=2)

            self._repo_list += _org_repos.json()

    def _filter_to_project_repos(self) -> None:
        print("Filtering project repositories.")
        _permitted_country_codes: list[str] = ["FN"] + [i.alpha_2 for i in countries]
        _name_check_regex = r"^(\w{2})-.+$"

        _storables: list[dict[str, str]] = []

        for result in self._repo_list or []:
            # look for valid repository names
            if not (iso2 := re.findall(_name_check_regex, result["name"])):
                self.error(
                    f"Skipping repository '{result['name']}' as name not a valid project repository"
                )
                continue
            if iso2[0] not in _permitted_country_codes:
                self.error(
                    f"Skipping repository '{result['name']}' as country code '{iso2[0]}' not valid"
                )
                continue
            _storables.append(result)

        if _storables:
            self._repo_list = _storables
        else:
            raise RuntimeError("No results retrieved after project filter applied")

    def _filter_to_released_projects(self, data_cache: pathlib.Path) -> None:
        print("Filtering on releases.")
        _release_results = []
        for result in self._repo_list or []:
            _json_file: pathlib.Path = data_cache.joinpath(
                f"{result['name'].replace('-', '_')}_cache.json"
            )
            if _json_file.exists():
                print(f"Using cache file '{_json_file}'...")
                self._release_list[result["name"]] = json.load(open(_json_file))
                _release_results.append(result)
                continue

            _releases_req = requests.get(
                result["releases_url"].replace("{/id}", ""),
                headers=self._headers,
                params=self._params,
            )

            if _releases_req.status_code != http.HTTPStatus.OK or not (
                _release_json := _releases_req.json()
            ):
                self.error(f"Skipping {result['name']} as no releases.")
                continue
            self._release_list[result["name"]] = _release_json

            with _json_file.open("w") as out_f:
                json.dump(_release_json, out_f, indent=2)

            _release_results.append(result)

        if _release_results:
            self._repo_list = _release_results
        else:
            raise RuntimeError("No results retrieved after release filter applied")

    def _get_file_metadata(
        self, download_url: str
    ) -> tuple[dict[str, str], dict[str, str], str, str]:
        with tempfile.TemporaryDirectory() as tempd:
            _download_loc: pathlib.Path = pathlib.Path(tempd).joinpath("download.zip")
            _request = requests.get(download_url)
            _ = _download_loc.write_bytes(_request.content)
            _out_zip: str = os.path.join(tempd, "download")
            try:
                with zipfile.ZipFile(_download_loc) as z_out:
                    z_out.extractall(_out_zip)
            except Exception:
                self.error(f"Failed to extract zip file '{_download_loc}'")
                return {}, {}, "", ""
            with _download_loc.open("rb") as in_f:
                _digest = hashlib.file_digest(in_f, "sha256")
            _metadata_files = glob.glob(
                os.path.join(_out_zip, "**", "*.toml"), recursive=True
            )

            if not os.path.isdir(MEDIA_DIRECTORY):
                os.makedirs(MEDIA_DIRECTORY)

            if not _metadata_files:
                self.error(
                    f"WARNING: Failed to obtain metadata for project from '{download_url}'"
                )
                print(f"Package contents: {os.listdir(_out_zip)}")
                return {}, {}, "", ""

            _metadata_file: str = _metadata_files[0]

            try:
                validate(_metadata_file)
            except Exception as e:
                self.error(
                    f"WARNING: Metadata validation failed for project from '{download_url}':\n{e}"
                )
                print(f"Validation returned: {e}")
                return {}, {}, "", ""

            _metadata = toml.load(_metadata_file)

            _image_file: str = _metadata["img_files"][0]
            _image_local: list[str] = glob.glob(
                os.path.join(_out_zip, "*", "Images", _image_file)
            )

            if not _image_local:
                _image_local = glob.glob(os.path.join(_out_zip, "*", "Images", "*"))

            try:
                _ = shutil.copy(
                    _image_local[0], os.path.join(MEDIA_DIRECTORY, _image_file)
                )
                _image_local_data = "/".join(["/media/project_images", _image_file])
            except IndexError:
                self.error(
                    f"Failed to get local image data for '{_metadata["name"]}'. "
                    + f"Expected file '{_image_file}' in Images folder of archive, but this does not exist."
                )
                return {}, {}, "", ""

            _hash = hash_file(f"{_download_loc}")

            _parsed_url = urllib.parse.urlparse(download_url)

            _file_remote_data = {
                "scheme": _parsed_url.scheme,
                "netloc": _parsed_url.netloc,
                "path": _parsed_url.path,
                "hash": _hash,
            }

        return _metadata, _file_remote_data, _image_local_data, _digest.hexdigest()

    def _build_file_storage(
        self, file_store_data: dict[str, typing.Any]
    ) -> FileStorage:
        return FileStorage(**file_store_data)

    def _build_project(
        self, metadata: dict[str, typing.Any], author: str
    ) -> Project | None:
        _name: str | None = None
        try:
            _name = metadata["name"]
            _display_name: str | None = metadata["display_name"]
            _factual: bool = metadata["factual"]
            _description: str | None = metadata["description"]
            _year: int = metadata["year"]
            _country_code: str = metadata["country_code"]
        except KeyError as e:
            self.error(
                f"Cannot store project '{_name}', missing metadata. Missing key: {e}"
            )
            return

        if not _name:
            self.error(f"Metadata '{metadata}' has empty name.")
            raise ValueError("Expected name for project.")

        return Project(
            name=_name.replace("_", " "),
            display_name=_display_name or _name,
            factual=_factual,
            description=_description,
            year=_year,
            country_code=_country_code,
            author=author,
            versions={},
        )

    def _build_versions(self) -> dict[str, dict[str, Project]]:
        _projects: dict[str, dict[str, Project]] = {}
        for repository in self._repo_list:
            _releases: list[dict[str, str]] = self._release_list[repository["name"]]

            _project: Project | None = None
            _project_name: str | None = None

            for release in _releases:
                if not (_assets := release["assets"]):
                    self.error(
                        f"Ignoring '{release['tag_name']}' for '{release['name']}' as no assets available."
                    )
                    continue
                _meta_data, _file_data, _image_data, _zip_hash = (
                    self._get_file_metadata(_assets[0]["browser_download_url"])
                )
                if not _meta_data:
                    continue
                _storage = self._build_file_storage(_file_data)
                _project_name_search = re.match(
                    r"\/(\w{2}-.*)\/", _assets[0]["browser_download_url"]
                )
                _contributors: list[str] = _meta_data.get("contributors", [])
                _author: str = _meta_data["author"]
                if not _project:
                    _project = self._build_project(_meta_data, author=_author)
                    if not _project:
                        continue
                _project_name = _project.websafe_name
                if _project_name_search:
                    _project_name = _project_name_search[1]
                print(
                    f"Creating version '{_meta_data['version']}' for '{_project.name}'"
                )
                _project_name = _project_name.replace("_", "")
                if not _project_name:
                    continue
                _prog_min_version: str | None = _meta_data.get("minimum_required")
                _version = Version(
                    semantic_version=semver.Version.parse(_meta_data["version"]),
                    release_date=datetime.datetime.strptime(
                        _meta_data["release_date"], "%Y-%m-%d"
                    ).date(),
                    has_session_file=len(_meta_data.get("ssn_files", [])) > 0,
                    minimum_required_railos=(
                        semver.Version.parse(_prog_min_version)
                        if _prog_min_version
                        else None
                    ),
                    download_url=_storage,
                    image_url=_image_data,
                    contributors=_contributors,
                    project_name=_project_name,
                    download_hash=_zip_hash,
                )
                _project.versions[_version.semantic_version] = _version
            if _project and _project_name:
                if _project.country_code == "FN":
                    _country = "Fictional"
                else:
                    _country_res = pycountry.countries.get(
                        alpha_2=_project.country_code
                    )
                    if hasattr(_country_res, "common_name"):
                        _country = _country_res.common_name
                    else:
                        _country = _country_res.name
                _ = _projects.setdefault(_country, {})
                _projects[_country][_project_name] = _project

        return _projects
