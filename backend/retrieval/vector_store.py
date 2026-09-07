# © 2026 BUPT_Mint-Green
# All rights reserved.

import importlib
from typing import Optional

from backend.config import CHROMA_DIR, EMBEDDING_MODEL, VECTOR_RAG_ENABLED
from backend.data_loader import normalize_poem
from backend.retrieval.hybrid_retriever import infer_form

class VectorPoetryStore:
    def __init__(self):
        self.available = False
        self.reason = "向量检索未初始化"
        self.client = None
        self.embedding = None
        if not VECTOR_RAG_ENABLED:
            self.reason = "配置已关闭向量检索"
            return
        try:
            chromadb = importlib.import_module("chromadb")
            sentence_transformers = importlib.import_module("sentence_transformers")
            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            self.embedding = sentence_transformers.SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
            self.available = True
            self.reason = "ready"
        except Exception as error:
            self.reason = str(error)

    def _collection(self, name: str):
        return self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

    def count(self, name: str) -> int:
        if not self.available:
            return 0
        try:
            return self._collection(name).count()
        except Exception:
            return 0

    def build(self, name: str, records: list[dict], batch_size: int = 256) -> int:
        if not self.available:
            raise RuntimeError(self.reason)
        collection = self._collection(name)
        if collection.count() >= len(records):
            return collection.count()
        for start in range(0, len(records), batch_size):
            batch = records[start:start + batch_size]
            documents = [self.document(record) for record in batch]
            embeddings = self.embedding.encode(documents, normalize_embeddings=True).tolist()
            ids = [f"{name}-{start + index}" for index in range(len(batch))]
            metadata = [self.metadata(record, name) for record in batch]
            collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadata)
        return collection.count()

    @staticmethod
    def document(record: dict) -> str:
        return " ".join(str(record.get(key, "")) for key in ("title", "author", "poet", "dynasty", "keywords")) + " " + normalize_poem(record)

    @staticmethod
    def metadata(record: dict, source: str) -> dict:
        result = {
            "source": source,
            "title": str(record.get("title", "无题")),
            "author": str(record.get("author") or record.get("poet", "佚名")),
            "dynasty": str(record.get("dynasty", "")),
            "form": infer_form(record),
            "poem": normalize_poem(record),
        }
        sentiment = record.get("setiments") or record.get("sentiments") or {}
        if sentiment:
            result["emotion"] = str(sentiment.get("holistic", "3"))
        if "overall score" in record:
            result["overall"] = float(record["overall score"])
        return result

    def search(self, name: str, query: str, top_k: int, filters: Optional[dict] = None) -> list[dict]:
        if not self.available or self.count(name) == 0 or not query.strip():
            return []
        try:
            embedding = self.embedding.encode([query], normalize_embeddings=True).tolist()
            result = self._collection(name).query(query_embeddings=embedding, n_results=top_k, where=filters or None)
            items = []
            for document, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
                items.append({**metadata, "content": metadata.get("poem", document), "vector_score": round(1 - distance, 4), "retrieval_mode": "vector"})
            return items
        except Exception as error:
            self.available = False
            self.reason = f"向量检索已降级：{error}"
            return []

    def status(self) -> dict:
        return {"available": self.available, "reason": self.reason, "collections": {name: self.count(name) for name in ("poetry", "ccpc", "fspc", "pqed")}}
