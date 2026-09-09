import json
from pathlib import Path
import subprocess
import sys
import unittest
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/korean"))
from korean_analyzer import KoreanAnalyzer, Morpheme, canonicalize, split_text


class Backend:
    metadata = {"engine": "test"}

    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = []

    def analyze(self, text):
        self.calls.append(text)
        return self.candidates


class AdapterContractTests(unittest.TestCase):
    def test_nfc_and_original_byte_spans(self):
        text = "😀，" + unicodedata.normalize("NFD", "학생이") + "\t사과를/먹었다."
        normalized, segments = split_text(text)
        self.assertEqual(normalized, unicodedata.normalize("NFC", text))
        self.assertEqual([s.normalized for s in segments], ["😀", "학생이", "사과를", "먹었다"])
        for s in segments:
            self.assertEqual(text.encode()[s.start_byte:s.end_byte].decode(), s.surface)
            self.assertEqual(normalized[s.start:s.end], s.normalized)

    def test_delimiters_and_empty_segments(self):
        _, segments = split_text("\t 학생이，，사과를|먹었다+ABC_123\u00a0학교가\u3000")
        self.assertEqual([s.surface for s in segments], ["학생이", "사과를", "먹었다", "ABC", "123", "학교가"])
        self.assertEqual(split_text(" \n,，|\t")[1], [])

    def test_combining_marks_and_compatibility_jamo_are_not_guessed(self):
        text, segments = split_text("a\u0315\u0300 ㅎㅏㄴ")
        self.assertEqual(text, unicodedata.normalize("NFC", "a\u0315\u0300 ㅎㅏㄴ"))
        self.assertEqual(segments[1].normalized, "ㅎㅏㄴ")
        self.assertEqual(canonicalize("ㅎㅏㄴ", [])["canonical"], "ㅎㅏㄴ")

    def test_delimiter_canonical_normalization(self):
        text = "학교\u037e책"
        normalized, segments = split_text(text)
        self.assertEqual(normalized, unicodedata.normalize("NFC", text))
        for segment in segments:
            self.assertEqual(normalized[segment.start:segment.end], segment.normalized)
            self.assertEqual(text.encode()[segment.start_byte:segment.end_byte].decode(), segment.surface)

    def test_empty_input_does_not_call_backend(self):
        backend = Backend([])
        self.assertEqual(KoreanAnalyzer(backend=backend).analyze(" ,\t")["tokens"], [])
        self.assertEqual(backend.calls, [])

    def test_invalid_utf8_and_surrogates(self):
        analyzer = KoreanAnalyzer(backend=Backend([]))
        for text in [b"\xff", "\ud800"]:
            with self.assertRaises(UnicodeError):
                analyzer.analyze(text)

    def test_configuration_validation_and_limits(self):
        for value in [-1, float("nan"), float("inf")]:
            with self.assertRaises(ValueError):
                KoreanAnalyzer(backend=Backend([]), ambiguity_margin=value)
        with self.assertRaises(ValueError):
            KoreanAnalyzer(backend=Backend([]), separators="\u1161")
        with self.assertRaises(ValueError):
            KoreanAnalyzer(backend=Backend([]), max_chars=1).analyze("학교")

    def test_near_candidates_disagree_preserves(self):
        backend = Backend([
            ([Morpheme("걷", "VV-I", 0, 1), Morpheme("었", "EP", 1, 2), Morpheme("다", "EF", 2, 3)], -10),
            ([Morpheme("걸", "VV", 0, 1), Morpheme("었", "EP", 1, 2), Morpheme("다", "EF", 2, 3)], -11),
        ])
        token = KoreanAnalyzer(backend=backend).analyze("걸었다")["tokens"][0]
        self.assertEqual((token["canonical"], token["rule"]), ("걸었다", "ambiguous_analysis"))

    def test_equivalent_endings_do_not_count_as_ambiguity(self):
        backend = Backend([
            ([Morpheme("먹", "VV", 0, 1), Morpheme("다", "EF", 1, 2)], -10),
            ([Morpheme("먹", "VV", 0, 1), Morpheme("다", "EC", 1, 2)], -10),
        ])
        token = KoreanAnalyzer(backend=backend).analyze("먹다")["tokens"][0]
        self.assertEqual(token["lemma"], "먹다")

    def test_overlapping_contraction_spans(self):
        backend = Backend([([Morpheme("하", "VV", 0, 1), Morpheme("었", "EP", 0, 1),
                             Morpheme("다", "EF", 1, 2)], -1)])
        token = KoreanAnalyzer(backend=backend).analyze("했다")["tokens"][0]
        self.assertEqual(token["canonical"], "하다")
        self.assertEqual((token["start_byte"], token["end_byte"]), (0, 6))

    def test_cross_boundary_or_partial_analysis_preserved(self):
        for morphs in [[Morpheme("학교책", "NNG", 0, 4)], [Morpheme("학", "NNG", 0, 1)]]:
            result = KoreanAnalyzer(backend=Backend([(morphs, -1)])).analyze("학교 책")
            self.assertEqual([t["canonical"] for t in result["tokens"]], ["학교", "책"])
            self.assertTrue(all(t["rule"] == "unaligned_analysis" for t in result["tokens"]))

    def test_backend_failure_is_not_silent_fallback(self):
        for candidates in [[], [([], float("nan"))]]:
            with self.assertRaises(RuntimeError):
                KoreanAnalyzer(backend=Backend(candidates)).analyze("학교")

    def test_oov_and_other_particles_preserved(self):
        cases = [
            ("쀍쀍이가", [Morpheme("쀍쀍이", "NNP", 0, 3, oov=True), Morpheme("가", "JKS", 3, 4)], "out_of_vocabulary"),
            ("학교에서", [Morpheme("학교", "NNG", 0, 2), Morpheme("에서", "JKB", 2, 4)], "unsupported_particle"),
            ("책을도", [Morpheme("책", "NNG", 0, 1), Morpheme("을", "JKO", 1, 2), Morpheme("도", "JX", 2, 3)], "unsupported_particle"),
            ("학교가", [Morpheme("학교", "NNG", 0, 2, typo_cost=1), Morpheme("가", "JKS", 2, 3)], "spelling_correction"),
        ]
        for word, morphs, reason in cases:
            with self.subTest(word=word):
                result = canonicalize(word, morphs)
                self.assertEqual((result["canonical"], result["rule"]), (word, reason))

    def test_derivation_and_independent_adverb(self):
        morphs = [Morpheme("공부", "NNG", 0, 2), Morpheme("하", "XSV", 2, 3),
                  Morpheme("었", "EP", 2, 3), Morpheme("다", "EF", 3, 4)]
        self.assertEqual(canonicalize("공부했다", morphs)["canonical"], "공부하다")
        result = canonicalize("조용히", [Morpheme("조용", "XR", 0, 2), Morpheme("히", "XSM", 2, 3)])
        self.assertEqual((result["canonical"], result["pos"]), ("조용히", "ADVERB"))

    def test_ambiguous_l_deletion(self):
        result = canonicalize("나는", [Morpheme("나", "VV", 0, 1), Morpheme("는", "ETM", 1, 2)])
        self.assertEqual(result["rule"], "ambiguous_l_deletion")

    def test_no_context_loss_and_version_fingerprint(self):
        morphs = [Morpheme("책", "NNG", 0, 1), Morpheme("책", "NNG", 2, 3)]
        backend = Backend([(morphs, -1)])
        a = KoreanAnalyzer(backend=backend)
        result = a.analyze("책 책")
        self.assertEqual(backend.calls, ["책 책"])
        self.assertEqual([t["canonical"] for t in result["tokens"]], ["책", "책"])
        self.assertNotIn("redis_fields", result)
        self.assertNotEqual(a.analysis_version, KoreanAnalyzer(backend=backend, ambiguity_margin=1).analysis_version)
        json.dumps(result, allow_nan=False)


class SnowballContractTests(unittest.TestCase):
    def stem(self, words, language="korean"):
        result = subprocess.run([str(ROOT / "stemwords"), "-l", language],
                                input="\n".join(words) + "\n", text=True, encoding="utf-8",
                                capture_output=True, check=True)
        return result.stdout.splitlines()

    def test_aliases_and_golden_words(self):
        data = ROOT / "tests/korean/data/korean"
        words = (data / "voc.txt").read_text(encoding="utf-8").splitlines()
        expected = (data / "output.txt").read_text(encoding="utf-8").splitlines()
        for language in ["korean", "ko", "kor"]:
            self.assertEqual(self.stem(words, language), expected)

    def test_fixed_points_and_no_partial_mutation(self):
        data = ROOT / "tests/korean/data/korean"
        words = (data / "output.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(self.stem(words), words)
        untouched = ["", "123", "😀", "abc먹었다", "먹었다xyz", "학생이 학생이", "고양이", "학교를도"]
        self.assertEqual(self.stem(untouched), untouched)


if __name__ == "__main__":
    unittest.main()
