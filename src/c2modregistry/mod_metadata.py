from typing import List, Optional
import requests
from github import Github, Auth
from github.GitRelease import GitRelease
from os import environ
from .models import Mod, Release, Manifest, Repo
from .hashes import sha512_sum

auth = Auth.Token(environ.get("GITHUB_TOKEN") or "")
github_client = Github(auth=auth)


def initialize_repo(repo: Repo) -> Optional[Mod]:
    try:
        releases = all_releases(repo)

        if len(releases) == 0:
            print(f"Repo {repo} has no releases.")
            return None

        return Mod(
            latest_manifest=releases[0].manifest,
            releases=releases
        )
    except Exception as e:
        print(f"Failed to initialize repo {repo}: {e}")
        return None

def add_release_tag(mod: Mod, release_tag: str) -> Optional[Mod]:
    (org, repoName) = mod.latest_manifest.repo_url.split("/")[-2:]
    repo = Repo(org, repoName)
    try:
        github_repo = github_client.get_repo(str(repo))
        release = github_repo.get_release(release_tag)
        
        mod_releases = mod.releases + [process_release(repo, release)]

        mod_releases.sort(key=lambda x: x.release_date, reverse=True)

        return Mod(
            latest_manifest=mod_releases[0].manifest,
            releases=mod_releases
        )

    except Exception as e:
        print(f"Failed to add release tag {release_tag} for repo {repo}: {e}")
        return None

def all_releases(repo: Repo) -> List[Release]:
    print(f"Getting all releases for {repo}")
    github_repo = github_client.get_repo(str(repo))
    git_releases = github_repo.get_releases()

    print(f"Found {git_releases.totalCount} releases for {repo}")
    results = []
    for release in git_releases:
        try:
            print(f"Processing release {release.tag_name} for {repo}")
            results.append(process_release(repo, release))
        except KeyError as e:
            print(f"Mod manifest missing required field: {e}")
        except Exception as e:
            print(f"Failed to get release for tag {release.tag_name}: {e}")

    results.sort(key=lambda x: x.release_date, reverse=True)
        
    print(f"Successfully processed {len(results)} releases for {repo}")
    return results

def process_release(repo: Repo, release: GitRelease) -> Release:
    # Download the mod json
    mod_json_url = f"https://raw.githubusercontent.com/{repo}/{release.tag_name}/mod.json"

    print(f"Downloading mod.json from {mod_json_url}")
    response = requests.get(mod_json_url)

    if response.status_code == 404:
        raise Exception(f"mod.json does not exist for this release.")
    elif response.status_code != 200:
        raise Exception(f"Failed to download mod.json from {mod_json_url} with status code {response.status_code}")

    response_json = response.json()

    response_json["repo_url"] = repo.github_url()
    mod_json = Manifest.from_dict(response_json)

    paks = list(filter(lambda asset: asset.name.endswith(".pak"), release.get_assets()))

    if len(paks) == 0:
        raise Exception(f"No pak file found for release {release.tag_name}.")
    
    if len(paks) > 1:
        raise Exception(f"Multiple pak files found for release {release.tag_name}.")
    
    pak = paks[0]

    # Download the pak and calculate hash of pak file
    pak_download = requests.get(pak.browser_download_url)
    pak_hash = sha512_sum(pak_download.content)
    

    
    return Release(
        tag=release.tag_name,
        hash=pak_hash,
        pak_file_name=paks[0].name,
        release_date=paks[0].updated_at,
        manifest=mod_json
    )
    