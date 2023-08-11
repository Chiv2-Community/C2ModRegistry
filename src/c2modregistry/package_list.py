from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import os

def repo_to_index_entry(repo: str) -> str:
    """An index entry is just $org/$repoName, which happens to be the last 2 pieces of a github repo url. This converts repo urls to index entries."""
    repo = repo.strip().rstrip("/")
    return "/".join(repo.split("/")[-2:])

def load_package_list(path: str) -> List[str]:
    """Loads the package list from a file."""
    try:
        with open(path, 'r') as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

def generate_package_list(directory: str) -> List[str]:
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
                        all_lines.append(repo_to_index_entry(line))

    return all_lines