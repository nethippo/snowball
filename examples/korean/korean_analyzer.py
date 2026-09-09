"""Conservative Korean sentence normalization, independent of libstemmer.

Run with Python 3.9+ and the adjacent requirements.txt. No Redis dependency.
Positions on output tokens refer to the original UTF-8 input; morpheme positions
refer to normalized text, since contraction can give overlapping spans.
"""

import argparse
from bisect import bisect_right
from dataclasses import asdict, dataclass
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import sys
import unicodedata


POLICY = "case_only_v1"
ENGINE_VERSION = "0.23.1"
MODEL_VERSION = "0.23.0"
NOUNS = {"NNG", "NNP", "NNB", "NP"}
ENDINGS = {"EF", "EC", "ETM", "ETN"}


@dataclass(frozen=True)
class Segment:
    surface: str
    normalized: str
    start_byte: int
    end_byte: int
    start: int
    end: int


@dataclass(frozen=True)
class Morpheme:
    form: str
    tag: str
    start: int
    end: int
    oov: bool = False
    typo_cost: float = 0.0


def split_text(text, separators="|+=<>~"):
    """Keep original byte spans while normalizing each complete segment to NFC.

    Delimiters cannot participate in Hangul composition. Normalizing complete
    segments also handles canonical reordering without guessing character-wise
    alignment back into the original text.
    """
    text.encode("utf-8", errors="strict")  # Reject lone surrogates as well.
    parts, segments = [], []
    byte_pos = norm_pos = start = 0
    for i, char in enumerate(text):
        boundary = (char.isspace() or unicodedata.category(char).startswith("P")
                    or unicodedata.category(char) == "Cc" or char in separators)
        if not boundary:
            continue
        if start < i:
            surface = text[start:i]
            normalized = unicodedata.normalize("NFC", surface)
            end_byte = byte_pos + len(surface.encode("utf-8"))
            segments.append(Segment(surface, normalized, byte_pos, end_byte,
                                    norm_pos, norm_pos + len(normalized)))
            parts.append(normalized)
            byte_pos, norm_pos = end_byte, norm_pos + len(normalized)
        delimiter = unicodedata.normalize("NFC", char)
        parts.append(delimiter)
        byte_pos += len(char.encode("utf-8"))
        norm_pos += len(delimiter)
        start = i + 1
    if start < len(text):
        surface = text[start:]
        normalized = unicodedata.normalize("NFC", surface)
        segments.append(Segment(surface, normalized, byte_pos,
                                byte_pos + len(surface.encode("utf-8")),
                                norm_pos, norm_pos + len(normalized)))
        parts.append(normalized)
    return "".join(parts), segments


def _preserve(word, reason, pos="UNKNOWN", lemma=None):
    return {"canonical": word, "lemma": lemma, "pos": pos,
            "status": "preserved", "rule": reason}


def _result(word, canonical, pos, rule):
    return {"canonical": canonical, "lemma": canonical, "pos": pos,
            "status": "normalized" if canonical != word else "preserved",
            "rule": rule}


def _has_endings(tags):
    return bool(tags) and tags[-1] in ENDINGS and all(t == "EP" for t in tags[:-1])


