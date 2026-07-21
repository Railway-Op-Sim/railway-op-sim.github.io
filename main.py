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
        destination=_destination, user_name=github_username, hash_files=False
    )
    _project_data = GitHubRailOSProjectData(
        destination=_destination, user_name=github_username, api_token=_args.token
    )
    _versions = sorted(list(_program_releases.program_versions.keys()))
    for page in (
        _templates := pathlib.Path(__file__).parent.joinpath("templates")
    ).glob("*.html"):
        if page.stem not in ("project_detail",):
            render_page(
                page.name,
                template_dir=_templates,
                program_releases=_program_releases,
                project_data=_project_data,
                latest_version=_program_releases.program_versions[_versions[-1]],
                penultimate_version=_program_releases.program_versions[_versions[-2]],
                projects=_project_data.projects,
                current_year=datetime.datetime.now(tz=datetime.UTC).strftime("%Y"),
                file_name_32bit="x86",
                file_name_64bit="x64",
                discord_server_invite="https://discord.gg/FmE8dxN",
            )
        for country_projects in _project_data.projects.values():
            for project_name, project in country_projects.items():
                render_page(
                    "project_detail.html",
                    destination=pathlib.Path(__file__)
                    .parent.joinpath("dist")
                    .joinpath("projects"),
                    template_dir=_templates,
                    file_name=f"{project.websafe_name}.html",
                    project_data=_project_data,
                    program_releases=_program_releases,
                    project=project,
                )
