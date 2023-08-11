import gzip
from typing import Dict
import hashlib
import requests

def sha512_sum(data: bytes) -> str:
    # Check if gzipped
    if data[0] == 0x1f and data[1] == 0x8b:
        data = gzip.decompress(data)
    
    digest = hashlib.sha512()
    digest.update(data)
    return digest.hexdigest()