def canonicalize(word, morphs):
    """Accept complete POS paths only; never strip a suffix on a partial parse."""
    if not word or not all("\uac00" <= c <= "\ud7a3" for c in word):
        return _preserve(word, "non_hangul")
    if not morphs:
        return _preserve(word, "missing_analysis")
    if any(m.oov for m in morphs):
        return _preserve(word, "out_of_vocabulary")
    if any(m.typo_cost for m in morphs):
        return _preserve(word, "spelling_correction")
    tags = [m.tag.split("-", 1)[0] for m in morphs]
    if all(t in NOUNS for t in tags):
        pos = "PRONOUN" if tags == ["NP"] else "NOUN"
        return _result(word, word, pos, "noun_unchanged")
    if tags[-1] in {"JKS", "JKO"} and tags[:-1] and all(t in NOUNS for t in tags[:-1]):
        base = "".join(m.form for m in morphs[:-1])
        # Kiwi already restores 나/저/너/누구 for 내가/제가/네가/누가.
        pos = "PRONOUN" if tags[:-1] == ["NP"] else "NOUN"
        return _result(word, base, pos, "case_particle")
    if tags in (["MAG"], ["MAJ"], ["XR", "XSM"]):
        return _result(word, word, "ADVERB", "adverb_unchanged")
    if tags[0] in {"VV", "VA"} and _has_endings(tags[1:]):
        stem = morphs[0].form
        # Some analyses lose ㄹ (e.g. 나는 -> 나/VV). These surface stems also
        # belong to other verbs; do not manufacture 나다/사다/파다 in this path.
        if stem in {"나", "사", "파", "거", "노", "우", "무", "여"} and morphs[1].form.startswith(("는", "니", "냐", "ᆸ")):
            return _preserve(word, "ambiguous_l_deletion")
        pos = "VERB" if tags[0] == "VV" else "ADJECTIVE"
        return _result(word, stem + "다", pos, "predicate_ending")
    for i, tag in enumerate(tags):
        if (tag in {"XSV", "XSA"} and i > 0
                and all(t in {"NNG", "NNP", "NNB", "XR", "XPN"} for t in tags[:i])
                and _has_endings(tags[i + 1:])):
            base = "".join(m.form for m in morphs[:i + 1])
            pos = "VERB" if tag == "XSV" else "ADJECTIVE"
            return _result(word, base + "다", pos, "derived_predicate")
    reason = "unsupported_particle" if any(t.startswith("J") for t in tags) else "unsupported_pos_path"
    return _preserve(word, reason)


def _group_morphemes(morphs, segments):
    groups = [[] for _ in segments]
    unsafe = set()
    starts = [s.start for s in segments]
    for m in morphs:
        index = max(0, bisect_right(starts, m.start) - 1)
        while index < len(segments) and segments[index].start < m.end:
            segment = segments[index]
            if m.start < segment.end and m.end > segment.start:
                if m.start < segment.start or m.end > segment.end or m.end <= m.start:
                    unsafe.add(index)
                else:
                    groups[index].append(m)
            index += 1
    for i, (segment, group) in enumerate(zip(segments, groups)):
        # Overlapping spans are expected for contracted vowels and endings.
        cursor = segment.start
        for m in sorted(group, key=lambda m: (m.start, m.end)):
            if m.start > cursor:
                unsafe.add(i)
            cursor = max(cursor, m.end)
        if cursor != segment.end:
            unsafe.add(i)
    return groups, unsafe


