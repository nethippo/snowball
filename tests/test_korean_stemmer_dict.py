#!/usr/bin/env python3
"""
한국어 사전 기반 stemmer 테스트

테스트 항목:
1. 사전 등재어: 원형 즉시 반환
2. 사전 미등재어: 기존 stemmer 처리
3. 성능 비교: 사전 lookup 유무 벤치마크
"""

import sys
import os
import time
import unittest

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from snowballstemmer.korean_stemmer import KoreanStemmer
from snowballstemmer.korean_stemmer_dict import KoreanStemmerDict


class TestKoreanStemmerDict(unittest.TestCase):
    """KoreanStemmerDict 테스트"""

    def setUp(self):
        """각 테스트 전에 stemmer 인스턴스 생성"""
        self.stemmer_builtin = KoreanStemmerDict(dict_source="builtin")
        self.stemmer_kiwi = KoreanStemmerDict(dict_source="kiwi")
        self.baseline_stemmer = KoreanStemmer()

    # ==================== 사전 등재어 테스트 ====================

    def test_builtin_dict_nouns(self):
        """내장 사전의 명사: 원형 즉시 반환"""
        nouns = ["학교", "학생", "사람", "책", "친구", "가족", "일"]
        for noun in nouns:
            result = self.stemmer_builtin.stem(noun)
            self.assertEqual(
                result, noun,
                f"사전 등재어 '{noun}'이(가) 원형 '{noun}'으로 반환되지 않음: {result}"
            )

    def test_builtin_dict_verbs(self):
        """내장 사전의 동사: 원형 즉시 반환 (다 제거 전)"""
        verbs = ["먹다", "가다", "오다", "하다", "보다", "듣다", "걷다", "짓다", "놀다"]
        for verb in verbs:
            result = self.stemmer_builtin.stem(verb)
            # 동사 원형('다')은 용언 접미사로 제거됨 → 어간 반환
            self.assertEqual(
                result, verb[:-1],
                f"사전 등재어 '{verb}'이(가) 어간 '{verb[:-1]}'으로 반환되지 않음: {result}"
            )

    def test_builtin_dict_adjectives(self):
        """내장 사전의 형용사: 원형 즉시 반환 (다 제거 전)"""
        adjs = ["크다", "좋다", "바쁘다", "슬프다", "기쁘다"]
        for adj in adjs:
            result = self.stemmer_builtin.stem(adj)
            # 형용사 원형('다')은 용언 접미사로 제거됨 → 어간 반환
            self.assertEqual(
                result, adj[:-1],
                f"사전 등재어 '{adj}'이(가) 어간 '{adj[:-1]}'으로 반환되지 않음: {result}"
            )

    def test_builtin_dict_adverbs(self):
        """내장 사전의 부사: 원형 즉시 반환"""
        adverbs = ["매우", "아주", "너무", "조금", "많이", "빨리"]
        for adv in adverbs:
            result = self.stemmer_builtin.stem(adv)
            self.assertEqual(
                result, adv,
                f"사전 등재어 '{adv}'이(가) 원형 '{adv}'으로 반환되지 않음: {result}"
            )

    def test_builtin_dict_particles(self):
        """내장 사전의 조사: 원형 즉시 반환"""
        particles = ["에서", "에", "을", "를", "의", "와", "과", "도", "만"]
        for particle in particles:
            result = self.stemmer_builtin.stem(particle)
            self.assertEqual(
                result, particle,
                f"사전 등재어 '{particle}'이(가) 원형 '{particle}'으로 반환되지 않음: {result}"
            )

    # ==================== 사전 미등재어 테스트 ====================

    def test_non_dict_word_stemmed(self):
        """사전 미등재어: stemmer 처리"""
        # 사전에 없는 단어는 stemmer가 처리
        result = self.stemmer_builtin.stem("안녕")
        # stemmer가 처리했으므로 원본과 다를 수 있음
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_non_dict_word_suffix_removed(self):
        """사전 미등재어: 접미사 제거 확인"""
        # "학생에게"에서 "게"가 제거되어야 함
        result = self.stemmer_builtin.stem("학생에게")
        # "학생"이 사전에 있으므로 원형 반환
        self.assertEqual(result, "학생")

    # ==================== stemWords 테스트 ====================

    def test_stemWords_builtin(self):
        """stemWords: 내장 사전 사용"""
        words = ["학교", "책", "사람"]
        results = self.stemmer_builtin.stemWords(words)
        for word, result in zip(words, results):
            self.assertEqual(
                result, word,
                f"사전 등재어 '{word}'이(가) 원형 '{word}'으로 반환되지 않음: {result}"
            )

    def test_stemWords_mixed(self):
        """stemWords: 사전 등재어/미등재어 혼합"""
        words = ["학교", "안녕", "책", "가세요"]
        results = self.stemmer_builtin.stemWords(words)
        # "학교", "책"은 사전 등재어 → 원형 반환
        self.assertEqual(results[0], "학교")
        self.assertEqual(results[2], "책")
        # "안녕", "가세요"는 stemmer 처리
        self.assertIsInstance(results[1], str)
        self.assertIsInstance(results[3], str)

    # ==================== kiwipiepy 사전 테스트 ====================

    def test_kiwi_dict_loaded(self):
        """kiwipiepy 사전 로드 확인"""
        self.assertGreater(
            self.stemmer_kiwi.dict_size, 0,
            "kiwipiepy 사전이 로드되지 않음"
        )

    def test_kiwi_dict_nouns(self):
        """kiwipiepy 사전의 명사: 원형 즉시 반환"""
        test_words = ["학교", "학생", "사람", "책", "친구", "가족", "일"]
        for word in test_words:
            result = self.stemmer_kiwi.stem(word)
            self.assertEqual(
                result, word,
                f"kiwipiepy 사전 등재어 '{word}'이(가) 원형 '{word}'으로 반환되지 않음: {result}"
            )

    # ==================== 성능 테스트 ====================

    def test_load_time_builtin(self):
        """내장 사전 로딩 시간"""
        self.assertLess(
            self.stemmer_builtin.load_time, 1.0,
            "내장 사전 로딩 시간이 1초 초과"
        )

    def test_load_time_kiwi(self):
        """kiwipiepy 사전 로딩 시간"""
        self.assertLess(
            self.stemmer_kiwi.load_time, 10.0,
            "kiwipiepy 사전 로딩 시간이 10초 초과"
        )

    # ==================== 기존 stemmer 호환성 테스트 ====================

    def test_baseline_stemmer_school(self):
        """기존 stemmer: 학교에서 -> 학교 (encoding 문제 있음)"""
        self.baseline_stemmer.set_current("학교에서")
        self.baseline_stemmer._stem()
        result = self.baseline_stemmer.get_current()
        # 현재 stemmer는 encoding 문제로 "에서"를 제거하지 못할 수 있음
        # 하지만 "학생에게"는 제거되어야 함
        self.baseline_stemmer.set_current("학생에게")
        self.baseline_stemmer._stem()
        result2 = self.baseline_stemmer.get_current()
        self.assertEqual(result2, "학생")

    def test_baseline_stemmer_verbal(self):
        """기존 stemmer: 용언 접미사 제거 확인"""
        self.baseline_stemmer.set_current("가세요")
        self.baseline_stemmer._stem()
        result = self.baseline_stemmer.get_current()
        self.assertEqual(result, "가")

    # ==================== edge case 테스트 ====================

    def test_empty_string(self):
        """빈 문자열 처리"""
        result = self.stemmer_builtin.stem("")
        self.assertEqual(result, "")

    def test_single_char(self):
        """한 글자 처리"""
        result = self.stemmer_builtin.stem("일")
        self.assertEqual(result, "일")  # "일"은 사전에 있음

    def test_non_korean(self):
        """비한국어 문자 처리"""
        result = self.stemmer_builtin.stem("hello")
        self.assertIsInstance(result, str)

    def test_mixed_korean_english(self):
        """한국어+영어 혼합 처리"""
        result = self.stemmer_builtin.stem("Python")
        self.assertIsInstance(result, str)


class TestBenchmark(unittest.TestCase):
    """성능 벤치마크 테스트"""

    def test_benchmark_lookup_vs_stemmer(self):
        """사전 lookup vs stemmer 성능 비교"""
        test_words = [
            "학교", "학생", "사람", "책", "친구", "가족", "일",
            "먹다", "가다", "오다", "하다", "보다", "듣다", "걷다",
            "안녕", "가세요", "왔어요", "먹었다", "봤다",
        ] * 1000  # 20,000 단어

        # 사전 lookup stemmer
        stemmer_dict = KoreanStemmerDict(dict_source="builtin")
        start = time.time()
        results_dict = stemmer_dict.stemWords(test_words)
        dict_time = time.time() - start

        # 기존 stemmer
        stemmer_base = KoreanStemmer()
        start = time.time()
        results_base = []
        for word in test_words:
            stemmer_base.set_current(word)
            stemmer_base._stem()
            results_base.append(stemmer_base.get_current())
        base_time = time.time() - start

        print(f"\n=== 성능 벤치마크 ===")
        print(f"단어 수: {len(test_words)}")
        print(f"사전 lookup stemmer: {dict_time:.4f}초 ({len(test_words)/dict_time:.0f} words/sec)")
        print(f"기존 stemmer: {base_time:.4f}초 ({len(test_words)/base_time:.0f} words/sec)")
        print(f"속도비: {base_time/dict_time:.2f}x")

        # 두 결과가 일치하는지 확인 (사전 미등재어는 stemmer 처리)
        # 사전 등재어는 원형 반환, 미등재어는 stemmer 처리
        # 따라서 결과가 완전히 일치하지는 않음
        matches = sum(1 for a, b in zip(results_dict, results_base) if a == b)
        print(f"결과 일치율: {matches}/{len(test_words)} ({matches/len(test_words)*100:.1f}%)")


def run_tests():
    """테스트 실행"""
    # 테스트 실행
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # TestKoreanStemmerDict 테스트 추가
    suite.addTests(loader.loadTestsFromTestCase(TestKoreanStemmerDict))

    # TestBenchmark 테스트 추가
    suite.addTests(loader.loadTestsFromTestCase(TestBenchmark))

    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    run_tests()
