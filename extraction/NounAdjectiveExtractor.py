# coding=utf-8
"""
Created on Mar 13, 2018

@author: mirko
"""
from CollocationExtractor import CollocationExtractor


class NounAdjectiveExtractor(CollocationExtractor):
    """

    """
    def __init__(self, corpus_path, noun_lemma):
        """

        :param noun:
        """
        super(NounAdjectiveExtractor, self).__init__(corpus_path, noun_lemma, "NOUN")

    def fetch_collocation_candidates(self):
        self.conc.sync()
        candidates = self.conc.extract_collocations("lempos", "f", 10, 3, (1, 1), 1000)
        return [c for c in candidates if c[1] == "ADJ"]

    def extract_candidate(self, lemma, pos):
        query = u'[lemma="%s" & pos="%s"]' % (lemma, pos)
        self.conc.filter(query, (1, 1))

    @property
    def pattern(self):
        return "NOUN + ADJ"


if __name__ == "__main__":
    path = "/home/mirko/Projects/arabic_corpora/manatee_corpora/registry/lcc"
    e = NounAdjectiveExtractor(path, u"حرب")
    candidates = e.fetch_collocation_candidates()
    print u"، ".join(c[0] for c in candidates)