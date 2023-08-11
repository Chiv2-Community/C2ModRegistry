from typing import List, Optional
import requests
from github import Github, Auth
from github.GitRelease import GitRelease
from os import environ
from .models import Mod, Release, Manifest
from .hashes import get_remote_sha512_sum

auth = Auth.Token(environ.get("GITHUB_TOKEN") or "")
github_client = Github(auth=auth)


def initialize_repo(org: str, repoName: str) -> Optional[Mod]:
    try:
        releases = all_releases(org, repoName)

        if len(releases) == 0:
            print(f"Repo {org}/{repoName} has no releases.")
            return None

        return Mod(
            latest_manifest=releases[-1].manifest,
            releases=releases
        )
    except Exception as e:
        print(f"Failed to initialize repo {org}/{repoName}: {e}")
        return None

def add_release_tag(mod: Mod, release_tag: str) -> Optional[Mod]:
    [org, repoName] = mod.latest_manifest.repo_url.split("/")[-2:]
    try:
        github_repo = github_client.get_repo(f"{org}/{repoName}")
        release = github_repo.get_release(release_tag)
        
        mod_releases = mod.releases + [process_release(org, repoName, release)]

        mod_releases.sort(key=lambda x: x.release_date, reverse=True)

        return Mod(
            latest_manifest=mod_releases[-1].manifest,
            releases=mod.releases + [process_release(org, repoName, release)]
        )

    except Exception as e:
        print(f"Failed to add release tag {release_tag} for repo {org}/{repoName}: {e}")
        return None

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
        except KeyError as e:
            print(f"Mod manifest missing required field: {e}")
        except Exception as e:
            print(f"Failed to get release for tag {release.tag_name}: {e}")

    results.sort(key=lambda x: x.release_date, reverse=True)
        
    print(f"Successfully processed {len(results)} releases for {org}/{repoName}")
    return results

def process_release(org: str, repoName: str, release: GitRelease) -> Release:
    # Download the mod json
    mod_json_url = f"https://raw.githubusercontent.com/{org}/{repoName}/{release.tag_name}/mod.json"

    print(f"Downloading mod.json from {mod_json_url}")
    response = requests.get(mod_json_url)

    if response.status_code == 404:
        raise Exception(f"mod.json does not exist for this release.")
    elif response.status_code != 200:
        raise Exception(f"Failed to download mod.json from {mod_json_url} with status code {response.status_code}")

    repo_url = f"https://github.com/{org}/{repoName}"
    response_json = response.json()

    response_json["repo_url"] = repo_url
    mod_json = Manifest.from_dict(response_json)

    paks = list(filter(lambda asset: asset.name.endswith(".pak"), release.get_assets()))

    if len(paks) == 0:
        raise Exception(f"No pak file found for release {release.tag_name}.")
    
    if len(paks) > 1:
        raise Exception(f"Multiple pak files found for release {release.tag_name}.")
    
    pak = paks[0]

    # Download the pak and calculate hash of pak file
    pak_hash = get_remote_sha512_sum(pak.browser_download_url)

    
    return Release(
        tag=release.tag_name,
        hash=pak_hash,
        pak_file_name=paks[0].name,
        release_date=paks[0].updated_at,
        manifest=mod_json
    )
    