class KiwiBackend:
    def __init__(self, user_dictionary=None):
        try:
            from kiwipiepy import Kiwi
        except ImportError as exc:
            raise RuntimeError("Install examples/korean/requirements.txt in a virtual environment") from exc
        actual = (version("kiwipiepy"), version("kiwipiepy-model"))
        if actual != (ENGINE_VERSION, MODEL_VERSION):
            raise RuntimeError("Unsupported Kiwi/model versions; install the pinned requirements.txt")
        self._kiwi = Kiwi(num_workers=1, model_type="cong", load_typo_dict=False,
                          load_multi_dict=False, integrate_allomorph=True)
        entries = []
        if user_dictionary is not None:
            entries = json.loads(Path(user_dictionary).read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                raise ValueError("User dictionary must be a JSON array")
            seen = set()
            for entry in entries:
                if not isinstance(entry, dict) or set(entry) != {"word", "tag"}:
                    raise ValueError("Dictionary entries require exactly word and tag")
                word, tag = entry["word"], entry["tag"]
                if (not isinstance(word, str) or not word
                        or not all("\uac00" <= c <= "\ud7a3" for c in word)
                        or tag not in {"NNG", "NNP"} or word in seen):
                    raise ValueError("Dictionary words must be unique NFC Hangul nouns (NNG/NNP)")
                seen.add(word)
                self._kiwi.add_user_word(word, tag, 0.0)
        self.metadata = {"engine": "kiwipiepy", "engine_version": actual[0],
                         "model_package_version": actual[1], "model_type": "cong",
                         "user_dictionary_sha256": hashlib.sha256(
                             json.dumps(entries, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
                         "load_typo_dict": False, "load_multi_dict": False,
                         "integrate_allomorph": True}

    def analyze(self, text):
        return [([Morpheme(t.form, t.tag, t.start, t.end, t.oov, t.typo_cost)
                  for t in tokens], float(score))
                for tokens, score in self._kiwi.analyze(
                    text, top_n=3, match_options=0, normalize_coda=False,
                    z_coda=False, split_complex=False)]


class KoreanAnalyzer:
    """One instance per sequential worker. No implicit fallback to word stemming."""

    def __init__(self, *, backend=None, user_dictionary=None, ambiguity_margin=2.0,
                 separators="|+=<>~", max_chars=100000):
        if not math.isfinite(ambiguity_margin) or ambiguity_margin < 0:
            raise ValueError("ambiguity_margin must be finite and nonnegative")
        if max_chars < 1:
            raise ValueError("max_chars must be positive")
        if any(not (c.isspace() or unicodedata.category(c)[0] in "PS"
                    or unicodedata.category(c) == "Cc") for c in separators):
            raise ValueError("Separators must be whitespace, punctuation, symbols or controls")
        if backend is not None and user_dictionary is not None:
            raise ValueError("Pass a configured backend or a user dictionary, not both")
        self.backend = backend if backend is not None else KiwiBackend(user_dictionary)
        self.ambiguity_margin = ambiguity_margin
        self.separators = separators
        self.max_chars = max_chars
        self.metadata = dict(self.backend.metadata, policy=POLICY, normalization="NFC",
                             unicode_version=unicodedata.unidata_version,
                             ambiguity_margin=ambiguity_margin, separators=separators,
                             top_n=3, max_chars=max_chars)
        fingerprint = hashlib.sha256(json.dumps(self.metadata, sort_keys=True).encode()).hexdigest()[:16]
        self.analysis_version = "ko-morph-v1:" + fingerprint

    def analyze(self, text):
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="strict")
        if not isinstance(text, str):
            raise TypeError("Expected str or UTF-8 bytes")
        if len(text) > self.max_chars:
            raise ValueError("Input exceeds max_chars; no text was truncated")
        normalized, segments = split_text(text, self.separators)
        result = {"analysis_version": self.analysis_version, "policy": POLICY,
                  "normalization": "NFC", "metadata": dict(self.metadata), "tokens": []}
        if not segments:
            return result
        candidates = self.backend.analyze(normalized)
        if not candidates or any(not math.isfinite(score) for _, score in candidates):
            raise RuntimeError("Analyzer did not return valid candidates")
        candidates = sorted(candidates, key=lambda item: item[1], reverse=True)
        analyses = []
        for morphs, score in candidates:
            groups, unsafe = _group_morphemes(morphs, segments)
            decisions = [(_preserve(s.normalized, "unaligned_analysis") if i in unsafe
                          else canonicalize(s.normalized, groups[i]))
                         for i, s in enumerate(segments)]
            analyses.append((decisions, groups, score))
        best, groups, score = analyses[0]
        for i, segment in enumerate(segments):
            decision = best[i]
            for other, _, other_score in analyses[1:]:
                if score - other_score > self.ambiguity_margin:
                    continue
                if (decision["canonical"], decision["pos"]) != (other[i]["canonical"], other[i]["pos"]):
                    decision = _preserve(segment.normalized, "ambiguous_analysis")
                    break
            result["tokens"].append(dict(
                decision, surface=segment.surface, normalized=segment.normalized,
                eojeol_id=i, start_byte=segment.start_byte, end_byte=segment.end_byte,
                normalized_start=segment.start, normalized_end=segment.end,
                morphemes=[asdict(m) for m in groups[i]]))
        result["analysis_score"] = score  # Model score, NOT a confidence probability.
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", help="Sentence; otherwise read all UTF-8 stdin")
    parser.add_argument("--words", action="store_true", help="Return only canonical words as JSON")
    parser.add_argument("--user-dictionary", type=Path)
    parser.add_argument("--ambiguity-margin", type=float, default=2.0)
    args = parser.parse_args(argv)
    try:
        text = args.text if args.text is not None else sys.stdin.buffer.read()
        analyzer = KoreanAnalyzer(user_dictionary=args.user_dictionary,
                                  ambiguity_margin=args.ambiguity_margin)
        result = analyzer.analyze(text)
        if args.words:
            result = [t["canonical"] for t in result["tokens"]]
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, TypeError, RuntimeError, OSError) as exc:
        parser.exit(2, f"korean_analyzer: {exc}\n")


if __name__ == "__main__":
    main()
