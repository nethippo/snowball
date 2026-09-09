"""Required real-engine tests for the optional adapter (no mock/skip fallback)."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "examples/korean"))
from korean_analyzer import KoreanAnalyzer, KiwiBackend


class KiwiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = KoreanAnalyzer()

    def words(self, text):
        return [t["canonical"] for t in self.analyzer.analyze(text)["tokens"]]

    def test_golden_sentences(self):
        cases = [
            ("학생이 사과를 먹었다.", ["학생", "사과", "먹다"]),
            ("한국어를 공부했다.", ["한국어", "공부하다"]),
            ("내가 책을 읽었다.", ["나", "책", "읽다"]),
            ("제가 책을 읽었다.", ["저", "책", "읽다"]),
            ("네가 책을 줬다.", ["너", "책", "주다"]),
            ("누가 사과를 먹었다.", ["누구", "사과", "먹다"]),
            ("우리가 한국어를 공부했다.", ["우리", "한국어", "공부하다"]),
            ("길을 걸었다. 전화를 걸었다.", ["길", "걷다", "전화", "걸다"]),
            ("소리를 들었다. 짐을 들었다.", ["소리", "듣다", "짐", "들다"]),
            ("빠르게 달렸다.", ["빠르다", "달리다"]),
            ("빨리 매우 조용히 함께", ["빨리", "매우", "조용히", "함께"]),
            ("고양이 국가 사과 마을", ["고양이", "국가", "사과", "마을"]),
            ("학교에서 책만 읽었다.", ["학교에서", "책만", "읽다"]),
            ("나는 책을 읽었다.", ["나는", "책", "읽다"]),
            ("꽃이 예뻤다.", ["꽃", "예쁘다"]),
            ("학생이 친구를 도왔다.", ["학생", "친구", "돕다"]),
            ("내가 몰랐다.", ["나", "모르다"]),
            ("학생이，사과를/먹었다.", ["학생", "사과", "먹다"]),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(self.words(text), expected)

    def test_nfd_roundtrip_and_contraction_positions(self):
        text = unicodedata.normalize("NFD", "내가 한국어를 공부했다.")
        result = self.analyzer.analyze(text.encode())
        self.assertEqual([t["canonical"] for t in result["tokens"]], ["나", "한국어", "공부하다"])
        for t in result["tokens"]:
            self.assertEqual(text.encode()[t["start_byte"]:t["end_byte"]].decode(), t["surface"])
        morphs = result["tokens"][-1]["morphemes"]
        self.assertTrue(any(a["start"] == b["start"] for a, b in zip(morphs, morphs[1:])))

    def test_oov_and_foreign_tokens(self):
        result = self.analyzer.analyze("쀍쀍이가 좋았다. Redis 123 😀 ㅎㅏㄴ")
        first = result["tokens"][0]
        self.assertEqual(first["canonical"], "쀍쀍이가")
        self.assertEqual(first["rule"], "out_of_vocabulary")
        self.assertEqual([t["canonical"] for t in result["tokens"]][-4:], ["Redis", "123", "😀", "ㅎㅏㄴ"])

    def test_user_dictionary_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "dictionary.json"
            p.write_text(json.dumps([{"word": "쀍쀍이", "tag": "NNP"}]), encoding="utf-8")
            analyzer = KoreanAnalyzer(user_dictionary=p)
            self.assertEqual(analyzer.analyze("쀍쀍이가 좋았다.")["tokens"][0]["canonical"], "쀍쀍이")
            self.assertNotEqual(analyzer.analysis_version, self.analyzer.analysis_version)
            p.write_text('[{"word": "bad word", "tag": "NNP"}]')
            with self.assertRaises(ValueError):
                KiwiBackend(p)

    def test_cli_json_and_invalid_utf8(self):
        cli = [sys.executable, str(ROOT / "examples/korean/korean_analyzer.py"), "--words"]
        good = subprocess.run(cli, input="학생이 책을 읽었다.".encode(), capture_output=True, check=True)
        self.assertEqual(json.loads(good.stdout), ["학생", "책", "읽다"])
        bad = subprocess.run(cli, input=b"\xff", capture_output=True)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, b"")


if __name__ == "__main__":
    unittest.main()
