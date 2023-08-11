from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List

@dataclass(frozen=True)
class Repo:
    org: str
    name: str

    def __str__(self) -> str:
        return f"{self.org}/{self.name}"
    
    def github_url(self) -> str:
        return f"https://github.com/{self.org}/{self.name}"

@dataclass(frozen=True)
class Dependency:
    repo_url: str
    version: str

    @staticmethod
    def from_dict(data: Dict) -> "Dependency":
        return Dependency(
            repo_url=data["repo_url"],
            version=data["version"]
        )

@dataclass(frozen=True)
class Manifest:
    repo_url: str
    name: str
    description: str
    mod_type: str
    authors: List[str]
    dependencies: List[Dependency]
    tags: List[str]

    @staticmethod
    def from_dict(data: Dict) -> "Manifest":
        return Manifest(
            repo_url=data["repo_url"],
            name=data["name"],
            description=data["description"],
            mod_type=data["mod_type"],
            authors=data["authors"],
            dependencies=[Dependency.from_dict(dep) for dep in data["dependencies"]],
            tags=data["tags"]
        )

@dataclass(frozen=True)
class Release:
    tag: str
    hash: str
    pak_file_name: str
    release_date: datetime
    manifest: Manifest

    @staticmethod
    def from_dict(data: Dict) -> "Release":
        return Release(
            tag=data["tag"],
            hash=data["hash"],
            pak_file_name=data["pak_file_name"],
            release_date=datetime.fromisoformat(data["release_date"]),
            manifest=Manifest.from_dict(data["manifest"])
        )

@dataclass(frozen=True)
class Mod:
    latest_manifest: Manifest
    releases: List[Release]

    @staticmethod
    def from_dict(data: Dict) -> "Mod":
        return Mod(
            latest_manifest=Manifest.from_dict(data["latest_manifest"]),
            releases=[Release.from_dict(release) for release in data["releases"]]
        )
    
    def asdict(self) -> Dict:
        return asdict(self)
