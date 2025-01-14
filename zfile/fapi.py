"""
Implements a simple proxy for accessing Zenodo resources using DOI/filename.
"""
import logging
import os
import typing
import urllib.parse

import fastapi
import fastapi.middleware.cors
import fastapi.staticfiles
import fastapi.responses
import httpx
import starlette.responses
import starlette.background
import zfile

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

MEDIA_TYPES = {
    "html": "text/html",
    "htm": "text/html",
    "css": "text/css",
    "js": "text/javascript",
}
app = fastapi.FastAPI(
    title="ZFile",
    description = __doc__,
    verson=zfile.__version__,
    contact={"name": "Dave Vieglais", "url": "https://github.com/datadavev/"},
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/license/mit/",
        },
        openapi_url="/api/v1/openapi.json",
        docs_url="/api",
    )

client = httpx.AsyncClient()

app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=True,
    allow_methods=[
        "GET",
    ],
    allow_headers=[
        "*",
    ],
)

app.mount(
    "/static",
    fastapi.staticfiles.StaticFiles(directory=os.path.join(BASE_FOLDER, "static")),
    name="static",
)


def media_type_from_name(fname: str) -> typing.Optional[str]:
    parts = fname.rsplit(".")
    if len(parts) < 2:
        return None
    try:
        return MEDIA_TYPES[parts[1]]
    except KeyError:
        return None


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
async def get_favicon():
    raise fastapi.HTTPException(status_code=404, detail="Not found")


@app.get("/", include_in_schema=False)
async def get_home():
    logging.info("get /")
    return starlette.responses.FileResponse(
        os.path.join(BASE_FOLDER, "static/index.html")
    )


@app.get(
    "/.info/{target:path}",
    summary="Retrieve metadata about the given DOI/filename."
)
async def get_zenodo_target_info(target: str):
    target = target.strip("/")
    if target is None or len(target) < 7:
        return get_home()
    doi, fname = zfile.split_doi_file(target)
    try:
        linkset = zfile.getZenodoPackageMetadata(doi)
        if fname is None:
        # return the Zenodo package JSON
            return linkset
        files = zfile.getZenodoFileList(linkset)
    except ValueError:
        return {"error": f"No link headers returned for DOI {doi}"}
    for f in files:
        if f.key == fname:
            return f
    linkset_url = linkset.get("links",{}).get("self", "")
    return {"error": f"File {fname} not found in linkset {doi} at {linkset_url}"}


@app.get(
    "/{target:path}",
    summary="Retrieve file given DOI/filename."
)
async def get_zenodo_target(request: fastapi.Request, target: typing.Optional[str]):

    def _streamer(_url):
        with httpx.stream("GET", _url) as r:
            for chunk in r.iter_bytes():
                yield chunk

    L = logging.getLogger("zfile.debug")
    target = target.strip("/")
    if target is None or len(target) < 7:
        return get_home()
    doi, fname = zfile.split_doi_file(target)
    L.info("DOI: %s fname:%s", doi, fname)
    # resolve the doi to get the linkset
    try:
        linkset = zfile.getZenodoPackageMetadata(doi)
        if fname is None:
        # return the Zenodo package JSON
            return linkset
        # Get the list of files in the linkset
        files = zfile.getZenodoFileList(linkset)
    except ValueError:
        return {"error": f"No link headers returned for DOI {doi}"}
    except Exception as e:
        return {"error": str(e)}
    # Find an entry in the files list matching the provided file name
    for f in files:
        if f.key == fname:
            media_type = media_type_from_name(fname)
            url = f.content
            # Is this a media type to show in the browser?
            if media_type is not None:
                # Proxy the content and set the appropriate content-type
                fname_encoded = urllib.parse.quote(fname)
                url = url.replace(fname, fname_encoded)
                L.info("Proxying html for URL: %s", url)
                return fastapi.responses.StreamingResponse(_streamer(url), media_type=media_type)
            # otherwise, redirect to the content location
            return fastapi.responses.RedirectResponse(url)
    # Fallback, return an error message
    linkset_url = linkset.get("links",{}).get("self", "")
    return {"error": f"File {fname} not found in linkset {doi} at {linkset_url}"}


if __name__ == "__main__":
    # This is used when debugging the app
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=4000)
