"""HTTP fetching with redirect-chain detection and size limits."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    redirect_chain: list[str] = field(default_factory=list)
    headers: dict = field(default_factory=dict)
    body: str = ""
    content_type: str = ""
    error: str | None = None


async def fetch(client: httpx.AsyncClient, url: str, max_size: int = 2_000_000) -> FetchResult:
    chain: list[str] = []
    final_url = url
    try:
        resp = await client.get(
            url,
            follow_redirects=True,
            timeout=client.timeout,
        )
        final_url = str(resp.url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        body = resp.text[:max_size]
        return FetchResult(
            url=url,
            final_url=final_url,
            status_code=resp.status_code,
            redirect_chain=extract_redirect_chain(resp.history),
            headers=dict(resp.headers),
            body=body,
            content_type=content_type,
        )
    except httpx.HTTPStatusError as exc:
        return FetchResult(
            url=url,
            final_url=final_url,
            status_code=exc.response.status_code if exc.response is not None else 0,
            redirect_chain=chain,
            headers=dict(exc.response.headers) if exc.response is not None else {},
            body="",
            content_type=exc.response.headers.get("content-type", "") if exc.response is not None else "",
            error=f"HTTP {exc.response.status_code if exc.response is not None else '?'}",
        )
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as exc:
        return FetchResult(url=url, final_url=final_url, status_code=0, error=str(exc))


def extract_redirect_chain(history: list[httpx.Response]) -> list[str]:
    chain: list[str] = []
    for resp in history:
        location = resp.headers.get("location", "")
        chain.append(f"{resp.status_code} -> {location}")
    return chain
