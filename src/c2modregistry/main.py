from __future__ import annotations
import argparse
from datetime import datetime
import functools
import json
import os
from typing import Callable, Dict, List, Optional, Tuple

from c2modregistry import add_release_tag, initialize_repo
from c2modregistry import Mod
from c2modregistry import get_all_text_lines_in_directory, repo_to_index_entry, parse_redirects
from c2modregistry.models import Dependency, Release, Repo
from c2modregistry.package_list import generate_package_list, load_package_list, load_redirects

from semantic_version import SimpleSpec, Version

import logging

level = os.environ.get("LOG_LEVEL", "WARNING")
logging.basicConfig(format='%(asctime)s %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=level)


DEFAULT_REGISTRY_PATH = "./registry"
DEFAULT_PACKAGE_DB_DIR = "./package_db"
DEFAULT_MOD_LIST_INDEX_PATH = f"{DEFAULT_PACKAGE_DB_DIR}/mod_list_index.txt"
DEFAULT_PACKAGES_DIR = f"{DEFAULT_PACKAGE_DB_DIR}/packages"

class PackageManagerJsonEncoder(json.JSONEncoder):
    """A custom JSON encoder that can encode datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

json_encoder = PackageManagerJsonEncoder()

def main() -> None:
    argparser = argparse.ArgumentParser(description="Manage the mod registry.")

    # add dry-run flag
    argparser.add_argument("--dry-run", action="store_true", help="Don't actually make any changes.")
    
    subparsers = argparser.add_subparsers(dest="command", required=True)

    init_subparser = subparsers.add_parser("init", help="Initialize a mod repo.")
    init_subparser.add_argument("repo_url", type=str, help="The repo url to add or remove.")

    process_registry_updates_subparser = subparsers.add_parser("process-registry-updates", help="Find any new package list entries and load all of their releases.")

    add_subparser = subparsers.add_parser("add", help="Add a release to a mod repo.")
    add_subparser.add_argument("repo_url", type=str, help="The repo url to add or remove.")
    add_subparser.add_argument("release_tag", type=str, help="The release tag to add or remove.")

    remove_subparser = subparsers.add_parser("remove", help="Remove mod from the repo.")
    remove_subparser.add_argument("repo_url", type=str, help="The repo url to add or remove.")

    args = argparser.parse_args()

    if args.command == "process-registry-updates":
        process_registry_updates("registry", "package_db", args.dry_run)
    elif args.command == "init":
        [org, repoName] = args.repo_url.strip().split("/")[-2:]
        redirects = load_redirects("package_db")
        init([Repo(org, repoName)], redirects, args.dry_run)
    elif args.command == "add":
        [org, repoName] = args.repo_url.strip().split("/")[-2:]
        redirects = load_redirects("package_db")
        add_release(Repo(org, repoName), args.release_tag.strip(), redirects, args.dry_run)
    elif args.command == "remove":
        [org, repoName] = args.repo_url.strip().split("/")[-2:]
        redirects = load_redirects("package_db")
        remove_mods([Repo(org, repoName)], redirects, args.dry_run)
    else:
        logging.error("Unknown command.")
        exit(1)

def process_registry_updates(registry_dir: str, package_db_path: str, dry_run: bool) -> None:
    # Get repo lines from the registry dir

    new_redirect_lines = get_all_text_lines_in_directory(os.path.join(registry_dir, "redirects"))
    new_redirects = parse_redirects(new_redirect_lines)
    existing_redirect_lines = load_redirects(package_db_path)

    logging.info(f"Loaded {len(new_redirects)} new redirect entries.")
    logging.info(f"Found {len(existing_redirect_lines)} existing redirect entries.")

    with open(package_db_path + os.path.sep + "redirects.txt", "w") as file:
        file.write('\n'.join(new_redirect_lines))

    logging.info("Loading package list entries...")
    updated_index_entries = generate_package_list(registry_dir)
    previous_index_entries = [] 
    try:
        with open(os.path.join(package_db_path, "mod_list_index.txt"), "r") as file:
            previous_index_entries = file.read().splitlines()
    except FileNotFoundError:
        pass

    new_entries = list(set(updated_index_entries) - set(previous_index_entries))
    removed_entries = list(set(previous_index_entries) - set(updated_index_entries)) 
    failed = False

    if len(new_entries) > 0:
        logging.info(f"Adding {len(new_entries)} new packages to the package list...")
        try:
            split_entries = [entry.split("/") for entry in new_entries]
            repo_entries = [Repo(entry[0], entry[1]) for entry in split_entries]
            init(repo_entries, new_redirects, dry_run)
        except Exception as e:
            # If we fail to initialize a repo, remove it from the package list
            logging.error(f"Failed to initialize repos {repo_entries}: {e}\n")
            failed = True
    
    if len(removed_entries) > 0:
        logging.info(f"Removing {len(removed_entries)} packages from the package list...")
        try:
            split_entries = [entry.split("/") for entry in removed_entries]
            repo_entries = [Repo(entry[0], entry[1]) for entry in split_entries]
            remove_mods(repo_entries, new_redirects, dry_run)
        except Exception as e:
            # If we fail to remove a repo, add it back to the package list
            print(f"Failed to remove repos {repo_entries}: {e}\n")
            failed = True

    if failed:
        logging.error(f"Failures occurred while processing the package list.")
        logging.error("The package list has not been updated.")
        exit(1)

    if dry_run:
        logging.warning("Dry run; not writing to package list.")
        return

    if not os.path.exists(DEFAULT_PACKAGE_DB_DIR):
        os.makedirs(DEFAULT_PACKAGE_DB_DIR)

    with open(package_db_path + os.path.sep + "/mod_list_index.txt", "w") as file:
        file.write('\n'.join(updated_index_entries))

    logging.info("Package list built.")

def init(repos: List[Repo], redirects: Dict[str, str], dry_run: bool) -> None:
    logging.info(f"Initializing {len(repos)} repos...")
    mods = [initialize_repo(repo) for repo in repos]
    filtered_mods = [mod for mod in mods if mod is not None]

    if len(filtered_mods) != len(repos):
        logging.error("Failed to initialize some repos.")
        exit(1)
    
    validate_package_db(DEFAULT_PACKAGE_DB_DIR, filtered_mods, redirects)

    if dry_run:
        logging.warning("Dry run; not writing to package dir.")
        return

    for mod in filtered_mods:
        [org, repoName] = mod.latest_manifest.repo_url.split("/")[-2:]

        if not os.path.exists(f"{DEFAULT_PACKAGES_DIR}/{org}"):
            os.makedirs(f"{DEFAULT_PACKAGES_DIR}/{org}")

        with open(f"{DEFAULT_PACKAGES_DIR}/{org}/{repoName}.json", "w") as file:
            file.write(json_encoder.encode(mod.asdict()))


        logging.info(f"Repo {org}/{repoName} initialized.")

    logging.info("Successfully initialized all repos.")

def add_release(repo: Repo, release_tag: str, redirects: Dict[str, str], dry_run: bool) -> None:
    logging.info(f"Loading mod metadata for {repo}...")
    mod = load_mod(repo, DEFAULT_PACKAGES_DIR)

    if mod is None:
        logging.info(f"Mod {repo} not initialized.")
        init([repo], redirects, dry_run)

        # No need to coninue. Initialization will get all releases.
        return
    
    tags = [release.tag for release in mod.releases]
    
    if release_tag in tags:
        logging.warning(f"Release {release_tag} already exists in repo {repo}.")
        return
    
    logging.info(f"Adding release {release_tag} to repo {repo}...")
    updated_mod = add_release_tag(mod, release_tag)

    if updated_mod is None:
        logging.info(f"Failed to add release {release_tag} to repo {repo}.")
        exit(1)
        return
    
    validate_package_db(DEFAULT_PACKAGE_DB_DIR, [updated_mod], redirects)

    if dry_run:
        logging.warning("Dry run; not writing to mod metadata.")
        return

    with open(f"{DEFAULT_PACKAGES_DIR}/{repo}.json", "w") as file:
        logging.info(f"Writing updated mod metadata for {repo}...")
        file.write(json_encoder.encode(updated_mod.asdict()))
    
    logging.info(f"Successfully added release {release_tag} to repo {repo}.")

def remove_mods(repo_list: List[Repo], redirects: Dict[str, str], dry_run: bool) -> None:
    logging.info(f"Removing {len(repo_list)} mods...")

    removed_mod_package_path_segements = [f"/{repo.org}/{repo.name}.json" for repo in repo_list]

    def filter_func(mod_path: str) -> bool:
        for removed_mod_package_path_segement in removed_mod_package_path_segements:
            if removed_mod_package_path_segement in mod_path:
                return False

        return True


    validate_package_db(DEFAULT_PACKAGE_DB_DIR, [], redirects, filter_func)
        
    if dry_run:
        logging.warning("Dry run; not writing to mod metadata.")
        return

    for repo in repo_list:
        os.remove(f"{DEFAULT_PACKAGES_DIR}/{repo}.json")
        logging.info(f"Successfully removed mod {repo}.")

        # If org directory is empty, remove it
        if not os.listdir(f"{DEFAULT_PACKAGES_DIR}/{repo.org}"):
            logging.info(f"Removing empty org {repo.org}...")
            os.rmdir(f"{DEFAULT_PACKAGES_DIR}/{repo.org}")
    
    
    logging.info(f"Successfully removed {len(repo_list)} mods.")

def load_mod(repo: Repo, package_dir: str) -> Optional[Mod]:
    try:
        with open(f"{package_dir}/{repo}.json", "r") as file:
            mod_dict = json.loads(file.read())
            return Mod.from_dict(mod_dict)
    except FileNotFoundError:
        return None
    
def validate_package_db(package_dir: str, additional_mods: List[Mod], redirects: Dict[str, str], mod_path_filter: Callable[[str], bool] = lambda x: True) -> None:
    logging.info("Validating package database...")
    packages = load_package_list(package_dir + "/mod_list_index.txt")
    mods: List[Mod] = additional_mods

    # Load all mods
    for package in packages:
        package_path = f"{package_dir}/packages/{package}.json"
        if mod_path_filter(package_path):
            try:
                with open(package_path, "r") as file:
                    mod_dict = json.loads(file.read())
                    mod = Mod.from_dict(mod_dict)

                    if mod is None:
                        logging.error(f"Failed to load mod {package} during validation.")
                        exit(1)

                    mods.append(mod)

            except FileNotFoundError:
                logging.error(f"Package {package} not found during validation.")
                exit(1)
    
    # Check for missing dependencies
    missing_deps: List[Tuple[Release, Dependency]] = []
    for mod in mods:
        for release in mod.releases:
            for dep in release.manifest.dependencies:
                found_release = find_dependency(mods, dep, redirects)
                if found_release is None:
                    missing_deps.append((release, dep))

    if len(missing_deps) > 0:
        logging.error(f"{len(missing_deps)} missing dependencies:")

        for (release, dep) in missing_deps:
            logging.error(f"{release.manifest.name} {release.tag} requires missing dependency {dep.repo_url} {dep.version}")

        logging.error("Package database is invalid.")
        exit(1)
    
    logging.info("Package database is valid.")
                
def find_dependency(mods: List[Mod], dep: Dependency, redirects: Dict[str, str]) -> Optional[Release]:
    for mod in mods:
        for release in mod.releases:
            release_tag = release.tag
            if release_tag.startswith("v"):
                release_tag = release_tag[1:]

            dep_version = dep.version
            if dep_version.startswith("v"):
                dep_version = dep_version[1:]

            resolved_manifest_url = resolve_redirects(redirects, release.manifest.repo_url)
            resolved_dep_url = resolve_redirects(redirects, dep.repo_url)
            if resolved_manifest_url == resolved_dep_url and Version(release_tag) in SimpleSpec(dep_version):
                return release

    return None

def resolve_redirects(redirects: Dict[str,str], repo: str) -> str:
    if repo in redirects:
        result = redirects[repo]
        return resolve_redirects(redirects, result)
    else:
        return repo
    
if __name__ == "__main__":
    main()