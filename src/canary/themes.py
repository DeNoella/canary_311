"""Theme discovery on complaint text -- fully local, zero paid APIs.

Pipeline:
  1. Embed the unique complaint strings.
       - Preferred: sentence-transformers ``all-MiniLM-L6-v2`` (free, local).
       - Fallback: TF-IDF -> TruncatedSVD dense vectors (pure scikit-learn).
     Embeddings are cached to cache/ so re-runs are instant.
  2. KMeans into CFG.n_themes clusters.
  3. Auto-label each cluster with its top TF-IDF terms (no LLM).
  4. Attach a theme id + label to every sampled complaint.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from .config import CACHE, CFG, PROCESSED

_EXTRA_STOP = {
    "nyc", "complaint", "condition", "issue", "request", "service", "other",
    "street", "st", "ave", "avenue", "new", "york", "na",
}
_STOP = list(ENGLISH_STOP_WORDS | _EXTRA_STOP)


def _embed(texts: list[str]) -> tuple[np.ndarray, str]:
    key = hashlib.md5(
        ("||".join(texts) + f"|{CFG.embed_model}").encode()
    ).hexdigest()[:16]
    npy = CACHE / f"emb_{key}.npy"
    meta = CACHE / f"emb_{key}.json"
    if npy.exists() and meta.exists():
        method = json.loads(meta.read_text())["method"]
        return np.load(npy), method

    method = "tfidf-svd"
    vecs: np.ndarray | None = None
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        model = SentenceTransformer(CFG.embed_model)
        vecs = np.asarray(
            model.encode(texts, batch_size=256, show_progress_bar=True,
                         normalize_embeddings=True),
            dtype="float32",
        )
        method = f"sentence-transformers/{CFG.embed_model}"
    except Exception as e:  # noqa: BLE001 - any failure -> local TF-IDF fallback
        print(f"  themes: sentence-transformers unavailable ({e.__class__.__name__}); "
              f"using TF-IDF+SVD fallback")
        min_df = 3 if len(texts) > 500 else 1
        tfidf = TfidfVectorizer(stop_words=_STOP, min_df=min_df, max_features=20_000,
                                ngram_range=(1, 2))
        X = tfidf.fit_transform(texts)
        k = max(2, min(256, X.shape[1] - 1, X.shape[0] - 1))
        svd = TruncatedSVD(n_components=k, random_state=42)
        vecs = svd.fit_transform(X).astype("float32")
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / np.clip(norms, 1e-9, None)

    np.save(npy, vecs)
    meta.write_text(json.dumps({"method": method, "n": len(texts)}))
    return vecs, method


def _label_clusters(texts: list[str], labels: np.ndarray, k: int) -> dict[int, str]:
    tfidf = TfidfVectorizer(stop_words=_STOP, min_df=2, max_features=5000,
                            ngram_range=(1, 2))
    X = tfidf.fit_transform(texts)
    terms = np.array(tfidf.get_feature_names_out())
    out: dict[int, str] = {}
    for c in range(k):
        mask = labels == c
        if not mask.any():
            out[c] = f"theme {c}"
            continue
        mean = np.asarray(X[mask].mean(axis=0)).ravel()
        top = terms[mean.argsort()[::-1][:6]]
        # de-duplicate words across the chosen terms, keep the first 3 phrases
        seen: set[str] = set()
        phrases: list[str] = []
        for t in top:
            words = [w for w in t.split() if w not in seen]
            if not words:
                continue
            seen.update(words)
            phrases.append(" ".join(words))
            if len(phrases) == 3:
                break
        out[c] = " / ".join(phrases) if phrases else f"theme {c}"
    return out


def run(sample: pd.DataFrame) -> pd.DataFrame:
    texts_all = sample["text"].fillna("").astype(str)
    uniq = sorted(t for t in texts_all.unique() if t.strip())
    print(f"  themes: embedding {len(uniq):,} unique complaint strings "
          f"({len(sample):,} rows)")
    vecs, method = _embed(uniq)

    k = int(min(CFG.n_themes, max(2, len(uniq))))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    uniq_labels = km.fit_predict(vecs)

    label_map = _label_clusters(uniq, uniq_labels, k)
    text_to_theme = dict(zip(uniq, uniq_labels))

    sample = sample.copy()
    sample["theme_id"] = sample["text"].map(text_to_theme).fillna(-1).astype(int)
    sample["theme"] = sample["theme_id"].map(label_map).fillna("unclassified")

    sample.to_parquet(PROCESSED / "complaints_themes.parquet", index=False)
    themes_tbl = pd.DataFrame(
        {"theme_id": list(label_map), "theme": list(label_map.values())}
    )
    themes_tbl["n"] = themes_tbl["theme_id"].map(
        sample["theme_id"].value_counts()
    ).fillna(0).astype(int)
    themes_tbl.sort_values("n", ascending=False).to_parquet(
        PROCESSED / "theme_catalog.parquet", index=False
    )
    (PROCESSED / "theme_meta.json").write_text(
        json.dumps({"method": method, "k": k}, indent=2)
    )
    print(f"  themes: {k} clusters via {method}")
    return sample
