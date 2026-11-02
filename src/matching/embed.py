"""공고 임베딩(의미 기반 검색). 글의 뜻을 숫자 목록(벡터)으로 바꿔 두고, 기업 설명과 얼마나 가까운지(코사인 유사도)를 잰다.

모델은 설정값(환경변수 EMBED_MODEL)으로 바꿀 수 있다. 기본은 가볍고 한국어를 지원하는 다국어 MiniLM(약 0.22GB).
공고 벡터는 파일로 저장해 두어 같은 공고를 다시 계산하지 않는다.
"""
import hashlib
import os
from pathlib import Path

import numpy as np

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_DIR = Path(__file__).resolve().parents[2] / "data" / "snapshots"


class Embedder:
    """fastembed(ONNX) 기반. 처음 쓸 때 모델을 내려받아 올린다."""

    def __init__(self, model: str | None = None):
        self.model_name = model or os.environ.get("EMBED_MODEL", DEFAULT_MODEL)
        self._model = None

    def embed(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from fastembed import TextEmbedding  # 무거운 import는 필요할 때만
            self._model = TextEmbedding(self.model_name)
        vecs = np.array(list(self._model.embed(list(texts))), dtype=np.float32)
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True).clip(min=1e-9)


def announcement_text(a: dict) -> str:
    """임베딩에 쓸 글. 제목과 요약을 앞에 둔다 (모델이 앞부분 위주로 읽는다)."""
    return f"{a['title']}. {a['summary'][:300]} 대상: {a['target']}. 분야: {a['field']}. 지역: {', '.join(a['regions'])}"


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def load_or_build_index(announcements: list[dict], embedder, index_path: Path | None = None) -> dict[str, np.ndarray]:
    """공고 id → 벡터. 글이 바뀌지 않은 공고는 저장된 벡터를 재사용한다."""
    safe = embedder.model_name.replace("/", "_") if hasattr(embedder, "model_name") else "custom"
    path = index_path or INDEX_DIR / f"embeddings_{safe}.npz"
    cache: dict[str, tuple[str, np.ndarray]] = {}
    if path.exists():
        z = np.load(path, allow_pickle=False)
        cache = {i: (h, v) for i, h, v in zip(z["ids"].tolist(), z["hashes"].tolist(), z["vecs"])}
    texts = {a["id"]: announcement_text(a) for a in announcements}
    todo = [i for i, t in texts.items() if i not in cache or cache[i][0] != _hash(t)]
    if todo:
        vecs = embedder.embed([texts[i] for i in todo])
        for i, v in zip(todo, vecs):
            cache[i] = (_hash(texts[i]), v)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            ids = list(cache)
            np.savez_compressed(path, ids=np.array(ids), hashes=np.array([cache[i][0] for i in ids]),
                                vecs=np.stack([cache[i][1] for i in ids]))
        except OSError:
            pass  # 쓰기 불가 환경(읽기 전용 배포 등)이어도 계산 결과는 쓸 수 있다
    return {i: cache[i][1] for i in texts}
