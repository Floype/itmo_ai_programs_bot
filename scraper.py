import re
import io
import json
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
import pdfplumber
import pandas as pd

from config import settings

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
}

def fetch_html(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def find_curriculum_link(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")
    # 1) Ищем кнопку/ссылку с текстом "Скачать учебный план"
    for a in soup.find_all("a"):
        text = (a.get_text(strip=True) or "").lower()
        if "скачать" in text and "учеб" in text:
            href = a.get("href")
            if href:
                return requests.compat.urljoin("https://abit.itmo.ru", href)
    # 2) fallback — любой pdf на странице
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if href.endswith(".pdf") or "uchebn" in href or "plan" in href:
            return requests.compat.urljoin("https://abit.itmo.ru", a["href"])
    return None

def extract_visible_text(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    for bad in soup(["script", "style", "nav", "header", "footer"]):
        bad.decompose()
    text = soup.get_text(" ", strip=True)
    chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s+|\n+", text) if len(c.strip()) > 20]
    norm = []
    for c in chunks:
        if len(c) > 500:
            for i in range(0, len(c), 400):
                norm.append(c[i:i+400])
        else:
            norm.append(c)
    return norm

def parse_pdf_curriculum(pdf_bytes: bytes) -> pd.DataFrame:
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            for t in tables or []:
                norm = [[(c or "").strip() for c in row] for row in t if any((c or "").strip() for c in row)]
                if not norm or len(norm[0]) < 2:
                    continue
                header = [h.lower() for h in norm[0]]
                colmap = {}
                for i, h in enumerate(header):
                    if any(k in h for k in ["дисцип", "модул", "наименование"]):
                        colmap["title"] = i
                    if "семестр" in h or "sem" in h:
                        colmap["semester"] = i
                    if "зе" in h or "зачет" in h or "кредит" in h:
                        colmap["credits"] = i
                    if "вид" in h or "тип" in h:
                        colmap["type"] = i
                for r in norm[1:]:
                    if "title" in colmap:
                        title = r[colmap["title"]].strip()
                        if not title or len(title) < 2:
                            continue
                        row = {
                            "title": title,
                            "semester": r[colmap["semester"]] if "semester" in colmap else "",
                            "credits": r[colmap["credits"]] if "credits" in colmap else "",
                            "type": r[colmap["type"]] if "type" in colmap else "",
                        }
                        rows.append(row)
    df = pd.DataFrame(rows).drop_duplicates()
    if "semester" in df:
        df["semester"] = df["semester"].astype(str).str.extract(r"(\d+)").fillna("")
    if "credits" in df:
        df["credits"] = df["credits"].astype(str).str.replace(",", ".", regex=False).str.extract(r"(\d+(?:\.\d+)?)")[0]
    return df

def download_file(url: str) -> bytes:
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.content

def collect_program(program_key: str, save_dir: Path) -> Dict:
    url = settings.program_urls[program_key]
    html = fetch_html(url)
    text_chunks = extract_visible_text(html)
    plan_url = find_curriculum_link(html)
    plan_df = pd.DataFrame()
    if plan_url:
        try:
            pdf_bytes = download_file(plan_url)
            plan_df = parse_pdf_curriculum(pdf_bytes)
        except Exception:
            pass

    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / f"{program_key}_page.txt").write_text("\n".join(text_chunks), encoding="utf-8")
    if not plan_df.empty:
        plan_df.to_csv(save_dir / f"{program_key}_plan.csv", index=False, encoding="utf-8-sig")

    return {
        "program": program_key,
        "text_chunks": text_chunks,
        "plan_path": str(save_dir / f"{program_key}_plan.csv") if not plan_df.empty else "",
    }

def collect_all() -> Dict[str, Dict]:
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(exist_ok=True, parents=True)
    result = {}
    for key in settings.program_urls.keys():
        result[key] = collect_program(key, data_dir / key)
    (data_dir / "index.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    collect_all()
