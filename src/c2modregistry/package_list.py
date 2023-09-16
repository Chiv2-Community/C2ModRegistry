from __future__ import annotations
from dataclasses import dataclass, field
import functools
from typing import List, Optional, Dict
from datetime import datetime
import os

def repo_to_index_entry(repo: str) -> str:
    """An index entry is just $org/$repoName, which happens to be the last 2 pieces of a github repo url. This converts repo urls to index entries."""
    repo = repo.strip().rstrip(os.path.sep)
    return os.path.sep.join(repo.split(os.path.sep)[-2:])

def load_package_list(path: str) -> List[str]:
    """Loads the package list from a file."""
    try:
        with open(path, 'r') as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

def generate_package_list(directory: str) -> List[str]:
    """Gets all lines from all files, ignoring any empty lines or lines starting with #"""
    return list(map(repo_to_index_entry, get_all_text_lines_in_directory(directory)))

def get_all_text_lines_in_directory(directory: str) -> List[str]:
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
                        all_lines.append(line)

    return all_lines

def load_redirects(package_db_dir: str) -> Dict[str, str]:
    """Loads the redirects from the redirects file."""
    redirects_path = os.path.join(package_db_dir, "redirects.txt")
    try:
        with open(redirects_path, 'r') as file:
            return parse_redirects(file.read().splitlines())
    except FileNotFoundError:
        return {}

def parse_redirects(redirect_lines: List[str]) -> Dict[str, str]:
    redirect_lines = [line.strip().split(" -> ") for line in redirect_lines if line.strip() != ""]
    print(redirect_lines)
    return {line[0]: line[1] for line in redirect_lines}
