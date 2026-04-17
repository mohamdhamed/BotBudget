"""Public landing page — no authentication required."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

# 1 hour browser cache, 1 day CDN (Cloudflare) cache
_CACHE_HEADERS = {
    "Cache-Control": "public, max-age=3600, s-maxage=86400",
}


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return request.app.state.templates.TemplateResponse(
        request, "landing.html", {}, headers=_CACHE_HEADERS,
    )


@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return request.app.state.templates.TemplateResponse(
        request, "privacy.html", {}, headers=_CACHE_HEADERS,
    )


@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return request.app.state.templates.TemplateResponse(
        request, "terms.html", {}, headers=_CACHE_HEADERS,
    )
