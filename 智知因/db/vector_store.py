"""
智知因 - ChromaDB 向量数据库管理
RAG 知识库核心组件
"""
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
from loguru import logger

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings


class VectorStore:
    """ChromaDB 向量存储管理器"""

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_dir = persist_directory or str(settings.CHROMA_PERSIST_DIR)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        self.collection = None
        self._init_collection()

    def _init_collection(self):
        """初始化集合"""
        try:
            self.collection = self.client.get_or_create_collection(
                name="course_knowledge_base",
                metadata={"description": "课程知识库 RAG 索引"}
            )
            logger.info(f"向量数据库初始化完成，集合包含 {self.collection.count()} 条文档")
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {e}")
            raise

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ):
        """添加文档到知识库"""
        if not documents:
            return

        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"成功添加 {len(documents)} 条文档到知识库")
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None
    ) -> List[Dict]:
        """相似性搜索"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k,
                where=where,
                where_document=where_document,
                include=["documents", "metadatas", "distances"]
            )

            # 格式化结果
            formatted = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                        "id": results["ids"][0][i] if results["ids"] else None,
                    })

            return formatted
        except Exception as e:
            logger.error(f"相似性搜索失败: {e}")
            return []

    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        """根据 ID 获取文档"""
        try:
            result = self.collection.get(ids=[doc_id], include=["documents", "metadatas"])
            if result["documents"]:
                return {
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                    "id": doc_id,
                }
            return None
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
            return None

    def delete(self, ids: List[str]):
        """删除文档"""
        try:
            self.collection.delete(ids=ids)
            logger.info(f"删除 {len(ids)} 条文档")
        except Exception as e:
            logger.error(f"删除文档失败: {e}")

    def reset(self):
        """重置知识库"""
        try:
            self.client.delete_collection("course_knowledge_base")
            self._init_collection()
            logger.warning("知识库已重置")
        except Exception as e:
            logger.error(f"重置知识库失败: {e}")


class RAGRetriever:
    """RAG 检索器 - 与 LangChain 集成"""

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()
        self._chain = None

    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """异步相似性搜索"""
        return self.vector_store.similarity_search(
            query=query,
            k=k,
            where=filter_metadata
        )

    def add_pdf_knowledge(self, pdf_path: str, chunk_size: int = 500):
        """从 PDF 添加知识"""
        try:
            import PyPDF2
            from langchain.text_splitter import RecursiveCharacterTextSplitter

            # 读取 PDF
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"

            # 分块
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            chunks = splitter.split_text(text)

            # 添加到向量库
            documents = []
            metadatas = []
            ids = []

            filename = Path(pdf_path).stem
            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                metadatas.append({
                    "source": filename,
                    "chunk_id": i,
                    "type": "pdf_content"
                })
                ids.append(f"{filename}_chunk_{i}")

            self.vector_store.add_documents(documents, metadatas, ids)
            logger.info(f"从 {pdf_path} 添加了 {len(chunks)} 个知识块")

        except Exception as e:
            logger.error(f"添加 PDF 知识失败: {e}")
            raise

    def add_text_knowledge(self, text: str, source: str, metadata: Optional[Dict] = None):
        """添加文本知识"""
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter

            # 分块
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            chunks = splitter.split_text(text)

            documents = []
            metadatas = []
            ids = []

            base_metadata = {"source": source, "type": "text_content"}
            if metadata:
                base_metadata.update(metadata)

            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                chunk_meta = base_metadata.copy()
                chunk_meta["chunk_id"] = i
                metadatas.append(chunk_meta)
                ids.append(f"{source}_chunk_{i}")

            self.vector_store.add_documents(documents, metadatas, ids)
            logger.info(f"添加了 {len(chunks)} 个文本知识块")

        except Exception as e:
            logger.error(f"添加文本知识失败: {e}")
            raise


# 全局向量库实例
_vector_store: Optional[VectorStore] = None
_rag_retriever: Optional[RAGRetriever] = None


def get_vector_store() -> VectorStore:
    """获取向量存储单例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_rag_retriever() -> RAGRetriever:
    """获取 RAG 检索器单例"""
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever(get_vector_store())
    return _rag_retriever
