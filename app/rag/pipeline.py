"""
智知因 - RAG Pipeline
完整的检索增强生成流程：PDF解析 -> 文本分割 -> Embedding -> 向量存储 -> 检索
"""
import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass
from loguru import logger

from app.config import settings


@dataclass
class Document:
    """文档对象"""
    id: str
    content: str
    metadata: Dict

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(self.content.encode()).hexdigest()


@dataclass
class Chunk:
    """文档块对象"""
    id: str
    content: str
    metadata: Dict
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """检索结果"""
    content: str
    metadata: Dict
    score: float
    distance: float


class TextSplitter:
    """文本分割器"""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", ". ", " "]

    def split_text(self, text: str) -> List[str]:
        """分割文本"""
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            if end >= len(text):
                chunks.append(text[start:])
                break

            # 寻找最佳分割点
            split_pos = -1
            for sep in self.separators:
                pos = text.rfind(sep, start + self.chunk_size // 2, end)
                if pos != -1:
                    split_pos = pos + len(sep)
                    break

            if split_pos == -1:
                split_pos = end

            chunks.append(text[start:split_pos])
            start = split_pos - self.chunk_overlap
            if start < 0:
                start = 0

        return chunks

    def split_documents(self, documents: List[Document]) -> List[Chunk]:
        """分割文档为块"""
        chunks = []

        for doc in documents:
            texts = self.split_text(doc.content)

            for i, text in enumerate(texts):
                if text.strip():
                    chunk_id = f"{doc.id}_chunk_{i}"
                    chunk = Chunk(
                        id=chunk_id,
                        content=text,
                        metadata={
                            **doc.metadata,
                            "chunk_index": i,
                            "total_chunks": len(texts)
                        }
                    )
                    chunks.append(chunk)

        return chunks


class EmbeddingService:
    """Embedding服务 - 支持多种后端"""

    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self._client = None
        self._init_client()

    def _init_client(self):
        """初始化Embedding客户端"""
        if self.provider == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self._client = OpenAIEmbeddings(
                        model="text-embedding-ada-002",
                        api_key=api_key
                    )
                    logger.info("OpenAI Embedding客户端初始化成功")
            except ImportError:
                logger.warning("OpenAI Embedding不可用")

        elif self.provider == "huggingface":
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                self._client = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                logger.info("HuggingFace Embedding客户端初始化成功")
            except ImportError:
                logger.warning("HuggingFace Embedding不可用")

        elif self.provider == "dashscope":
            try:
                import dashscope
                from langchain_community.embeddings import DashScopeEmbeddings
                api_key = os.getenv("QWEN_API_KEY")
                if api_key:
                    dashscope.api_key = api_key
                    self._client = DashScopeEmbeddings(
                        model="text-embedding-v1",
                        dashscope_api_key=api_key
                    )
                    logger.info("DashScope Embedding客户端初始化成功")
            except ImportError:
                logger.warning("DashScope Embedding不可用")

        # 默认使用HuggingFace
        if self._client is None:
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                self._client = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                logger.info("使用HuggingFace作为默认Embedding后端")
            except Exception as e:
                logger.error(f"Embedding客户端初始化失败: {e}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本的embedding"""
        if not self._client:
            # 返回随机向量作为降级方案
            import random
            dim = 384
            return [[random.random() for _ in range(dim)] for _ in texts]

        try:
            return self._client.embed_documents(texts)
        except Exception as e:
            logger.error(f"Embedding失败: {e}")
            # 返回随机向量作为降级方案
            import random
            dim = 384
            return [[random.random() for _ in range(dim)] for _ in texts]

    def embed_query(self, query: str) -> List[float]:
        """获取查询的embedding"""
        if not self._client:
            import random
            dim = 384
            return [random.random() for _ in range(dim)]

        try:
            return self._client.embed_query(query)
        except Exception as e:
            logger.error(f"Query embedding失败: {e}")
            import random
            dim = 384
            return [random.random() for _ in range(dim)]


class PDFProcessor:
    """PDF文档处理器"""

    def __init__(self):
        self.supported_formats = ['.pdf', '.txt', '.md', '.markdown']

    def can_process(self, file_path: str) -> bool:
        """检查是否支持处理该文件"""
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_formats

    def process_pdf(self, file_path: str, course: str, chapter: int) -> List[Document]:
        """处理PDF文件"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = Path(file_path).suffix.lower()

        if ext == '.pdf':
            return self._process_pdf_file(file_path, course, chapter)
        elif ext in ['.txt', '.md', '.markdown']:
            return self._process_text_file(file_path, course, chapter)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _process_pdf_file(self, file_path: str, course: str, chapter: int) -> List[Document]:
        """处理PDF文件"""
        documents = []

        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()

                if text and text.strip():
                    doc = Document(
                        id=f"{course}_ch{chapter}_p{page_num}",
                        content=text,
                        metadata={
                            "course": course,
                            "chapter": chapter,
                            "source": Path(file_path).name,
                            "type": "pdf",
                            "page": page_num + 1,
                            "total_pages": len(reader.pages)
                        }
                    )
                    documents.append(doc)

            logger.info(f"PDF处理完成: {file_path}, {len(documents)}页")

        except ImportError:
            logger.error("请安装pypdf: pip install pypdf")
            raise
        except Exception as e:
            logger.error(f"PDF处理失败: {e}")
            raise

        return documents

    def _process_text_file(self, file_path: str, course: str, chapter: int) -> List[Document]:
        """处理文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        doc = Document(
            id=f"{course}_ch{chapter}_text",
            content=content,
            metadata={
                "course": course,
                "chapter": chapter,
                "source": Path(file_path).name,
                "type": "text"
            }
        )

        return [doc]


class RAGPipeline:
    """完整的RAG流程管道"""

    def __init__(self):
        self.text_splitter = TextSplitter(
            chunk_size=settings.RAG_CHUNK_SIZE if hasattr(settings, 'RAG_CHUNK_SIZE') else 500,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP if hasattr(settings, 'RAG_CHUNK_OVERLAP') else 50
        )
        self.embedding_service = EmbeddingService()
        self.pdf_processor = PDFProcessor()
        self._db_manager = None

    @property
    def db_manager(self):
        """延迟导入db_manager"""
        if self._db_manager is None:
            from app.db.database import db_manager
            self._db_manager = db_manager
        return self._db_manager

    def process_and_store(
        self,
        file_path: str,
        course: str,
        chapter: int,
        source: str = "教材",
        doc_type: str = "concept",
        importance: str = "核心"
    ) -> Dict:
        """处理文档并存储到向量库"""
        # 处理文档
        documents = self.pdf_processor.process_pdf(file_path, course, chapter)

        # 分割文本
        chunks = self.text_splitter.split_documents(documents)

        # 获取embedding并存储
        if chunks:
            texts = [c.content for c in chunks]
            embeddings = self.embedding_service.embed_texts(texts)

            # 存储到ChromaDB
            for i, chunk in enumerate(chunks):
                if i < len(embeddings):
                    chunk.embedding = embeddings[i]

            # 添加到向量库
            result = self._add_to_vector_store(chunks, course, chapter, source, doc_type, importance)

            return {
                "status": "success",
                "documents": len(documents),
                "chunks": len(chunks),
                "message": f"成功处理{len(chunks)}个知识片段"
            }

        return {"status": "no_content", "chunks": 0}

    def _add_to_vector_store(
        self,
        chunks: List[Chunk],
        course: str,
        chapter: int,
        source: str,
        doc_type: str,
        importance: str
    ) -> Dict:
        """添加到向量存储"""
        try:
            for chunk in chunks:
                self.db_manager.course_collection.add(
                    documents=[chunk.content],
                    embeddings=[chunk.embedding] if chunk.embedding else None,
                    metadatas=[{
                        "course": course,
                        "chapter": chapter,
                        "source": chunk.metadata.get("source", source),
                        "type": doc_type,
                        "importance": importance,
                        "page": chunk.metadata.get("page", 0),
                        "chunk_index": chunk.metadata.get("chunk_index", 0)
                    }],
                    ids=[chunk.id]
                )

            logger.info(f"向量化存储完成: {course} 第{chapter}章, {len(chunks)}个块")
            return {"status": "success", "chunks_stored": len(chunks)}

        except Exception as e:
            logger.error(f"向量化存储失败: {e}")
            return {"status": "error", "message": str(e)}

    def retrieve(
        self,
        query: str,
        course: Optional[str] = None,
        top_k: int = 5,
        score_threshold: float = 0.0
    ) -> List[SearchResult]:
        """检索相关知识"""
        # 获取查询embedding
        query_embedding = self.embedding_service.embed_query(query)

        try:
            # 从ChromaDB检索
            results = self.db_manager.course_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where={"course": course} if course else None
            )

            search_results = []
            if results and results.get('documents') and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    distance = results['distances'][0][i] if results.get('distances') else 0.0

                    # 转换为分数 (距离越小分数越高)
                    score = max(0, 1.0 - distance / 2.0)

                    if score >= score_threshold:
                        search_results.append(SearchResult(
                            content=doc,
                            metadata=metadata,
                            score=score,
                            distance=distance
                        ))

            return search_results

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []

    def get_context_for_topic(
        self,
        topic: str,
        knowledge_gaps: List[str],
        course: Optional[str] = None
    ) -> str:
        """为特定主题获取RAG上下文"""
        queries = [topic] + knowledge_gaps

        all_results = []
        for query in queries:
            results = self.retrieve(query, course=course, top_k=3, score_threshold=0.5)
            all_results.extend(results)

        # 去重并按分数排序
        seen = set()
        unique_results = []
        for r in sorted(all_results, key=lambda x: x.score, reverse=True):
            content_preview = r.content[:100]
            if content_preview not in seen:
                seen.add(content_preview)
                unique_results.append(r)

        # 构建上下文
        context_parts = []
        for r in unique_results[:5]:
            context_parts.append(f"[来源: {r.metadata.get('source', '未知')} | 重要性: {r.metadata.get('importance', '普通')}]\n{r.content}")

        return "\n\n---\n\n".join(context_parts)


# 全局RAG管道
rag_pipeline = RAGPipeline()
