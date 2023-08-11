from typing import Dict
import urllib3
import hashlib

from urllib3 import HTTPSConnectionPool
from urllib3 import BaseHTTPResponse

connection_pools: Dict[str, HTTPSConnectionPool] = {}

# 2GB
MAX_GITHUB_RELEASE_SIZE = 2 * (1024 ** 3)

# 4MB
BUFFER_SIZE = 4 * (1024 ** 2)

def url_to_host(url: str) -> str:
    return url.split("/")[2]

def get_remote_sha512_sum(url: str) -> str:
    host = url_to_host(url)
    if host not in connection_pools:
        connection_pools[host] = HTTPSConnectionPool(host)

    connection: BaseHTTPResponse = connection_pools[host].urlopen("GET", url)

    digest = hashlib.sha512()

    total_read = 0
    while True:
        data = connection.read(BUFFER_SIZE)
        total_read += 4096

        if not data or total_read > MAX_GITHUB_RELEASE_SIZE:
            break

        digest.update(data)

    return digest.hexdigest()
