"""
core/knowledge_base.py
NotebookLM 스타일 지식 베이스 시스템

Gemini 2.5 Pro를 사용하여 문서 기반 그라운딩 응답을 생성한다.
에이전트가 전문 지식을 확보할 수 있도록 문서를 등록하고 질의한다.

구조:
  knowledge/
    {kb_id}/
      metadata.json    — 지식 베이스 메타데이터, 소스 목록
      sources/
        src_xxxx.md    — 텍스트 소스 파일

외부 의존: httpx (기존 ai_router와 동일)
"""

import os
import json
import uuid
import shutil
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

logger = logging.getLogger("knowledge_base")

# ─── 경로/설정 상수 ───────────────────────────────────
_CORE_DIR = Path(__file__).parent
_PROJECT_ROOT = _CORE_DIR.parent
_KB_DIR = _PROJECT_ROOT / "knowledge"

GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/{model}:generateContent"
)

# 소스 텍스트 합산 최대 크기 (약 200KB → 약 5만 토큰)
MAX_CONTEXT_BYTES = 200_000


# ═══════════════════════════════════════════════════════
# KnowledgeBase 클래스
# ═══════════════════════════════════════════════════════

class KnowledgeBase:
    """
    단일 지식 베이스. 문서(소스)를 관리하고 Gemini로 질의한다.
    """

    def __init__(self, kb_id: str):
        self.kb_id = kb_id
        self.root = _KB_DIR / kb_id
        self.sources_dir = self.root / "sources"
        self.metadata_path = self.root / "metadata.json"

    # ─── 상태 확인 ────────────────────────────────────

    def exists(self) -> bool:
        return self.metadata_path.exists()

    def get_metadata(self) -> dict:
        if not self.exists():
            return {}
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def _save_metadata(self, meta: dict):
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.metadata_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ─── 소스 관리 ────────────────────────────────────

    def add_text(self, title: str, content: str) -> dict:
        """텍스트 소스를 추가한다."""
        self.sources_dir.mkdir(parents=True, exist_ok=True)

        source_id = f"src_{uuid.uuid4().hex[:8]}"
        filename = f"{source_id}.md"
        source_path = self.sources_dir / filename

        source_path.write_text(content, encoding="utf-8")

        meta = self.get_metadata()
        sources = meta.get("sources", [])
        sources.append({
            "source_id": source_id,
            "title": title,
            "type": "text",
            "filename": filename,
            "size_bytes": len(content.encode("utf-8")),
            "added_at": datetime.now(timezone.utc).isoformat(),
        })
        meta["sources"] = sources
        self._save_metadata(meta)

        logger.info("소스 추가: kb=%s, source=%s, title=%s", self.kb_id, source_id, title)
        return {"success": True, "source_id": source_id, "title": title}

    def add_file(self, filepath: str, title: Optional[str] = None) -> dict:
        """로컬 텍스트 파일을 소스로 추가한다."""
        src = Path(filepath)
        if not src.exists():
            return {"success": False, "message": f"파일이 없습니다: {filepath}"}

        content = src.read_text(encoding="utf-8")
        if title is None:
            title = src.stem
        return self.add_text(title, content)

    def list_sources(self) -> list[dict]:
        """등록된 소스 목록."""
        return self.get_metadata().get("sources", [])

    def get_source_content(self, source_id: str) -> Optional[str]:
        """특정 소스의 본문을 반환한다."""
        for s in self.list_sources():
            if s["source_id"] == source_id:
                path = self.sources_dir / s["filename"]
                if path.exists():
                    return path.read_text(encoding="utf-8")
        return None

    def remove_source(self, source_id: str) -> dict:
        """소스를 삭제한다."""
        meta = self.get_metadata()
        sources = meta.get("sources", [])

        found = None
        for i, s in enumerate(sources):
            if s["source_id"] == source_id:
                found = sources.pop(i)
                break

        if not found:
            return {"success": False, "message": f"소스 '{source_id}'를 찾을 수 없습니다."}

        # 파일 삭제
        filepath = self.sources_dir / found["filename"]
        if filepath.exists():
            filepath.unlink()

        meta["sources"] = sources
        self._save_metadata(meta)

        logger.info("소스 삭제: kb=%s, source=%s", self.kb_id, source_id)
        return {"success": True, "removed": found["title"]}

    # ─── 컨텍스트 빌드 ────────────────────────────────

    def _build_context(self) -> str:
        """모든 소스를 하나의 컨텍스트 텍스트로 결합한다."""
        meta = self.get_metadata()
        parts = []
        total_bytes = 0

        for s in meta.get("sources", []):
            filepath = self.sources_dir / s["filename"]
            if not filepath.exists():
                continue

            content = filepath.read_text(encoding="utf-8")
            content_bytes = len(content.encode("utf-8"))

            # 최대 크기 초과 시 중단
            if total_bytes + content_bytes > MAX_CONTEXT_BYTES:
                remaining = MAX_CONTEXT_BYTES - total_bytes
                if remaining > 500:
                    content = content[:remaining]
                    parts.append(f"=== 문서: {s['title']} (일부) ===\n{content}")
                break

            parts.append(f"=== 문서: {s['title']} ===\n{content}")
            total_bytes += content_bytes

        return "\n\n".join(parts)

    # ─── Gemini 질의 ──────────────────────────────────

    async def query(self, question: str) -> dict:
        """
        지식 베이스의 문서를 기반으로 Gemini 2.5 Pro에 질의한다.
        NotebookLM과 동일한 원리: 문서 컨텍스트 + 질문 → 그라운딩된 답변.
        """
        api_key = os.environ.get(GEMINI_API_KEY_ENV, "")
        if not api_key:
            return {"answer": "", "error": f"{GEMINI_API_KEY_ENV}가 설정되지 않았습니다."}

        if not _HAS_HTTPX:
            return {"answer": "", "error": "httpx 패키지가 필요합니다."}

        context = self._build_context()
        if not context:
            return {"answer": "", "error": "지식 베이스에 소스가 없습니다."}

        url = GEMINI_URL.format(model=GEMINI_MODEL) + f"?key={api_key}"

        payload = {
            "systemInstruction": {
                "parts": [{
                    "text": (
                        "너는 지식 베이스 어시스턴트다. "
                        "아래 제공된 문서들만을 근거로 정확하게 답변하라.\n"
                        "규칙:\n"
                        "1. 문서에 있는 정보만 사용하라. 추측하지 마라.\n"
                        "2. 답변 시 참조한 문서 제목을 [출처: 문서명] 형식으로 명시하라.\n"
                        "3. 문서에 없는 내용은 '제공된 문서에서 해당 정보를 찾을 수 없습니다'라고 답하라.\n"
                        "4. 한국어로 응답하라.\n"
                        "5. 핵심을 먼저, 세부사항은 뒤에 배치하라."
                    )
                }]
            },
            "contents": [{
                "role": "user",
                "parts": [{
                    "text": (
                        f"[참조 문서]\n{context}\n\n"
                        f"[질문]\n{question}"
                    )
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 4096,
                "temperature": 0.3,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    url, json=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()

            answer = data["candidates"][0]["content"]["parts"][0]["text"]

            return {
                "answer": answer,
                "kb_id": self.kb_id,
                "kb_name": self.get_metadata().get("name", ""),
                "sources_used": len(self.list_sources()),
                "model": GEMINI_MODEL,
                "error": None,
            }
        except Exception as e:
            logger.error("Gemini 질의 실패 [kb=%s]: %s", self.kb_id, e)
            return {"answer": "", "error": str(e)}


# ═══════════════════════════════════════════════════════
# 팩토리 함수
# ═══════════════════════════════════════════════════════

def create_knowledge_base(kb_id: str, name: str, description: str = "") -> dict:
    """새 지식 베이스를 생성한다."""
    kb = KnowledgeBase(kb_id)
    if kb.exists():
        return {"success": False, "message": f"지식 베이스 '{kb_id}'가 이미 존재합니다."}

    kb.root.mkdir(parents=True, exist_ok=True)
    kb.sources_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "kb_id": kb_id,
        "name": name,
        "description": description,
        "sources": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    kb.metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info("지식 베이스 생성: %s (%s)", kb_id, name)
    return {"success": True, "kb_id": kb_id, "name": name}


def get_knowledge_base(kb_id: str) -> Optional[KnowledgeBase]:
    """지식 베이스 인스턴스를 반환한다."""
    kb = KnowledgeBase(kb_id)
    if kb.exists():
        return kb
    return None


def list_knowledge_bases() -> list[dict]:
    """모든 지식 베이스 목록."""
    if not _KB_DIR.exists():
        return []

    result = []
    for d in sorted(_KB_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / "metadata.json"
        if not meta_path.exists():
            continue

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        result.append({
            "kb_id": meta.get("kb_id", d.name),
            "name": meta.get("name", ""),
            "description": meta.get("description", ""),
            "sources_count": len(meta.get("sources", [])),
            "created_at": meta.get("created_at", ""),
        })
    return result


def delete_knowledge_base(kb_id: str) -> dict:
    """지식 베이스를 삭제한다."""
    kb = KnowledgeBase(kb_id)
    if not kb.exists():
        return {"success": False, "message": f"지식 베이스 '{kb_id}'를 찾을 수 없습니다."}

    shutil.rmtree(kb.root)
    logger.info("지식 베이스 삭제: %s", kb_id)
    return {"success": True, "message": f"지식 베이스 '{kb_id}' 삭제 완료"}
