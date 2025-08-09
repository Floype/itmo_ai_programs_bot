from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings

class KnowledgeBase:
    def __init__(self):
        self.corpus: Dict[str, List[str]] = {}
        self.vectorizers: Dict[str, TfidfVectorizer] = {}
        self.matrices = {}
        self.plans: Dict[str, pd.DataFrame] = {}

    def load(self):
        data_dir = Path(settings.data_dir)
        meta = json.loads((data_dir / "index.json").read_text(encoding="utf-8"))
        for program, info in meta.items():
            texts = info.get("text_chunks") or []
            self.corpus[program] = texts
            if info.get("plan_path") and Path(info["plan_path"]).exists():
                self.plans[program] = pd.read_csv(info["plan_path"])
            else:
                self.plans[program] = pd.DataFrame(columns=["title", "semester", "credits", "type"])
            if texts:
                vec = TfidfVectorizer(min_df=1, max_df=0.9, ngram_range=(1,2))
                X = vec.fit_transform(texts)
                self.vectorizers[program] = vec
                self.matrices[program] = X

    def answer(self, program: str, question: str, top_k: int = 5) -> Tuple[str, List[str]]:
        """Возвращает краткий ответ и источники (топ-фрагменты)."""
        if program not in self.corpus or not self.corpus[program]:
            return "Пока нет данных для ответа. Попробуйте еще раз позже.", []
        vec = self.vectorizers[program]
        X = self.matrices[program]
        qv = vec.transform([question])
        sims = cosine_similarity(qv, X).ravel()
        idx = sims.argsort()[::-1][:top_k]
        top = [self.corpus[program][i] for i in idx if sims[i] > 0.08]
        if not top:
            return "Я отвечаю только по двум программам ИТМО (AI и AI Product). Уточните вопрос.", []
        answer = " ".join(top[:2])
        return answer, top

    def compare_programs(self) -> str:
        """Короткая справка по отличиям (по текстам страниц)."""
        return (
            "AI — более техническая программа (ML/DE/DS, вечерний формат, проекты индустрии). "
            "AI Product — сочетает техническую базу и продуктовый менеджмент, фокус на выводе ИИ-решений на рынок."
        )

    def plan_for(self, program: str) -> pd.DataFrame:
        return self.plans.get(program, pd.DataFrame())

kb = KnowledgeBase()
