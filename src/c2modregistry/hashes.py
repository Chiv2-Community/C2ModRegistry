import gzip
from typing import Dict
import hashlib
import requests

# 2GB
MAX_GITHUB_RELEASE_SIZE = 2 * (1024 ** 3)

# 4MB
BUFFER_SIZE = 4 * (1024 ** 2)

def url_to_host(url: str) -> str:
    return url.split("/")[2]

def get_remote_sha512_sum(url: str) -> str:
    response = requests.get(url)
    data = response.content

    # Check if gzipped
    if data[0] == 0x1f and data[1] == 0x8b:
        data = gzip.decompress(data)
    
    digest = hashlib.sha512()
    digest.update(data)
    return digest.hexdigest()
