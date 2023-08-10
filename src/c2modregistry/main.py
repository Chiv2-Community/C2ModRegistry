from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from typing import Optional

from c2modregistry import add_release_tag, initialize_repo
from c2modregistry import Mod
from c2modregistry import get_package_list, repo_to_index_entry

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
    
    subparsers = argparser.add_subparsers(dest="command", required=True)

    init_subparser = subparsers.add_parser("init", help="Initialize a mod repo.")
    init_subparser.add_argument("repo_url", type=str, help="The repo url to add or remove.")

    process_registry_updates_subparser = subparsers.add_parser("process-registry-updates", help="Find any new package list entries and load all of their releases.")

    add_subparser = subparsers.add_parser("add", help="Add a release to a mod repo.")
    add_subparser.add_argument("repo_url", type=str, help="The repo url to add or remove.")
    add_subparser.add_argument("release_tag", type=str, help="The release tag to add or remove.")

    remove_subparser = subparsers.add_parser("remove", help="Remove a release from a mod repo.")
    remove_subparser.add_argument("repo_url", type=str, help="The repo url to add or remove.")

    args = argparser.parse_args()

    if args.command == "process-registry-updates":
        process_registry_updates("./registry", "./package_db/mod_list_index.txt")
    elif args.command == "init":
        [org, repoName] = args.repo_url.split("/")[-2:]
        init(org, repoName)
    elif args.command == "add":
        [org, repoName] = args.repo_url.split("/")[-2:]
        add_release(org, repoName, args.release_tag)
    elif args.command == "remove":
        [org, repoName] = args.repo_url.split("/")[-2:]
        remove_mod(org, repoName)
    else:
        print("Unknown command.")

def process_registry_updates(registry_dir: str, mod_list_index_path: str) -> None:
    # Get repo lines from the registry dir
    print("Loading package list entries...")
    updated_index_entries = get_package_list(registry_dir)
    previous_index_entries = []
    try:
        with open(mod_list_index_path, "r") as file:
            previous_index_entries = file.read().splitlines()
    except FileNotFoundError:
        pass

    new_entries = list(set(updated_index_entries) - set(previous_index_entries))
    removed_entries = list(set(previous_index_entries) - set(updated_index_entries)) 
    failures = 0

    print(f"Adding {len(new_entries)} new packages to the package list...")
    print("")
    for entry in new_entries:
        [org, repoName] = entry.split("/")
        try:
            init(org, repoName)
            print("")
        except Exception as e:
            # If we fail to initialize a repo, remove it from the package list
            print(f"Failed to initialize repo {org}/{repoName}: {e}\n")
            updated_index_entries.remove(entry)
            failures += 1
    
    print(f"Removing {len(removed_entries)} packages from the package list...")
    for entry in removed_entries:
        [org, repoName] = entry.split("/")
        try:
            remove_mod(org, repoName)
        except Exception as e:
            # If we fail to remove a repo, add it back to the package list
            print(f"Failed to remove repo {org}/{repoName}: {e}")
            updated_index_entries.append(entry)
            failures += 1

    print(f"Writing {len(updated_index_entries)} packages to the package list. ({failures} failures)")

    if not os.path.exists(DEFAULT_PACKAGE_DB_DIR):
        os.makedirs(DEFAULT_PACKAGE_DB_DIR)

    with open(mod_list_index_path, "w") as file:
        file.write('\n'.join(updated_index_entries))

    print("Package list built.")

def init(org: str, repoName: str) -> None:
    print(f"Initializing repo {org}/{repoName}...")
    mod = initialize_repo(org, repoName)

    if not os.path.exists(f"{DEFAULT_PACKAGES_DIR}/{org}"):
        os.makedirs(f"{DEFAULT_PACKAGES_DIR}/{org}")

    with open(f"{DEFAULT_PACKAGES_DIR}/{org}/{repoName}.json", "w") as file:
        file.write(json_encoder.encode(mod.asdict()))

def add_release(org: str, repoName: str, release_tag: str) -> None:
    print(f"Loading mod metadata for {org}/{repoName}...")
    mod = load_mod(org, repoName, DEFAULT_PACKAGES_DIR)

    if mod is None:
        print(f"Mod {org}/{repoName} not initialized.")
        init(org, repoName)

        # No need to coninue. Initialization will get all releases.
        return
    
    print(f"Adding release {release_tag} to repo {org}/{repoName}...")
    updated_mod = add_release_tag(mod, release_tag)

    with open(f"{DEFAULT_PACKAGES_DIR}/{org}/{repoName}.json", "w") as file:
        print(f"Writing updated mod metadata for {org}/{repoName}...")
        file.write(json_encoder.encode(updated_mod.asdict()))
    
    print(f"Successfully added release {release_tag} to repo {org}/{repoName}.")

def remove_mod(org: str, repoName: str) -> None:
    print(f"Loading mod metadata for {org}/{repoName}...")
    mod = load_mod(org, repoName, DEFAULT_PACKAGES_DIR)

    if mod is None:
        print(f"Mod {org}/{repoName} not found.")
        return
    
    print(f"Removing mod {org}/{repoName}...")
    os.remove(f"{DEFAULT_PACKAGES_DIR}/{org}/{repoName}.json")

    # If org directory is empty, remove it
    if not os.listdir(f"{DEFAULT_PACKAGES_DIR}/{org}"):
        print(f"Removing empty org {org}...")
        os.rmdir(f"{DEFAULT_PACKAGES_DIR}/{org}")

def load_mod(org: str, repoName: str, package_dir: str) -> Optional[Mod]:
    try:
        with open(f"{package_dir}/{org}/{repoName}.json", "r") as file:
            mod_dict = json.loads(file.read())
            return Mod.from_dict(mod_dict)
    except FileNotFoundError:
        return None


if __name__ == "__main__":
    main()