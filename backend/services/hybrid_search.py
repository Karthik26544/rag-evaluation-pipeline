from rank_bm25 import BM25Okapi
from typing import List, Dict, Any
import re

class HybridSearch:

    def __init__(self):
        self.corpus = []
        self.bm25 = None

    def build_index(self, chunks: List[Dict]):
        self.corpus = chunks
        tokenized = [self._tokenize(chunk["content"]) for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized)

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()

    def search(self, query: str, top_k: int = 20) -> List[Dict]:
        if not self.bm25:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    **self.corpus[idx],
                    "bm25_score": scores[idx]
                })

        return results

    def hybrid_search(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        alpha: float = 0.7
    ) -> List[Dict]:
        combined = {}

        max_vec = max(
            [r["score"] for r in vector_results], default=1
        )
        for result in vector_results:
            key = result["content"][:100]
            combined[key] = {
                **result,
                "vector_score": result["score"] / max_vec,
                "bm25_score": 0,
                "final_score": 0
            }

        max_bm25 = max(
            [r["bm25_score"] for r in bm25_results], default=1
        )
        for result in bm25_results:
            key = result["content"][:100]
            if key in combined:
                combined[key]["bm25_score"] = (
                    result["bm25_score"] / max_bm25
                )
            else:
                combined[key] = {
                    **result,
                    "vector_score": 0,
                    "bm25_score": result["bm25_score"] / max_bm25,
                    "final_score": 0
                }

        for key in combined:
            v = combined[key]["vector_score"]
            b = combined[key]["bm25_score"]
            combined[key]["final_score"] = alpha * v + (1 - alpha) * b

        sorted_results = sorted(
            combined.values(),
            key=lambda x: x["final_score"],
            reverse=True
        )

        return sorted_results[:5]