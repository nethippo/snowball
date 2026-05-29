# Generated from korean.sbl by Snowball 3.1.0 - https://snowballstem.org/

from .basestemmer import BaseStemmer
from .among import Among


class KoreanStemmer(BaseStemmer):
    '''
    This class implements the stemming algorithm defined by a snowball script.
    Generated from korean.sbl by Snowball 3.1.0 - https://snowballstem.org/
    '''


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

    a_0 = [
        Among("\uC5D0\uAC8C", -1, 1),
        Among("\uBD80\uD130", -1, 1),
        Among("\uAE4C\uC9C0", -1, 1),
        Among("\uC5D0\uC11C", -1, 1),
        Among("\uC5D0\uC11C\uC11C", -1, 1),
        Among("\uD558\uACE0", -1, 1),
        Among("\uACFC", -1, 1),
        Among("\uB098", -1, 1),
        Among("\uAC00", -1, 1),
        Among("\uB97C", -1, 1),
        Among("\uB3C4", -1, 1),
        Among("\uB85C", -1, 1),
        Among("\uC758", -1, 1),
        Among("\uC744", -1, 1),
        Among("\uC640", -1, 1),
        Among("\uB9CC", -1, 1),
        Among("\uCC98\uB7FC", -1, 1),
        Among("\uC870\uCC28", -1, 1),
        Among("\uC73C\uB85C\uBD80\uD130", -1, 1),
        Among("\uD55C\uD14C", -1, 1),
        Among("\uB77C\uB3C4", -1, 1),
        Among("\uB300\uB85C", -1, 1),
        Among("\uC5D0", -1, 1),
        Among("\uB9C8\uC800", -1, 1)
    ]

    a_1 = [
        Among("\uC2B5\uB2C8\uB2E4", -1, 1),
        Among("\uC544\uC694", -1, 1),
        Among("\uC5B4\uC694", -1, 1),
        Among("\uB2E4", -1, 1),
        Among("\uACE0", -1, 1),
        Among("\uB2C8", -1, 1),
        Among("\uC790", -1, 1),
        Among("\uB77C", -1, 1),
        Among("\uC138\uC694", -1, 1),
        Among("\uC5C8\uC5B4\uC694", -1, 1),
        Among("\uC558\uC5B4\uC694", -1, 1),
        Among("\uACA0\uC5B4\uC694", -1, 1),
        Among("\uC5C8", -1, 1),
        Among("\uC558", -1, 1),
        Among("\uC600", -1, 1),
        Among("\uC73C", -1, 1),
        Among("\uB108", -1, 1),
        Among("\uAE30", -1, 1),
        Among("\uAC8C", -1, 1),
        Among("\uB9CC", -1, 1),
        Among("\uC9C0", -1, 1)
    ]
