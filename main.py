import asyncio, json
from typing import List, Optional
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    JsonCssExtractionStrategy,
)
import pandas as pd

app = FastAPI(title="Stock Crawler API - Batch Version")

# --- BrowserConfig
browser_cfg = BrowserConfig(
    headless=True,
    java_script_enabled=True,
    viewport_width=1400,
    viewport_height=1000,
)

# --- Schema extraction
schema = {
    "name": "cafef_stock_daily",
    "baseSelector": "#owner-contents-table tbody tr",
    "fields": [
        {"name": "date", "selector": "td.owner_time", "type": "text"},
        {"name": "close", "selector": "td.owner_priceClose", "type": "text"},
        {"name": "volume", "selector": "td.owner_gd_td", "type": "text"},
    ],
}

extractor = JsonCssExtractionStrategy(schema)

# --- CrawlerRunConfig
run_cfg = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    extraction_strategy=extractor,
    wait_for="css:#owner-contents-table tbody tr",
    wait_until="networkidle",
    page_timeout=90000,
)


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
    df["volume"] = (
        df["volume"]
        .str.replace(",", "", regex=False)
        .str.strip()
        .astype("float64", errors="ignore")
    )
    df = df.sort_values("date", ascending=False).reset_index(drop=True)

    if len(df) > 14:
        avg14 = df.loc[1:14, "volume"].mean()
    else:
        avg14 = df.loc[1:, "volume"].mean()

    df["Khối lượng TB 14 ngày"] = None
    if pd.notna(avg14):
        df.at[0, "Khối lượng TB 14 ngày"] = f"{int(round(avg14)):,}".replace(",", ".")

    return df


async def crawl_symbols(symbols: List[str]):
    all_rows = []
    async with AsyncWebCrawler(config=browser_cfg, verbose=True) as crawler:
        for sym in symbols:
            url = f"https://cafef.vn/du-lieu/lich-su-giao-dich-{sym.lower()}-1.chn"
            result = await crawler.arun(url=url, config=run_cfg)
            raw = result.extracted_content or "[]"
            data = json.loads(raw)

            if data:
                df = pd.DataFrame(data)
                df.insert(0, "symbol", sym)
                df = process_dataframe(df)
                current_row = df.iloc[0].fillna("").astype(str).to_dict()
                all_rows.append(current_row)
    return all_rows


# --- Pydantic model cho POST body
class SymbolsBody(BaseModel):
    symbols: List[str]


# --- GET endpoint
@app.get("/crawl_batch")
async def crawl_batch_get(symbols: List[str] = Query(..., description="Danh sách mã CK")):
    rows = await crawl_symbols(symbols)
    return {"data": rows, "count": len(rows)}


# --- POST endpoint
@app.post("/crawl_batch")
async def crawl_batch_post(body: SymbolsBody = Body(...)):
    rows = await crawl_symbols(body.symbols)
    return {"data": rows, "count": len(rows)}
