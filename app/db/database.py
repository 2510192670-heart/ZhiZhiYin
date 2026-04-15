"""
智知因 - 数据库管理器
SQLite存储业务数据，ChromaDB存储向量知识库
"""
import sqlite3
import json
import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from app.config import settings


class DatabaseManager:
    """统一数据库管理器"""

    def __init__(self):
        self.sqlite_path = settings.SQLITE_DB_PATH
        self.chroma_path = settings.CHROMA_DB_PATH
        self._init_sqlite()
        self._init_chroma()

    def _init_sqlite(self):
        """初始化SQLite数据库"""
        with sqlite3.connect(self.sqlite_path) as conn:
            cursor = conn.cursor()

            # 用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    student_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    major TEXT DEFAULT '计算机科学',
                    grade TEXT DEFAULT '大一',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 学生档案表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS student_profiles (
                    user_id TEXT PRIMARY KEY,
                    level INTEGER DEFAULT 1,
                    learning_style TEXT DEFAULT '文本',
                    weaknesses TEXT DEFAULT '[]',
                    mastered_nodes TEXT DEFAULT '[]',
                    last_study_topic TEXT,
                    last_study_time TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # 学习记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_records (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    score REAL,
                    knowledge_gaps TEXT DEFAULT '[]',
                    resources_used TEXT DEFAULT '[]',
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            # 学习会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS study_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    current_state TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)

            conn.commit()
            logger.info(f"SQLite数据库初始化完成: {self.sqlite_path}")

    def _init_chroma(self):
        """初始化ChromaDB向量数据库"""
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False)
        )

        # 创建课程知识库集合
        self.course_collection = self.chroma_client.get_or_create_collection(
            name="course_knowledge_base",
            metadata={"description": "课程知识库，用于RAG检索"}
        )

        # 创建用户会话历史集合
        self.history_collection = self.chroma_client.get_or_create_collection(
            name="session_history",
            metadata={"description": "会话历史记录"}
        )

        logger.info(f"ChromaDB初始化完成: {self.chroma_path}")

    # ========== 用户操作 ==========

    def create_user(self, user_id: str, student_id: str, name: str,
                    major: str = "计算机科学", grade: str = "大一") -> bool:
        """创建用户"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, student_id, name, major, grade)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, student_id, name, major, grade))

                # 同时创建学生档案
                cursor.execute("""
                    INSERT INTO student_profiles (user_id)
                    VALUES (?)
                """, (user_id,))

                conn.commit()
                logger.info(f"用户创建成功: {user_id}")
                return True
        except Exception as e:
            logger.error(f"用户创建失败: {e}")
            return False

    def get_user_by_student_id(self, student_id: str) -> Optional[Dict]:
        """根据学号获取用户"""
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE student_id = ?", (student_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ========== 学生档案操作 ==========

    def get_profile(self, user_id: str) -> Optional[Dict]:
        """获取学生档案"""
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM student_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                data['weaknesses'] = json.loads(data.get('weaknesses', '[]'))
                data['mastered_nodes'] = json.loads(data.get('mastered_nodes', '[]'))
                return data
            return None

    def update_profile(self, user_id: str, **kwargs) -> bool:
        """更新学生档案"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                for key, value in kwargs.items():
                    if key in ['weaknesses', 'mastered_nodes']:
                        value = json.dumps(value)
                    cursor.execute(f"""
                        UPDATE student_profiles SET {key} = ?
                        WHERE user_id = ?
                    """, (value, user_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"档案更新失败: {e}")
            return False

    # ========== 学习记录操作 ==========

    def add_learning_record(self, user_id: str, topic: str, score: float,
                           knowledge_gaps: List[str], resources_used: List[str],
                           session_id: str) -> bool:
        """添加学习记录"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO learning_records
                    (user_id, topic, score, knowledge_gaps, resources_used, session_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, topic, score, json.dumps(knowledge_gaps),
                      json.dumps(resources_used), session_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"学习记录添加失败: {e}")
            return False

    def get_learning_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """获取学习历史"""
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM learning_records
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # ========== 学习会话操作 ==========

    def create_session(self, session_id: str, user_id: str, topic: str) -> bool:
        """创建学习会话"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO study_sessions (session_id, user_id, topic)
                    VALUES (?, ?, ?)
                """, (session_id, user_id, topic))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"会话创建失败: {e}")
            return False

    def update_session_state(self, session_id: str, state: Dict) -> bool:
        """更新会话状态"""
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE study_sessions
                    SET current_state = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = ?
                """, (json.dumps(state), session_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"会话状态更新失败: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM study_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ========== RAG向量操作 ==========

    def add_knowledge(self, course: str, chapter: int, content: str,
                     source: str, doc_type: str = "concept",
                     importance: str = "核心") -> str:
        """添加知识到向量库"""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from langchain.text_splitter import RecursiveCharacterTextSplitter

            # 文本分割
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            chunks = text_splitter.split_text(content)

            # 添加到ChromaDB
            for i, chunk in enumerate(chunks):
                self.course_collection.add(
                    documents=[chunk],
                    metadatas=[{
                        "course": course,
                        "chapter": chapter,
                        "source": source,
                        "type": doc_type,
                        "importance": importance,
                        "chunk_index": i
                    }],
                    ids=[f"{course}_ch{chapter}_{doc_type}_{i}"]
                )
            logger.info(f"知识添加成功: {course} 第{chapter}章, {len(chunks)}个片段")
            return f"成功添加{len(chunks)}个知识片段"
        except Exception as e:
            logger.error(f"知识添加失败: {e}")
            return str(e)

    def vector_search(self, query: str, course: str = None, top_k: int = 5) -> List[Dict]:
        """向量相似度搜索"""
        try:
            results = self.course_collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"course": course} if course else None
            )

            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    search_results.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if 'distances' in results else 0
                    })
            return search_results
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    def get_course_chapters(self, course: str) -> List[int]:
        """获取课程所有章节"""
        try:
            result = self.course_collection.get(
                where={"course": course}
            )
            chapters = set()
            for meta in result.get('metadatas', []):
                if meta and 'chapter' in meta:
                    chapters.add(meta['chapter'])
            return sorted(list(chapters))
        except Exception as e:
            logger.error(f"获取课程章节失败: {e}")
            return []

    def delete_course_knowledge(self, course: str) -> bool:
        """删除课程所有知识"""
        try:
            self.course_collection.delete(where={"course": course})
            logger.info(f"课程知识删除成功: {course}")
            return True
        except Exception as e:
            logger.error(f"课程知识删除失败: {e}")
            return False


# 全局单例
db_manager = DatabaseManager()
