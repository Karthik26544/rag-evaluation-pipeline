import os
from typing import List, Dict, Any
import pypdf
from docx import Document as DocxDocument
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter
)

class DocumentProcessor:

    def extract_text(self, file_path: str, file_type: str) -> str:
        if file_type == "pdf":
            return self._extract_pdf(file_path)
        elif file_type == "docx":
            return self._extract_docx(file_path)
        elif file_type in ["txt", "md"]:
            return self._extract_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _extract_pdf(self, file_path: str) -> str:
        text = ""
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _extract_docx(self, file_path: str) -> str:
        doc = DocxDocument(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    def _extract_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def chunk_text(self, text: str, strategy: str = "recursive") -> List[Dict[str, Any]]:
        if strategy == "fixed":
            return self._fixed_chunking(text)
        elif strategy == "recursive":
            return self._recursive_chunking(text)
        elif strategy == "sentence":
            return self._sentence_chunking(text)
        else:
            return self._recursive_chunking(text)

    def _fixed_chunking(self, text: str) -> List[Dict[str, Any]]:
        splitter = CharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separator="\n"
        )
        chunks = splitter.split_text(text)
        return [
            {
                "content": chunk,
                "index": i,
                "strategy": "fixed",
                "size": len(chunk)
            }
            for i, chunk in enumerate(chunks)
        ]

    def _recursive_chunking(self, text: str) -> List[Dict[str, Any]]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = splitter.split_text(text)
        return [
            {
                "content": chunk,
                "index": i,
                "strategy": "recursive",
                "size": len(chunk)
            }
            for i, chunk in enumerate(chunks)
        ]

    def _sentence_chunking(self, text: str) -> List[Dict[str, Any]]:
        sentences = text.replace("\n", " ").split(". ")
        chunks = []
        current_chunk = ""
        index = 0

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < 600:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "index": index,
                        "strategy": "sentence",
                        "size": len(current_chunk)
                    })
                    index += 1
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "index": index,
                "strategy": "sentence",
                "size": len(current_chunk)
            })

        return chunks