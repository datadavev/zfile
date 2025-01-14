import pytest

import zfile

def test_known_doi():
    doi = "10.5281/zenodo.11400483"
    zf = zfile.getZenodoFileList(doi)
    assert(len(zf) == 3)

split_cases = (
    ("10.1234/foo/bar.txt", ("10.1234/foo", "bar.txt",)),
    ("10.1234/foo", ("10.1234/foo", None,)),
    ("10.1234/foo/bang/bar.txt", ("10.1234/foo/bang", "bar.txt",)),
)

@pytest.mark.parametrize("src,expected", split_cases)
def test_doi_fname_split(src, expected):
    res = zfile.split_doi_file(src)
    assert(res == expected)
