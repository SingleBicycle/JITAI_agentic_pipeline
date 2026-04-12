import os
from difflib import SequenceMatcher


try:
    from bert_score import BERTScorer as _BERTScorer  # type: ignore
except ImportError:  # pragma: no cover
    _BERTScorer = None


class FallbackBERTScorer:
    def __init__(self, *args, **kwargs):
        self.mode = "fallback"

    def score(self, text1, text2):
        if isinstance(text1, str):
            text1 = [text1]
        if isinstance(text2, str):
            text2 = [text2]

        scores = []
        for left, right in zip(text1, text2):
            scores.append(SequenceMatcher(None, left, right).ratio())

        class _ScoreList:
            def __init__(self, values):
                self._values = values

            def mean(self):
                class _MeanValue:
                    def __init__(self, value):
                        self._value = value

                    def item(self):
                        return self._value

                if not self._values:
                    return _MeanValue(0.0)
                return _MeanValue(sum(self._values) / len(self._values))

            def tolist(self):
                return list(self._values)

        wrapped = _ScoreList(scores)
        return wrapped, wrapped, wrapped


class SafeBERTScorer:
    def __init__(self, model_type="microsoft/deberta-xlarge-mnli", lang="en"):
        if _BERTScorer is None:
            raise ImportError(
                "bert-score is not installed. Run `pip install bert-score` in the active environment."
            )

        self.model_type = model_type
        self.lang = lang
        self.max_char_length = int(os.getenv("AVA_BERT_SCORE_MAX_CHAR_LENGTH", "4000"))
        self.max_token_length = int(os.getenv("AVA_BERT_SCORE_MAX_TOKEN_LENGTH", "512"))
        self.scorer = _BERTScorer(model_type=model_type, lang=lang)
        self._configure_tokenizer()

    def _configure_tokenizer(self):
        tokenizer = getattr(self.scorer, "_tokenizer", None)
        if tokenizer is None:
            return

        config = getattr(getattr(self.scorer, "_model", None), "config", None)
        config_limit = getattr(config, "max_position_embeddings", None)
        limit_candidates = [self.max_token_length]
        if isinstance(config_limit, int) and config_limit > 0:
            limit_candidates.append(config_limit)

        model_limit = getattr(tokenizer, "model_max_length", None)
        if isinstance(model_limit, int) and 0 < model_limit < 10**6:
            limit_candidates.append(model_limit)

        safe_limit = min(limit_candidates)
        tokenizer.model_max_length = safe_limit
        init_kwargs = getattr(tokenizer, "init_kwargs", None)
        if isinstance(init_kwargs, dict):
            init_kwargs["model_max_length"] = safe_limit

    def _normalize_texts(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        normalized = []
        for text in texts:
            if text is None:
                text = ""
            text = str(text).strip()
            if len(text) > self.max_char_length:
                text = text[: self.max_char_length]
            normalized.append(text)
        return normalized

    def score(self, text1, text2):
        text1 = self._normalize_texts(text1)
        text2 = self._normalize_texts(text2)
        return self.scorer.score(text1, text2)


def get_bert_scorer(model_type=None, lang="en"):
    model_type = model_type or os.getenv(
        "AVA_BERT_SCORE_MODEL_TYPE", "microsoft/deberta-xlarge-mnli"
    )
    allow_fallback = os.getenv("AVA_ALLOW_TEXT_SIMILARITY_FALLBACK", "0").lower() in {
        "1",
        "true",
        "yes",
    }

    try:
        return SafeBERTScorer(model_type=model_type, lang=lang)
    except Exception:
        if allow_fallback:
            return FallbackBERTScorer()
        raise
