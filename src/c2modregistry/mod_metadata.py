from typing import List
import requests
from github import Github, Auth
from github.GitRelease import GitRelease
from os import environ
from .models import Mod, Release, Manifest
from natsort import natsorted

auth = Auth.Token(environ.get("GITHUB_TOKEN") or "")
github_client = Github(auth=auth)


def initialize_repo(org: str, repoName: str) -> Mod:
    releases = all_releases(org, repoName)

    return Mod(
        latest_manifest=releases[-1].manifest,
        releases=releases
    )

def add_release_tag(mod: Mod, release_tag: str) -> Mod:
    github_repo = github_client.get_repo(mod.latest_manifest.repo_url)
    release = github_repo.get_release(release_tag)

    [org, repoName] = mod.latest_manifest.repo_url.split("/")[-2:]

    return Mod(
        latest_manifest=mod.latest_manifest,
        releases=mod.releases + [process_release(org, repoName, release)]
    )

def all_releases(org: str, repoName: str) -> List[Release]:
    print(f"Getting all releases for {org}/{repoName}")
    repo = github_client.get_repo(f"{org}/{repoName}")
    git_releases = repo.get_releases()

    print(f"Found {git_releases.totalCount} releases for {org}/{repoName}")
    results = []
    for release in git_releases:
        try:
            print(f"Processing release {release.tag_name} for {org}/{repoName}")
            results.append(process_release(org, repoName, release))
        except Exception as e:
            print(f"Failed to get release for tag {release.tag_name}: {e}")

    natsorted(results, key=lambda x: x.tag)
                
    print(f"Successfully processed {len(results)} releases for {org}/{repoName}")
    return results

def process_release(org: str, repoName: str, release: GitRelease) -> Release:
    # Download the mod json
    mod_json_url = f"https://raw.githubusercontent.com/{org}/{repoName}/{release.tag_name}/mod.json"

    print(f"Downloading mod.json from {mod_json_url}")
    response = requests.get(mod_json_url)

    if response.status_code != 200:
        raise Exception(f"Failed to download mod.json from {mod_json_url} with status code {response.status_code}")

    mod_json = Manifest.from_dict(response.json())

    paks = list(filter(lambda asset: asset.name.endswith(".pak"), release.get_assets()))

    if len(paks) == 0:
        raise Exception(f"No pak file found for release {release.tag_name}.")
    
    if len(paks) > 1:
        raise Exception(f"Multiple pak files found for release {release.tag_name}.")
    
    return Release(
        tag=release.tag_name,
        hash=release.target_commitish,
        pak_file_name=paks[0].name,
        release_date=paks[0].updated_at,
        manifest=mod_json
    )
    