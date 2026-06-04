#!/usr/bin/env python3
"""
한국어 사전 로드 스크립트

kiwipiepy의 내장 사전을 파싱하여 어휘 사전을 구축합니다.
표준국어대사전 API 또는 오픈 데이터셋에서 로드하는 기능도 제공합니다.

사용법:
    python scripts/load_dict.py                    # 기본 사전 로드
    python scripts/load_dict.py --output dict.json  # JSON 파일로 저장
    python scripts/load_dict.py --format pickle     # pickle 형식으로 저장
"""

import json
import os
import sys
import pickle
import time
from pathlib import Path
from typing import Dict, Set, Optional


def find_kiwi_dict_path() -> Optional[str]:
    """kiwipiepy의 default.dict 파일 경로를 찾습니다."""
    try:
        import kiwipiepy
        kiwi_dir = os.path.dirname(kiwipiepy.__file__)
        model_dir = os.path.join(
            os.path.dirname(kiwi_dir),
            "kiwipiepy_model",
            "default.dict"
        )
        if os.path.exists(model_dir):
            return model_dir
    except ImportError:
        pass

    # pip install 경로 확인
    import site
    for site_pkg in site.getsitepackages():
        model_dir = os.path.join(
            site_pkg,
            "kiwipiepy_model",
            "default.dict"
        )
        if os.path.exists(model_dir):
            return model_dir

    return None


