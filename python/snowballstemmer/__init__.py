__all__ = ('language', 'stemmer')

try:
    import Stemmer
    algorithms = Stemmer.algorithms
    stemmer = Stemmer.Stemmer
except ImportError:
    from .korean_stemmer import KoreanStemmer

    _languages = {
        'korean': KoreanStemmer,
    }

    def algorithms():
        return list(_languages.keys())

    def stemmer(lang):
        lang = lang.lower()
        if lang in _languages:
            return _languages[lang]()
        else:
            raise KeyError("Stemming algorithm '%s' not found" % lang)
