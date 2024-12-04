from typing import Any, List, Optional
import requests
from github import Github, Auth
from github.GitRelease import GitRelease
from os import environ
from .models import Dependency, Mod, Release, Manifest, Repo
from .hashes import sha512_sum
from semantic_version import SimpleSpec, Version

import logging


auth = Auth.Token(environ.get("GITHUB_TOKEN") or "")
github_client = Github(auth=auth)


def initialize_repo(repo: Repo) -> Optional[Mod]:
    try:
        releases = all_releases(repo)

        if len(releases) == 0:
            logging.warning(f"Repo {repo} has no valid releases.")
            return None

        return Mod(
            latest_manifest=releases[0].manifest,
            releases=releases
        )
    except Exception as e:
        logging.error(f"Failed to initialize repo {repo}: {e}")
        return None

def add_release_tag(mod: Mod, release_tag: str) -> Optional[Mod]:
    (org, repoName) = mod.latest_manifest.repo_url.split("/")[-2:]
    repo = Repo(org, repoName)
    try:
        repoString = str(repo)
        
        logging.info(f"Fetching repo {repoString}") 
        github_repo = github_client.get_repo(repoString)
        
        logging.info(f"Successfully Retrieved repository. Fetching release {release_tag}")
        release = github_repo.get_release(release_tag)

        mod_releases = mod.releases + [process_release(repo, release)]

        mod_releases.sort(key=lambda x: x.release_date, reverse=True)

        return Mod(
            latest_manifest=mod_releases[0].manifest,
            releases=mod_releases
        )

    except Exception as e:
        logging.error(f"Failed to add release tag {release_tag} for repo {repo}: {e}")
        return None

def all_releases(repo: Repo) -> List[Release]:
    logging.info(f"Getting all releases for {repo}")
    github_repo = github_client.get_repo(str(repo))
    git_releases = github_repo.get_releases()

    logging.info(f"Found {git_releases.totalCount} releases for {repo}")
    results = []
    has_error = False
    for release in git_releases:
        try:
            logging.info(f"Processing release {release.tag_name} for {repo}")
            results.append(process_release(repo, release))
        except KeyError as e:
            has_error = True
            print()
            logging.error(f"Mod manifest {repo} {release.tag_name} missing required field: {e}")
        except Exception as e:
            has_error = True
            print()
            logging.error(f"Failed to process release {repo} {release.tag_name}: {e}")

    if has_error:
        print()

    results.sort(key=lambda x: x.release_date, reverse=True)
        
    logging.info(f"Successfully processed {len(results)} releases for {repo}")
    return results

def process_release(repo: Repo, release: GitRelease) -> Release:
    # Download the mod json
    mod_json_url = f"https://raw.githubusercontent.com/{repo}/{release.tag_name}/mod.json"

    logging.info(f"Downloading mod.json from {mod_json_url}")
    response = requests.get(mod_json_url)

    if response.status_code == 404:
        raise Exception(f"mod.json does not exist for this release.")
    elif response.status_code != 200:
        raise Exception(f"Failed to download mod.json from {mod_json_url} with status code {response.status_code}")

    response_json = response.json()

    response_json["repo_url"] = repo.github_url()
    manifest = Manifest.from_dict(response_json)
    pak = find_pak_file(release)

    pak_error = pak if isinstance(pak, str) else None
    tag_error = validate_tags(manifest.tags)
    mod_type_error = validate_mod_type(manifest.mod_type)
    dependency_errors = validate_dependency_versions(manifest.dependencies)
    tag_name_error = validate_version_tag_name(release.tag_name)

    if pak_error or tag_error or mod_type_error or dependency_errors or tag_name_error:
        all_errors = filter(lambda x: x is not None, [pak_error, tag_error, mod_type_error, tag_name_error] + dependency_errors)
        error_string = "\n\t" + "\n\t".join(all_errors)
        raise Exception(f"Mod manifest {repo} {release.tag_name} failed validation: {error_string}")

    # Download the pak and calculate hash of pak file
    pak_download = requests.get(pak.browser_download_url)
    pak_hash = sha512_sum(pak_download.content)
    
    return Release(
        tag=release.tag_name,
        hash=pak_hash,
        pak_file_name=pak.name,
        release_date=pak.updated_at,
        manifest=manifest
    )

def find_pak_file(release) -> Any | str:
    paks = list(filter(lambda asset: asset.name.endswith(".pak"), release.get_assets()))

    if len(paks) == 0:
        return f"No pak file found for release {release.tag_name}."
    
    if len(paks) > 1:
        return f"Multiple pak files found for release {release.tag_name}."
    
    pak = paks[0]

    return pak

# Should line up with https://github.com/Chiv2-Community/C2GUILauncher/blob/main/C2GUILauncher/src/JsonModels/Mod.cs#L29-L38
VALID_TAGS = ["Mutator", "Map", "Cosmetic", "Audio", "Model", "Weapon", "Doodad", "Explicit"]

def validate_version_tag_name(tag_name: str) -> Optional[str]:
    if tag_name.startswith("v"):
        tag_name = tag_name[1:]

    try:
        Version(tag_name)
        return None
    except ValueError as e:
        return f"Version Tag '{tag_name}' Does not conform to the semver spec: {e}"

def validate_dependency_versions(dependencies: List[Dependency]) -> List[str]:
    errors = []
    for dependency in dependencies:
        try:
            input_version_range = dependency.version
            if input_version_range.startswith("v"):
                input_version_range = input_version_range[1:]

            SimpleSpec(input_version_range)
        except ValueError as e:
            dependency_name = "/".join(dependency.repo_url.split("/")[-2:])
            errors.append(f"Version Range '{dependency.version}' for dependency '{dependency_name}' does not conform to the semver spec: {e}")

    return errors

def validate_tags(tags: List[str]) -> Optional[str]:
    invalid_tags = list(filter(lambda tag: tag not in VALID_TAGS, tags))
    if len(invalid_tags) > 0:
        return f"Invalid tags: {invalid_tags}. Valid tags are: {VALID_TAGS}"
    return None

# Should line up with https://github.com/Chiv2-Community/C2GUILauncher/blob/main/C2GUILauncher/src/JsonModels/Mod.cs#L22-L27
VALID_MOD_TYPES = [
    "Client", "Server", "Shared"
]

def validate_mod_type(mod_type: str) -> Optional[str]:
    if mod_type not in VALID_MOD_TYPES:
        return f"Invalid mod type: {mod_type}. Valid types are: {VALID_MOD_TYPES}"
