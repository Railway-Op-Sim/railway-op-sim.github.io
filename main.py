import json
import datetime
import jinja2
import pathlib

from railos_static_website.github_populate import GitHubRailOSProjectData
from railos_static_website.check_release import GitHubRailOSReleaseData


def render_page(
    page: str,
    destination: pathlib.Path | None = None,
    template_dir: pathlib.Path | None = None,
    file_name: str | None = None,
    **kwargs,
) -> None:
    _template_dir = template_dir or pathlib.Path(__file__).parent.joinpath("templates")
    if not _template_dir.exists():
        raise FileNotFoundError("Template directory does not exist.")
    _environment = jinja2.Environment(loader=jinja2.FileSystemLoader(_template_dir))
    _destination = destination or pathlib.Path(__file__).parent.joinpath("dist")
    _template = _environment.get_template(page)
    _output = _template.render(
        **kwargs,
    )

    _destination.mkdir(exist_ok=True)

    with _destination.joinpath(file_name or page).open("w", encoding="utf-8") as out_f:
        _ = out_f.write(_output)


if __name__ in "__main__":
    import argparse

    _parser = argparse.ArgumentParser()
    _ = _parser.add_argument(
        "--token", "-t", type=str, default=None, help="Provide GH API token"
    )
    _args = _parser.parse_args()
    github_username = "zarethrex"
    _destination = pathlib.Path(__file__).parent.joinpath("dist")
    _destination.mkdir(exist_ok=True)
    _program_releases = GitHubRailOSReleaseData(
        destination=_destination,
        user_name=github_username,
        hash_files=False,
        token=_args.token,
    )
    _project_data = GitHubRailOSProjectData(
        destination=_destination, user_name=github_username, api_token=_args.token
    )
    _versions = sorted(list(_program_releases.program_versions.keys()))
    _search_index_file = pathlib.Path(__file__).parent.joinpath(
        "dist", "search-index.json"
    )
    _search_index_file.unlink(missing_ok=True)
    _index: list[dict[str, str | int]] = [
        {
            "id": 1,
            "title": "Program Downloads",
            "url": "/program_download.html",
            "content": "Downloads for the latest release of Railway Operation Simulator.",
        },
        {
            "id": 2,
            "title": "Community Projects",
            "uri": "/project_listing.html",
            "content": "Community content downloads page.",
        },
    ]
    for page in (
        _templates := pathlib.Path(__file__).parent.joinpath("templates")
    ).glob("*.html"):
        if page.stem == "project_detail":
            _id: int = 3
            for country_projects in _project_data.projects.values():
                for project_name, project in country_projects.items():
                    _index.append(
                        {
                            "id": _id,
                            "title": project.name,
                            "url": f"/projects/{project.websafe_name}.html",
                            "content": project.description or project.display_name,
                        }
                    )
                    _id += 1
                    render_page(
                        "project_detail.html",
                        destination=_destination.joinpath("projects"),
                        template_dir=_templates,
                        file_name=f"{project.websafe_name}.html",
                        project_data=_project_data,
                        program_releases=_program_releases,
                        project=project,
                    )
        else:
            render_page(
                page.name,
                template_dir=_templates,
                program_releases=_program_releases,
                project_data=_project_data,
                latest_version=_program_releases.program_versions[_versions[-1]],
                penultimate_version=_program_releases.program_versions[_versions[-2]],
                projects=_project_data.projects,
                latest_projects=_project_data.latest_projects,
                current_year=datetime.datetime.now(tz=datetime.UTC).strftime("%Y"),
                file_name_32bit="x86",
                file_name_64bit="x64",
                installers=_project_data.installers,
                discord_server_invite="https://discord.gg/FmE8dxN",
            )
    with _search_index_file.open("w") as out_f:
        json.dump(_index, out_f, indent=2)
