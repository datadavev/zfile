import contextlib
import dataclasses
import functools
import logging
import typing

import httpx
from httpx import Response

__version__ = "0.1.0"

JSON_MEDIA = "application/json"
TIMEOUT_SECS = 5.0
LRU_CACHE_SIZE = 100

@dataclasses.dataclass
class ZFile:
    id: str
    key: str
    size: int
    checksum: str
    content: str


def size_str_to_int(size_str: str) -> int:
    return int(size_str)


def split_doi_file(src:str)->tuple[str, typing.Optional[str]]:
    # doi should be of the form prefix/value
    # the last / here is expected to delimit the doi from the file name
    if src.count("/") < 2:
        return (src, None)
    parts = src.rsplit("/", 1)
    return (parts[0], parts[1], )


@functools.lru_cache(maxsize=LRU_CACHE_SIZE)
def getLinkHeaders(url: str)-> typing.Dict[str, any]:
    response = httpx.get(
        url,
        headers={"Accept": f"{JSON_MEDIA}, */*; q=0.1"},
        follow_redirects=True,
        timeout=TIMEOUT_SECS #seconds
    )
    return response.links


@functools.lru_cache(maxsize=LRU_CACHE_SIZE)
def getZenodoPackageMetadata(doi:str)->typing.Dict[str, typing.Any]:
    url = f"https://doi.org/{doi}"
    links = getLinkHeaders(url)
    url = links.get("linkset",{}).get("url", None)
    if url is None:
        raise ValueError(f"No links found for {doi}")
    return httpx.get(
        url,
        headers = {"Accept": JSON_MEDIA},
        timeout=TIMEOUT_SECS
    ).json()


@functools.lru_cache(maxsize=LRU_CACHE_SIZE)
def getZenodoFileList(doi: str)-> typing.List[ZFile]:
    response = getZenodoPackageMetadata(doi)
    results = []
    for entry in response.get("files", []):
        results.append(ZFile(
            id=entry["id"],
            key=entry["key"],
            size=size_str_to_int(entry["size"]),
            checksum=entry["checksum"],
            content=entry.get("links", {}).get("self")
        ))
    return results

def getZenodoContentUrl(doi: str, filename:str )->str:
    files = getZenodoFileList(doi)
    for f in files:
        if f.key == filename:
            return f.content
    raise ValueError(f"No Zenodo file matching {doi}/{filename}")
