# Generated from korean.sbl by Snowball 3.1.0 - https://snowballstem.org/
#
# UTF-8 encoding fix: Among tables sorted by reversed string for correct
# binary search in find_among_b (backward processing).
#
# All entries use precomposed Hangul (NFC) to match Python string comparison.
# Unicode values verified against Python chr()/ord().

from .basestemmer import BaseStemmer
from .among import Among


class KoreanStemmer(BaseStemmer):
    """
    Korean stemmer generated from korean.sbl.
    
    UTF-8 encoding fix:
    - Among tables sorted by reversed string for correct backward binary search
    - All entries use precomposed Hangul (NFC) to match Python string comparison
    - Unicode values verified: \uAC8C for 게 (not \uAC8E which is 겎)
    - Unicode values verified: \uC5D0\uC11C\uC5D0\uC11C for 에서에서
    - Unicode values verified: \uCC28\uB9C8 for 차마
    """

    def __r_remove_nominal_suffixes(self):
        self.limit_backward = self.cursor
        self.cursor = self.limit
        self.ket = self.cursor
        if self.find_among_b(KoreanStemmer.a_0) == 0:
            return False
        self.bra = self.cursor
        self.slice_del()
        self.cursor = self.limit_backward
        return True

    def __r_remove_verbal_suffixes(self):
        self.limit_backward = self.cursor
        self.cursor = self.limit
        self.ket = self.cursor
        if self.find_among_b(KoreanStemmer.a_1) == 0:
            return False
        self.bra = self.cursor
        self.slice_del()
        self.cursor = self.limit_backward
        return True

    def _stem(self):
        v_1 = self.cursor
        self.__r_remove_nominal_suffixes()
        self.cursor = v_1
        v_2 = self.cursor
        self.__r_remove_verbal_suffixes()
        self.cursor = v_2
        return True

    # Among tables for nominal suffixes (격 조사) - SORTED BY REVERSED STRING
    a_0 = [
        Among("가", -1, 1),    # 가
        Among("에게", -1, 1),    # 에게
        Among("하고", -1, 1),    # 하고
        Among("과", -1, 1),    # 과
        Among("나", -1, 1),    # 나
        Among("도", -1, 1),    # 도
        Among("라도", -1, 1),    # 라도
        Among("처럼", -1, 1),    # 처럼
        Among("로", -1, 1),    # 로
        Among("대로", -1, 1),    # 대로
        Among("를", -1, 1),    # 를
        Among("차마", -1, 1),    # 차마
        Among("만", -1, 1),    # 만
        Among("에서", -1, 1),    # 에서
        Among("에서에서", -1, 1),    # 에서에서
        Among("에", -1, 1),    # 에
        Among("와", -1, 1),    # 와
        Among("을", -1, 1),    # 을
        Among("의", -1, 1),    # 의
        Among("마저", -1, 1),    # 마저
        Among("까지", -1, 1),    # 까지
        Among("부터", -1, 1),    # 부터
        Among("으로부터", -1, 1),    # 으로부터
        Among("한테", -1, 1),    # 한테
    ]

    # Among tables for verbal suffixes (용언 어미) - SORTED BY REVERSED STRING
    a_1 = [
        Among("게", -1, 1),    # 게
        Among("고", -1, 1),    # 고
        Among("기", -1, 1),    # 기
        Among("너", -1, 1),    # 너
        Among("니", -1, 1),    # 니
        Among("다", -1, 1),    # 다
        Among("습니다", -1, 1),    # 습니다
        Among("라", -1, 1),    # 라
        Among("만", -1, 1),    # 만
        Among("았", -1, 1),    # 았
        Among("었", -1, 1),    # 었
        Among("였", -1, 1),    # 였
        Among("세요", -1, 1),    # 세요
        Among("아요", -1, 1),    # 아요
        Among("어요", -1, 1),    # 어요
        Among("겠어요", -1, 1),    # 겠어요
        Among("았어요", -1, 1),    # 았어요
        Among("었어요", -1, 1),    # 었어요
        Among("자", -1, 1),    # 자
        Among("지", -1, 1),    # 지
    ]
