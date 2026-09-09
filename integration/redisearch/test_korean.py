"""RLTest coverage for the integrated, deliberately limited Korean stemmer."""
from common import waitForIndex


def testKoreanLanguage(env):
    env.expect('FT.CREATE', 'ko', 'LANGUAGE', 'korean', 'STOPWORDS', 0,
               'SCHEMA', 'body', 'TEXT').ok()
    env.cmd('HSET', 'doc:1', 'body', '학생이 사과를 먹었다.')
    waitForIndex(env, 'ko')
    env.expect('FT.SEARCH', 'ko', '학생 사과 먹다', 'NOCONTENT',
               'DIALECT', 2).equal([1, 'doc:1'])
    env.expect('FT.SEARCH', 'ko', '학생이 사과를 먹었다', 'NOCONTENT',
               'LANGUAGE', 'KOREAN', 'DIALECT', 2).equal([1, 'doc:1'])
    env.expect('FT.SEARCH', 'ko', '학생 사과 먹다', 'VERBATIM',
               'NOCONTENT', 'DIALECT', 2).equal([0])
    env.expect('FT.SEARCH', 'ko', '먹다', 'RETURN', 1, 'body',
               'DIALECT', 2).equal([1, 'doc:1', ['body', '학생이 사과를 먹었다.']])
    env.expect('FT.SEARCH', 'ko', '먹다', 'LANGUAGE', 'ko').error()
    env.cmd('HSET', 'doc:2', 'body', '내가 길을 걸었다.')
    waitForIndex(env, 'ko')
    env.expect('FT.SEARCH', 'ko', '걷다', 'NOCONTENT', 'DIALECT', 2).equal([0])
    env.expect('FT.SEARCH', 'ko', '걸었다', 'NOCONTENT', 'DIALECT', 2).equal([1, 'doc:2'])
    for _ in env.reloadingIterator():
        env.expect('FT.SEARCH', 'ko', '학생 사과 먹다', 'NOCONTENT',
                   'DIALECT', 2).equal([1, 'doc:1'])
