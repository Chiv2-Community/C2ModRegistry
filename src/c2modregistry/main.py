from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from typing import Callable, List, Optional, Tuple

from c2modregistry import add_release_tag, initialize_repo
from c2modregistry import Mod
from c2modregistry import generate_package_list, repo_to_index_entry
from c2modregistry.models import Dependency, Release
from c2modregistry.package_list import load_package_list

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
        process_registry_updates("./registry", "./package_db/mod_list_index.txt", args.dry_run)
    elif args.command == "init":
        [org, repoName] = args.repo_url.split("/")[-2:]
        init([(org, repoName)], args.dry_run)
    elif args.command == "add":
        [org, repoName] = args.repo_url.split("/")[-2:]
        add_release(org, repoName, args.release_tag, args.dry_run)
    elif args.command == "remove":
        [org, repoName] = args.repo_url.split("/")[-2:]
        remove_mods([(org, repoName)], args.dry_run)
    else:
        print("Unknown command.")

def process_registry_updates(registry_dir: str, mod_list_index_path: str, dry_run: bool) -> None:
    # Get repo lines from the registry dir
    print("Loading package list entries...")
    updated_index_entries = generate_package_list(registry_dir)
    previous_index_entries = []
    try:
        with open(mod_list_index_path, "r") as file:
            previous_index_entries = file.read().splitlines()
    except FileNotFoundError:
        pass

    new_entries = list(set(updated_index_entries) - set(previous_index_entries))
    removed_entries = list(set(previous_index_entries) - set(updated_index_entries)) 
    failed = False

    if len(new_entries) > 0:
        print(f"Adding {len(new_entries)} new packages to the package list...")
        try:
            split_entries = [entry.split("/") for entry in new_entries]
            tupled_entries = [(entry[0], entry[1]) for entry in split_entries]
            init(tupled_entries, dry_run)
        except Exception as e:
            # If we fail to initialize a repo, remove it from the package list
            print(f"Failed to initialize repos {tupled_entries}: {e}\n")
            failed = True
    
    if len(removed_entries) > 0:
        print(f"Removing {len(removed_entries)} packages from the package list...")
        try:
            split_entries = [entry.split("/") for entry in removed_entries]
            tupled_entries = [(entry[0], entry[1]) for entry in split_entries]
            remove_mods(tupled_entries, dry_run)
        except Exception as e:
            # If we fail to remove a repo, add it back to the package list
            print(f"Failed to remove repos {tupled_entries}: {e}\n")
            failed = True

    if failed:
        print(f"Failures occurred while processing the package list.")
        print("The package list has not been updated.")
        exit(1)

    if dry_run:
        print("Dry run; not writing to package list.")
        return

    if not os.path.exists(DEFAULT_PACKAGE_DB_DIR):
        os.makedirs(DEFAULT_PACKAGE_DB_DIR)

    with open(mod_list_index_path, "w") as file:
        file.write('\n'.join(updated_index_entries))

    print("Package list built.")

def init(repos: List[Tuple[str, str]], dry_run: bool) -> None:
    print(f"Initializing {len(repos)} repos...")
    mods = [initialize_repo(org, repoName) for (org, repoName) in repos]
    filtered_mods = [mod for mod in mods if mod is not None]

    if len(filtered_mods) != len(repos):
        print("Failed to initialize some repos.")
        exit(1)
    
    validate_package_db(DEFAULT_PACKAGE_DB_DIR, filtered_mods)

    if dry_run:
        print("Dry run; not writing to package dir.")
        return

    for mod in filtered_mods:
        [org, repoName] = mod.latest_manifest.repo_url.split("/")[-2:]

        if not os.path.exists(f"{DEFAULT_PACKAGES_DIR}/{org}"):
            os.makedirs(f"{DEFAULT_PACKAGES_DIR}/{org}")

        with open(f"{DEFAULT_PACKAGES_DIR}/{org}/{repoName}.json", "w") as file:
            file.write(json_encoder.encode(mod.asdict()))


        print(f"Repo {org}/{repoName} initialized.")

    print("Successfully initialized all repos.")

