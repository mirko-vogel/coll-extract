# coding=utf-8
"""
Created on Mar 13, 2018

@author: mirko
"""
from CollocationExtractor import CollocationExtractor


class AdjectiveExtractor(CollocationExtractor):
    @property
    def pattern(self):
        return ["NOUN", "adj"]

    @property
    def candidate_query_template(self):
        return '[lempos="%s\\+NOUN"] [pos="ADJ"]'

    @property
    def example_by_lemma_query_template(self):
        return '[lempos="%s\\+NOUN"] [lempos="%s\\+ADJ"]'


class MudafExtractor(CollocationExtractor):
    @property
    def pattern(self):
        return ["NOUN", "noun"]

    @property
    def candidate_query_template(self):
        return '[lempos="%s\\+NOUN"] [pos="NOUN"]'

    @property
    def example_by_lemma_query_template(self):
        return '[lempos="%s\\+NOUN"] [lempos="%s\\+NOUN"]'

class MudafIlehiExtractor(CollocationExtractor):
    @property
    def pattern(self):
        return ["noun", "NOUN"]

    @property
    def candidate_query_template(self):
        return '[pos="NOUN"] [lempos="%s\\+NOUN"]'

    @property
    def example_by_lemma_query_template(self):
        return '[lempos="%s\\+NOUN"] [lempos="%s\\+NOUN"]'


class VerbForSubjectExtractor(CollocationExtractor):
    @property
    def pattern(self):
        return ["NOUN", "*", "v"]

    @property
    def candidate_query_template(self):
        return '[lempos="%s\\+NOUN"] [ pos!="V" ]{0,} [pos="V"] within < s/>'

    @property
    def example_by_lemma_query_template(self):
        return '[lempos="%s\\+NOUN"] [ pos!="V" ]{0,} [lempos="%s\\+V"] within < s/>'


class VerbForObjectExtractor(CollocationExtractor):
    @property
    def pattern(self):
        return ["v", "*", "NOUN"]

    @property
    def candidate_query_template(self):
        return '[pos="V"] [ pos!="V" ]{0,} [lempos="%s\\+NOUN"] within < s/>'

    @property
    def example_by_lemma_query_template(self):
        return '[lempos="%s\\+V"] [ pos!="V" ]{0,} [lempos="%s\\+NOUN"] within < s/>'


if __name__ == "__main__":
    path = "/home/mirko/Projects/arabic_corpora/manatee_corpora/registry/lcc"
    e = AdjectiveExtractor(path, u"حرب")
    cc = e.fetch_candidates()
    lempos_freqs = dict((lempos, sum(freqs.itervalues())) for lempos, freqs in cc.iteritems())
    top_3 = sorted(lempos_freqs.iteritems(), key=lambda x:x[1], reverse=True)[:3]
    for lempos, freq in top_3:
        words = [lp.partition("+")[0] for lp in lempos.split(" ")]
        ex = e.get_examples(words, n=1)[0]
        print freq, lempos, u" ".join(ex["word"])