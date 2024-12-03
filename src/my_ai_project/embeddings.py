import os
import json
import hashlib
from typing import Dict, List, Optional
from pathlib import Path
import aiohttp
import numpy as np
from datetime import datetime

class EmbeddingsManager:
    def __init__(self, storage_dir: str = "embeddings"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self._cache = {}

    def _get_bill_hash(self, bill_text: str) -> str:
        """Generate a unique hash for bill content"""
        return hashlib.sha256(bill_text.encode()).hexdigest()[:16]

    def _get_embedding_path(self, bill_hash: str) -> Path:
        """Get path to embedding file"""
        return self.storage_dir / f"{bill_hash}.json"

    async def get_embeddings(self, text: str, chunk_size: int = 6000) -> List[List[float]]:
        """Get embeddings for text chunks, using cache if available"""
        bill_hash = self._get_bill_hash(text)
        
        # Check memory cache first
        if bill_hash in self._cache:
            return self._cache[bill_hash]["embeddings"]
        
        # Check file cache
        embedding_path = self._get_embedding_path(bill_hash)
        if embedding_path.exists():
            with open(embedding_path) as f:
                data = json.load(f)
                self._cache[bill_hash] = data
                return data["embeddings"]
        
        # Generate new embeddings
        chunks = self._split_text(text, chunk_size)
        embeddings = await self._generate_embeddings(chunks)
        
        # Store embeddings
        data = {
            "bill_hash": bill_hash,
            "embeddings": embeddings,
            "chunk_size": chunk_size,
            "created_at": datetime.utcnow().isoformat(),
            "model": "text-embedding-ada-002"
        }
        
        with open(embedding_path, "w") as f:
            json.dump(data, f)
        
        self._cache[bill_hash] = data
        return embeddings

    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks of roughly equal token size"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) // 4  # Rough token estimate
            if current_size + word_size > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_size = 0
            current_chunk.append(word)
            current_size += word_size
            
        if current_chunk:
            chunks.append(" ".join(current_chunk))
            
        return chunks

    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            embeddings = []
            for text in texts:
                async with session.post(
                    "https://api.openai.com/v1/embeddings",
                    headers=headers,
                    json={
                        "input": text,
                        "model": "text-embedding-ada-002"
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        embeddings.append(data["data"][0]["embedding"])
                    else:
                        raise Exception(f"Failed to generate embedding: {await response.text()}")
            
            return embeddings

    def find_similar_sections(
        self,
        query_embedding: List[float],
        bill_hash: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """Find most similar sections using cosine similarity"""
        if bill_hash and bill_hash not in self._cache:
            embedding_path = self._get_embedding_path(bill_hash)
            if embedding_path.exists():
                with open(embedding_path) as f:
                    self._cache[bill_hash] = json.load(f)
        
        results = []
        query_embedding = np.array(query_embedding)
        
        for cached_hash, data in self._cache.items():
            if bill_hash and cached_hash != bill_hash:
                continue
                
            for i, embedding in enumerate(data["embeddings"]):
                similarity = np.dot(query_embedding, embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                )
                results.append({
                    "bill_hash": cached_hash,
                    "chunk_index": i,
                    "similarity": float(similarity)
                })
        
        return sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k] 