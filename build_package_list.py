from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import os


def main() -> None:
    # Get repo lines from the registry dir
    print("Loading package list entries...")
    repos = get_all_lines_from_directory("./registry")

    index_entries = list(map(lambda repo: repo_to_index_entry(repo), repos))

    print(f"Writing {len(repos)} packages to the package list.")
    with open("./package_db/mod_list_index.txt", "w") as file:
        file.write('\n'.join(index_entries))

    print("Package list built.")

def repo_to_index_entry(repo: str) -> str:
    return "/".join(repo.split("/")[-2:])

def get_all_lines_from_directory(directory: str) -> list[str]:
    """Gets all lines from all files, ignoring any empty lines or lines starting with #"""
    all_lines = []

    # Get all files in the directory
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        
        # Ensure it's a file and not another directory or symbolic link
        if os.path.isfile(filepath):
            with open(filepath, 'r') as file:
                for line in file:
                    line = line.strip()

                    # Exclude lines that start with '#' or are empty
                    if not line.startswith('#') and line != "":
                        all_lines.append(line.strip())

    return all_lines


if __name__ == "__main__":
    main()