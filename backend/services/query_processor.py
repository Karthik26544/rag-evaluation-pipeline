import google.generativeai as genai
import os
import time
from typing import List, Dict, Tuple
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

class QueryProcessor:

    def __init__(self):
        self.model = genai.GenerativeModel("gemini-flash-latest")

    def rewrite_query(self, original_query: str) -> str:
        prompt = f"""
        Rewrite the following user question to be more specific 
        and searchable for semantic search in a document database.
        Return ONLY the rewritten question, nothing else.

        Original question: {original_query}

        Rewritten question:
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Query rewrite failed: {e}")
            return original_query

    def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict],
        original_question: str = None
    ) -> Tuple[str, float, int]:

        context = "\n\n---\n\n".join([
            f"Source {i+1}:\n{chunk['content']}"
            for i, chunk in enumerate(context_chunks)
        ])

        prompt = f"""
        You are a helpful assistant. Answer the question based 
        ONLY on the provided context below.
        
        If the answer is not in the context, say exactly:
        "I could not find this information in the provided documents."

        Context:
        {context}

        Question: {question}

        Instructions:
        - Answer clearly and concisely
        - Mention which Source number you used
        - Do not make up any information

        Answer:
        """

        try:
            start_time = time.time()
            response = self.model.generate_content(prompt)
            latency = int((time.time() - start_time) * 1000)
            answer = response.text.strip()
            confidence = self._calculate_confidence(answer, context_chunks)
            return answer, confidence, latency

        except Exception as e:
            error_str = str(e)
            print(f"Answer generation failed: {error_str}")
            
            if "429" in error_str or "quota" in error_str.lower():
                return (
                    "Rate limit reached. The free Gemini API allows limited requests per minute. Please wait 60 seconds and try again.",
                    0.0,
                    0
                )
            elif "404" in error_str:
                return (
                    "The AI model is temporarily unavailable. Please try again later.",
                    0.0,
                    0
                )
            else:
                return (
                    "Failed to generate answer. Please try again.",
                    0.0,
                    0
                )

    def _calculate_confidence(
        self,
        answer: str,
        chunks: List[Dict]
    ) -> float:
        if "could not find" in answer.lower() or "rate limit" in answer.lower():
            return 0.2
        if len(chunks) == 0:
            return 0.1

        avg_score = sum(
            c.get("score", c.get("final_score", 0.5))
            for c in chunks
        ) / len(chunks)

        confidence = min(0.95, avg_score * 1.2)
        return round(confidence, 2)