def add_release(org: str, repoName: str, release_tag: str, dry_run: bool) -> None:
    print(f"Loading mod metadata for {org}/{repoName}...")
    mod = load_mod(org, repoName, DEFAULT_PACKAGES_DIR)

    if mod is None:
        print(f"Mod {org}/{repoName} not initialized.")
        init([(org, repoName)], dry_run)

        # No need to coninue. Initialization will get all releases.
        return
    
    tags = [release.tag for release in mod.releases]
    
    if release_tag in tags:
        print(f"Release {release_tag} already exists in repo {org}/{repoName}.")
        return
    
    print(f"Adding release {release_tag} to repo {org}/{repoName}...")
    updated_mod = add_release_tag(mod, release_tag)

    if updated_mod is None:
        print(f"Failed to add release {release_tag} to repo {org}/{repoName}.")
        exit(1)
        return
    
    validate_package_db(DEFAULT_PACKAGE_DB_DIR, [updated_mod])

    if dry_run:
        print("Dry run; not writing to mod metadata.")
        return

    with open(f"{DEFAULT_PACKAGES_DIR}/{org}/{repoName}.json", "w") as file:
        print(f"Writing updated mod metadata for {org}/{repoName}...")
        file.write(json_encoder.encode(updated_mod.asdict()))
    
    print(f"Successfully added release {release_tag} to repo {org}/{repoName}.")

def remove_mods(mods: List[Tuple[str, str]], dry_run: bool) -> None:
    print(f"Removing {len(mods)} mods...")

    removed_mod_package_path_segements = [f"/{org}/{repoName}.json" for (org, repoName) in mods]

    def filter_func(mod_path: str) -> bool:
        for removed_mod_package_path_segement in removed_mod_package_path_segements:
            if removed_mod_package_path_segement in mod_path:
                return False

        return True


    validate_package_db(DEFAULT_PACKAGE_DB_DIR, [], filter_func)
        
    if dry_run:
        print("Dry run; not writing to mod metadata.")
        return

    for (org, repoName) in mods:
        os.remove(f"{DEFAULT_PACKAGES_DIR}/{org}/{repoName}.json")

        # If org directory is empty, remove it
        if not os.listdir(f"{DEFAULT_PACKAGES_DIR}/{org}"):
            print(f"Removing empty org {org}...")
            os.rmdir(f"{DEFAULT_PACKAGES_DIR}/{org}")
    
            print(f"Successfully removed mod {org}/{repoName}.")
    
    print(f"Successfully removed {len(mods)} mods.")

def load_mod(org: str, repoName: str, package_dir: str) -> Optional[Mod]:
    try:
        with open(f"{package_dir}/{org}/{repoName}.json", "r") as file:
            mod_dict = json.loads(file.read())
            return Mod.from_dict(mod_dict)
    except FileNotFoundError:
        return None
    
def validate_package_db(package_dir: str, additional_mods: List[Mod], mod_path_filter: Callable[[str], bool] = lambda x: True) -> None:
    print("Validating package database...")
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
                        print(f"Failed to load mod {package} during validation.")
                        exit(1)

                    mods.append(mod)

            except FileNotFoundError:
                print(f"Package {package} not found during validation.")
                exit(1)
    
    # Check for missing dependencies
    missing_deps: List[Tuple[Release, Dependency]] = []
    for mod in mods:
        for release in mod.releases:
            for dep in release.manifest.dependencies:
                found_release = find_dependency(mods, dep)
                if found_release is None:
                    missing_deps.append((release, dep))

    if len(missing_deps) > 0:
        print(f"{len(missing_deps)} missing dependencies:")

        for (release, dep) in missing_deps:
            print(f"{release.manifest.name} {release.tag} requires missing dependency {dep.repo_url} {dep.version}")

        print("Package database is invalid.")
        exit(1)
    
    print("Package database is valid.")
                
def find_dependency(mods: List[Mod], dep: Dependency) -> Optional[Release]:
    for mod in mods:
        for release in mod.releases:
            if release.manifest.repo_url == dep.repo_url and dep.version in release.tag:
                return release

    return None

    print("Package database is valid.")

if __name__ == "__main__":
    main()