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
    ext = os.path.splitext(fname)[1]
    try:
        return MEDIA_TYPES[ext]
    except KeyError:
        return None


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
async def get_favicon():
    raise fastapi.HTTPException(status_code=404, detail="Not found")


@app.get("/", include_in_schema=False)
def get_home():
    logging.info("get /")
    return starlette.responses.FileResponse(
        os.path.join(BASE_FOLDER, "static/index.html")
    )


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
    try:
        if fname is None:
        # return the Zenodo package JSON
            return zfile.getZenodoPackageMetadata(doi)
        url = zfile.getZenodoContentUrl(doi, fname)
    except ValueError:
        return {"error": f"No link headers returned for DOI {doi}"}
    media_type = media_type_from_name(fname)
    if media_type is not None:
        fname_encoded = urllib.parse.quote(fname)
        url = url.replace(fname, fname_encoded)
        L.info("Proxying html for URL: %s", url)
        return fastapi.responses.StreamingResponse(_streamer(url), media_type=media_type)
    return fastapi.responses.RedirectResponse(url)