def parse_kiwi_dict(dict_path: str) -> Dict[str, str]:
    """
    kiwipiepy의 default.dict 파일을 파싱하여 어휘 사전을 구축합니다.

    반환값:
        Dict[str, str]: word -> lemma 매핑 (word: 형태소, lemma: 원형)
    """
    lemma_map: Dict[str, str] = {}
    word_set: Set[str] = set()

    with open(dict_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()

            # 주석 줄 또는 빈 줄 건너뛰기
            if not line or line.startswith("#"):
                continue

            # 형태소 분석 결과 (예: "랬\t라/EC + 하/VV + 었/EP")
            if "\t" not in line:
                continue

            parts = line.split("\t")
            word = parts[0]

            # 형태소 분석 결과인 경우 (예: "랬\t라/EC + 하/VV + 었/EP")
            if " +" in parts[1]:
                # 각 형태소를 파싱하여 원형 추출
                morphemes = parts[1].split(" + ")
                for morph in morphemes:
                    morph = morph.strip()
                    if "/" in morph:
                        lemma = morph.split("/")[0]
                        if lemma:
                            lemma_map[lemma] = lemma
                            word_set.add(lemma)
                # 전체 단어 тоже 추가
                if word:
                    word_set.add(word)
                continue

            # 단순 형태소 (예: "학교\tNNG\t-5.0")
            if len(parts) >= 2:
                pos_tag = parts[1].strip()
                # 품사 태그 확인 (NNP, NNG, VV, VA, MAG, etc.)
                # 명사(NN*), 용언(VV, VA, VX, MAG, MAG), 부사(MAG, MJC), 형용사(VA) 등
                if pos_tag.startswith("NN"):
                    # 명사: word를 lemma로 사용
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("VV"):
                    # 동사: word를 lemma로 사용
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("VA"):
                    # 형용사: word를 lemma로 사용
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("VX"):
                    # 보조 용언: word를 lemma로 사용
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("MAG"):
                    # 부사: word를 lemma로 사용
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("EC"):
                    # 접미사: 추가 (접미사도 원형으로 사용)
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("EP"):
                    # 어미: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("EF"):
                    # 종결 어미: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("JX"):
                    # 보조사: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("JK"):
                    # 조사: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("SL"):
                    # 외래어: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("SW"):
                    # 심의어: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("XSN"):
                    # 파생명사: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("XSA"):
                            # 파생형용사: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("XSV"):
                            # 파생동사: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)
                elif pos_tag.startswith("VV"):
                            # 동사: 추가
                    if word:
                        lemma_map[word] = word
                        word_set.add(word)

    return lemma_map


def load_kiwi_dict() -> Dict[str, str]:
    """kiwipiepy의 내장 사전을 로드합니다."""
    dict_path = find_kiwi_dict_path()
    if dict_path is None:
        raise FileNotFoundError(
            "kiwipiepy의 default.dict 파일을 찾을 수 없습니다. "
            "kiwipiepy를 설치해주세요: pip install kiwipiepy"
        )
    print(f"kiwipiepy 사전 로드: {dict_path}")
    return parse_kiwi_dict(dict_path)


def load_builtin_dict() -> Dict[str, str]:
    """
    내장 사전 (소규모 테스트용)을 로드합니다.
    """
    # 테스트를 위한 기본 사전
    builtin = {
        # 명사
        "학교": "학교", "학생": "학생", "사람": "사람", "책": "책",
        "친구": "친구", "가족": "가족", "일": "일", "시간": "시간",
        "물건": "물건", "의사": "의사", "선생님": "선생님",
        "학교": "학교", "책": "책", "사람": "사람",
        # 동사
        "먹다": "먹다", "가다": "가다", "오다": "오다", "하다": "하다",
        "보다": "보다", "듣다": "듣다", "걷다": "걷다", "짓다": "짓다",
        "놀다": "놀다", "돕다": "돕다", "받다": "받다", "웃다": "웃다",
        "붓다": "붓다", "낫다": "낫다", "믿다": "믿다", "갚다": "갚다",
        # 형용사
        "크다": "크다", "작다": "작다", "좋다": "좋다", "나쁘다": "나쁘다",
        "빠르다": "빠르다", "느리다": "느리다", "길다": "길다", "짧다": "짧다",
        # 부사
        "매우": "매우", "아주": "아주", "너무": "너무", "조금": "조금",
        "많이": "많이", "적게": "적게", "빨리": "빨리", "천천히": "천천히",
        # 조사
        "에서": "에서", "에": "에", "을": "을", "를": "를",
        "의": "의", "와": "와", "과": "과", "도": "도", "만": "만",
        "부터": "부터", "까지": "까지", "처럼": "처럼", "조차": "조차",
        "라도": "라도", "으로": "으로", "로": "로",
        # 접미사
        "들": "들", "이": "이", "음": "음", "함": "함",
        # 어미
        "습니다": "습니다", "어요": "어요", "다": "다", "고": "고",
        "니": "니", "자": "자", "라": "라", "세요": "세요",
        "었": "었", "았": "았", "었": "었", "겠": "겠",
        "ㅂ니다": "ㅂ니다", "습니다": "습니다",
    }
    return builtin


def save_dict(lemma_map: Dict[str, str], output_path: str, format: str = "json"):
    """사전을 파일로 저장합니다."""
    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(lemma_map, f, ensure_ascii=False, indent=2)
        print(f"JSON 사전 저장: {output_path} ({len(lemma_map)} 단어)")
    elif format == "pickle":
        with open(output_path, "wb") as f:
            pickle.dump(lemma_map, f)
        print(f"Pickle 사전 저장: {output_path} ({len(lemma_map)} 단어)")
    elif format == "set":
        with open(output_path, "w", encoding="utf-8") as f:
            for word in sorted(lemma_map.keys()):
                f.write(word + "\n")
        print(f"단어 목록 저장: {output_path} ({len(lemma_map)} 단어)")
    else:
        raise ValueError(f"지원하지 않는 형식: {format}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="한국어 어휘 사전 로드 스크립트"
    )
    parser.add_argument(
        "--source",
        choices=["kiwi", "builtin"],
        default="kiwi",
        help="사전 소스 (기본: kiwi)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 파일 경로 (기본: stdout에 통계 출력)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "pickle", "set"],
        default="json",
        help="출력 형식 (기본: json)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="사전 통계 출력",
    )

    args = parser.parse_args()

    # 사전 로드
    start_time = time.time()
    if args.source == "kiwi":
        lemma_map = load_kiwi_dict()
    else:
        lemma_map = load_builtin_dict()
    load_time = time.time() - start_time

    # 통계 출력
    if args.stats:
        print(f"\n=== 사전 통계 ===")
        print(f"총 단어 수: {len(lemma_map)}")
        print(f"로딩 시간: {load_time:.3f}초")

        # 품사별 분포
        pos_counts = {}
        with open(find_kiwi_dict_path() or "", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "\t" not in line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    pos = parts[1].strip()
                    if pos not in pos_counts:
                        pos_counts[pos] = 0
                    pos_counts[pos] += 1

        print(f"\n품사별 분포 (상위 20개):")
        for pos, count in sorted(pos_counts.items(), key=lambda x: -x[1])[:20]:
            print(f"  {pos}: {count}")

        # 샘플 단어 출력
        print(f"\n샘플 단어 (상위 20개):")
        for i, word in enumerate(sorted(lemma_map.keys())[:20]):
            print(f"  {i+1}. {word}")

    # 파일로 저장
    if args.output:
        save_dict(lemma_map, args.output, args.format)


if __name__ == "__main__":
    main()
