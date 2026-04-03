import sqlite3
import time

from src.utils.config import USER_DATA_DIR


CACHE_DB = USER_DATA_DIR / "cache.db"
MAX_ENTRIES = 1000
EXPIRY_SECONDS = 86400  # 24 hours


class TranslationCache:
    def __init__(self):
        self._conn = sqlite3.connect(str(CACHE_DB), check_same_thread=False)
        self._create_table()
        self._cleanup()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_text TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                timestamp REAL NOT NULL,
                last_accessed REAL NOT NULL,
                UNIQUE(source_text, source_lang, target_lang)
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lookup
            ON translations(source_text, source_lang, target_lang)
        """)
        self._conn.commit()

    def get(self, source_text: str, source_lang: str, target_lang: str) -> str | None:
        now = time.time()
        cursor = self._conn.execute(
            """SELECT translated_text, timestamp FROM translations
               WHERE source_text = ? AND source_lang = ? AND target_lang = ?""",
            (source_text, source_lang, target_lang),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        translated, timestamp = row
        if now - timestamp > EXPIRY_SECONDS:
            self._conn.execute(
                """DELETE FROM translations
                   WHERE source_text = ? AND source_lang = ? AND target_lang = ?""",
                (source_text, source_lang, target_lang),
            )
            self._conn.commit()
            return None
        self._conn.execute(
            """UPDATE translations SET last_accessed = ?
               WHERE source_text = ? AND source_lang = ? AND target_lang = ?""",
            (now, source_text, source_lang, target_lang),
        )
        self._conn.commit()
        return translated

    def put(self, source_text: str, source_lang: str, target_lang: str, translated_text: str):
        now = time.time()
        self._conn.execute(
            """INSERT INTO translations (source_text, source_lang, target_lang, translated_text, timestamp, last_accessed)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(source_text, source_lang, target_lang)
               DO UPDATE SET translated_text = ?, timestamp = ?, last_accessed = ?""",
            (source_text, source_lang, target_lang, translated_text, now, now,
             translated_text, now, now),
        )
        self._conn.commit()
        self._evict_if_needed()

    def _cleanup(self):
        now = time.time()
        self._conn.execute(
            "DELETE FROM translations WHERE ? - timestamp > ?",
            (now, EXPIRY_SECONDS),
        )
        self._conn.commit()

    def _evict_if_needed(self):
        cursor = self._conn.execute("SELECT COUNT(*) FROM translations")
        count = cursor.fetchone()[0]
        if count > MAX_ENTRIES:
            excess = count - MAX_ENTRIES
            self._conn.execute(
                """DELETE FROM translations WHERE id IN (
                       SELECT id FROM translations ORDER BY last_accessed ASC LIMIT ?
                   )""",
                (excess,),
            )
            self._conn.commit()

    def clear(self):
        self._conn.execute("DELETE FROM translations")
        self._conn.commit()

    def close(self):
        self._conn.close()
