from dataclasses import dataclass
from typing import List, Dict
import pandas as pd

KEYWORDS = {
    "ml": ["машинное обучение", "ml", "deep", "глубок", "нейрон", "cv", "nlp"],
    "data_eng": ["данн", "хранилищ", "etl", "pipelin", "spark", "инженер", "big data", "базы"],
    "analytics": ["аналит", "a/b", "метрик", "продуктов", "sql", "эксперимент", "визуал"],
    "product": ["продукт", "product", "менеджмент", "управлен", "маркет", "go-to-market", "unit"],
    "mlofs": ["mlops", "деплой", "prod", "kubernetes", "docker"],
    "prog": ["python", "программ", "алгоритм"],
    "ux": ["ux", "ui", "дизайн", "исследован", "hypothesis"],
}

@dataclass
class Background:
    goal: str
    python: str
    math: str
    work_load: str = "fulltime"

def pick_electives(plan: pd.DataFrame, bg: Background) -> List[Dict]:
    if plan is None or plan.empty:
        return []
    def has_any(title: str, kws: List[str]) -> bool:
        t = title.lower()
        return any(k in t for k in kws)

    recs = []
    for _, row in plan.iterrows():
        title = str(row.get("title", ""))
        typ = str(row.get("type", ""))
        sem = str(row.get("semester", ""))
        score = 0
        if bg.goal == "ml_engineer":
            if has_any(title, KEYWORDS["ml"] + KEYWORDS["mlofs"] + KEYWORDS["prog"]):
                score += 3
            if has_any(title, KEYWORDS["data_eng"]):
                score += 1
        elif bg.goal == "data_engineer":
            if has_any(title, KEYWORDS["data_eng"] + KEYWORDS["prog"]):
                score += 3
            if has_any(title, KEYWORDS["mlofs"]):
                score += 1
        elif bg.goal == "ai_product_manager":
            if has_any(title, KEYWORDS["product"] + KEYWORDS["analytics"] + KEYWORDS["ux"]):
                score += 3
            if has_any(title, KEYWORDS["ml"]):
                score += 1
        elif bg.goal == "analyst":
            if has_any(title, KEYWORDS["analytics"] + (["sql"] if "sql" in KEYWORDS else [])):
                score += 3
            if has_any(title, KEYWORDS["ml"]):
                score += 1
        if bg.python in ("none", "basic") and has_any(title, KEYWORDS["prog"]):
            score += 1
        if bg.math == "weak" and ("вероятност" in title.lower() or "математ" in title.lower()):
            score += 1
        if "элек" in typ.lower() or "выбор" in typ.lower():
            score += 1
        if score >= 3:
            recs.append({
                "title": title,
                "semester": sem,
                "type": typ,
                "score": score
            })
    recs.sort(key=lambda x: (int(x["semester"]) if str(x["semester"]).isdigit() else 99, -x["score"], x["title"]))
    return recs[:10]
