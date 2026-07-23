import cohere
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


class Reranker:
    
    def __init__(self):
        self.api_key = os.getenv("COHERE_API_KEY")
        if self.api_key:
            self.client = cohere.Client(self.api_key)
            self.enabled = True
            print("Reranker enabled (Cohere)")
        else:
            self.client = None
            self.enabled = False
            print("Reranker disabled (no COHERE_API_KEY)")
    
    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Rerank retrieved documents using Cohere.
        
        Input: 20 chunks from vector/hybrid search
        Output: Top 5 chunks after reranking
        """
        
        if not self.enabled or not documents:
            return documents[:top_k]
        
        try:
            texts = [doc["content"] for doc in documents]
            
            response = self.client.rerank(
                query=query,
                documents=texts,
                top_n=min(top_k, len(texts)),
                model="rerank-english-v3.0"
            )
            
            reranked = []
            for result in response.results:
                original_doc = documents[result.index]
                reranked.append({
                    **original_doc,
                    "rerank_score": result.relevance_score,
                    "original_score": original_doc.get("score", original_doc.get("final_score", 0))
                })
            
            return reranked
        
        except Exception as e:
            print(f"Reranking failed: {e}")
            return documents[:top_k]