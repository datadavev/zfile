# zfile

A simple resolver and partial proxy service for published content on Zenodo.

zfile is a tiny FastAPI service that may help streamline access to published resources on Zenodo.

## Operation

zfile may be run locally. To do so, clone this repo, then:
```
cd zfile
poetry run python -m zfile
```

The service may then be accessed at http://localhost:4000/

zfile is also deployed on a very resource limited service at: https://z.rslv.xyz

## Usage

Call the service using the service end point URL using a pattern like:

```
/DO[/FNAME]

DOI = The published DOI without embellishments, e.g. "10.5281/zenodo.11400483".
FNAME = The name of a file within the package.
```

Given the DOI for a package, the service returns the package metadata from the Zenodo API.

Example:

```
curl
```

If the DOI and the name of a file within the package is given, the service will either redirect to the content URL on Zenodo, or for some specific media_types, will proxy the content.

Example: