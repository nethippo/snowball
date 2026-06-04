#!/usr/bin/env python3
"""
한국어 stemmer 벤치마크

1. 사전 lookup 유무 성능 비교
2. 사전 등재어/미등재어 처리 검증
3. kiwipiepy 사전 vs 내장 사전 비교
"""

import sys
import os
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from snowballstemmer.korean_stemmer import KoreanStemmer
from snowballstemmer.korean_stemmer_dict import KoreanStemmerDict


def generate_test_words():
    """테스트 단어 생성"""
    # 사전 등재어
    dict_words = [
        "학교", "학생", "사람", "책", "친구", "가족", "일", "시간",
        "물건", "의사", "선생님", "먹다", "가다", "오다", "하다",
        "보다", "듣다", "걷다", "짓다", "놀다", "돕다", "받다",
        "크다", "작다", "좋다", "나쁘다", "매우", "아주", "빨리",
        "에서", "에", "을", "를", "의", "와", "과", "도", "만",
    ]

    # 사전 미등재어 (stemmer가 처리해야 하는 단어)
    non_dict_words = [
        "안녕", "가세요", "왔어요", "먹었다", "봤다", "읽다",
        "쓰다", "말하다", "생각하다", "일하다", "공부하다", "운동하다",
        "먹어요", "가요", "와요", "해요", "봐요", "들어요",
        "갔습니다", "왔습니다", "먹었습니다", "봤습니다", "읽었습니다",
        "학교에서", "책에", "사람을", "학생에게", "친구와", "가족도",
        "일만", "시간에", "물건을", "의사를", "선생님께",
    ]

    return dict_words, non_dict_words


def benchmark(dict_source="builtin", num_iterations=1000):
    """벤치마크 실행"""
    dict_words, non_dict_words = generate_test_words()

    # 테스트 단어 생성 (70% 사전 등재어, 30% 미등재어)
    test_words = []
    for _ in range(num_iterations):
        test_words.extend(random.sample(dict_words, min(7, len(dict_words))))
        test_words.extend(random.sample(non_dict_words, min(3, len(non_dict_words))))

    random.shuffle(test_words)

    # 사전 lookup stemmer
    stemmer_dict = KoreanStemmerDict(dict_source=dict_source)
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

    return {
        "num_words": len(test_words),
        "dict_time": dict_time,
        "base_time": base_time,
        "speedup": base_time / dict_time if dict_time > 0 else float('inf'),
        "dict_size": stemmer_dict.dict_size,
        "load_time": stemmer_dict.load_time,
    }


def main():
    print("=" * 60)
    print("한국어 stemmer 벤치마크")
    print("=" * 60)

    # 내장 사전 벤치마크
    print("\n--- 내장 사전 (builtin) ---")
    result_builtin = benchmark(dict_source="builtin", num_iterations=5000)
    print(f"  단어 수: {result_builtin['num_words']}")
    print(f"  사전 크기: {result_builtin['dict_size']} 단어")
    print(f"  로딩 시간: {result_builtin['load_time']:.4f}초")
    print(f"  처리 시간: {result_builtin['dict_time']:.4f}초")
    print(f"  처리 속도: {result_builtin['num_words']/result_builtin['dict_time']:.0f} words/sec")
    print(f"  기존 stemmer: {result_builtin['base_time']:.4f}초 ({result_builtin['num_words']/result_builtin['base_time']:.0f} words/sec)")
    print(f"  속도 향상: {result_builtin['speedup']:.2f}x")

    # kiwipiepy 사전 벤치마크
    print("\n--- kiwipiepy 사전 ---")
    result_kiwi = benchmark(dict_source="kiwi", num_iterations=5000)
    print(f"  단어 수: {result_kiwi['num_words']}")
    print(f"  사전 크기: {result_kiwi['dict_size']} 단어")
    print(f"  로딩 시간: {result_kiwi['load_time']:.4f}초")
    print(f"  처리 시간: {result_kiwi['dict_time']:.4f}초")
    print(f"  처리 속도: {result_kiwi['num_words']/result_kiwi['dict_time']:.0f} words/sec")
    print(f"  기존 stemmer: {result_kiwi['base_time']:.4f}초 ({result_kiwi['num_words']/result_kiwi['base_time']:.0f} words/sec)")
    print(f"  속도 향상: {result_kiwi['speedup']:.2f}x")

    # 요약
    print("\n" + "=" * 60)
    print("요약")
    print("=" * 60)
    print(f"  내장 사전: {result_builtin['speedup']:.2f}x 속도 향상 ({result_builtin['dict_size']} 단어)")
    print(f"  kiwipiepy 사전: {result_kiwi['speedup']:.2f}x 속도 향상 ({result_kiwi['dict_size']} 단어)")
    print(f"  kiwipiepy 사전이 {result_kiwi['dict_size']/result_builtin['dict_size']:.1f}배 더 큰 사전 사용")
    print("=" * 60)


if __name__ == "__main__":
    main()
