from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
import os
from dotenv import load_dotenv
from ..dependencies import get_current_user_id

load_dotenv()

router = APIRouter(prefix="/api/books", tags=["books"])

GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")


@router.get("/search")
async def search_google_books(
    q: str = Query(..., description="検索キーワード"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Google Books API から本を検索する。
    認証済みユーザーのみ利用可能。
    """
    params = {"q": q, "maxResults": 10}
    if GOOGLE_BOOKS_API_KEY:
        params["key"] = GOOGLE_BOOKS_API_KEY

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(GOOGLE_BOOKS_API_URL, params=params)
            response.raise_for_status()
            items = response.json().get("items", [])

            # フロントで使いやすい形に整形して返す
            results = []
            for item in items:
                info = item.get("volumeInfo", {})
                image_links = info.get("imageLinks", {})
                results.append({
                    "api_id": item.get("id"),
                    "api_etag": item.get("etag"),
                    "self_link": item.get("selfLink"),
                    "title": info.get("title"),
                    "author": ", ".join(info.get("authors", [])),
                    "publisher": info.get("publisher"),
                    "published_date": info.get("publishedDate"),
                    "description": info.get("description"),
                    "total_pages": info.get("pageCount"),
                    "small_cover_url": image_links.get("smallThumbnail"),
                    "cover_url": image_links.get("thumbnail"),
                })
            return results

        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail="Google Books API連携エラー"
            )
        except Exception:
            raise HTTPException(status_code=500, detail="通信失敗")