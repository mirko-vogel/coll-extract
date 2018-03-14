# coding=utf-8
'''
Created on Mar 13, 2018

@author: mirko
'''

import manatee
from collections import defaultdict
from itertools import izip

import operator

from Concordance import Concordance

"""
To put it down...

A collocation in a pos-tagged, lemmazized corpus is given by
1) a pos pattern with holes
(noun patterns only, currently)
A. NOUN adj
B. NOUN * verb
C. verb * NOUN
D. NOUN noun
E. noun NOUN
F. verb * prep NOUN 

These patterns translate into a query
A. [lemma="%s" & pos="N"] [pos="ADJ"] {"lemma"} 
B. [lemma="NOUN" & pos="N"] []{0,} [pos="V"] 
...

The result of the search then needs to be parsed ...

DAS DAUERT ZU LANGE!

2) constraints


Pattern Extractor
> build query
> for every kwic_line (kw only)
>   extract candidate (drop in-between tokens)
>   instances[candidate.lempos][candidate.word-pos] +=1 (add examples?) 
> filter candidates (candidate.word-pos)

"""


class MalformedPatternException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg.encode("utf-8"))


class CollocationExtractor(object):
    """
    Base class for all collocation extractors. Extracts collocations for a given
    core (lemma and pos) and a given pattern.
    """

    def __init__(self, corpus_path, lemma, pos):
        """
        Constructs a ColllocationExtractor
        """

        self.corpus = manatee.Corpus(corpus_path)
        self.lemma, self.pos = lemma, pos

        # query = u'[lempos="%s+%s"]' % (core_lemma, core_pos) -- DOES NOT WORK
        #query = u'[lemma="%s" & pos="%s"]' % (self.lemma, self.pos)
        #self.conc = Concordance(self.corpus, query.encode("utf-8"), 1000000, -1)  # Returns immediately


    def extract_candidates(self, extract_inflected_forms, extract_examples):
        """
        Extracts candidates

        :param extract_inflected_forms:
        :param extract_examples:
        :return:
        """
        raw_candidates = self.fetch_collocation_candidates()
        candidates = []
        for (lemma, pos, freq, score) in raw_candidates:
            c = self.extract_candidate(lemma, pos)
            if c:
                candidates.append(c)
        return candidates

    def extract_candidate(self, lemma, pos):
        """
        Extracts a candidate, possibly returning Null

        :param lemma:
        :param pos:
        :return:

        """
        raise NotImplementedError

    @property
    def pattern(self):
        """
        e.g. [u"V", u"*", u"noun"]

        :rtype: list[unicode]
        """
        raise NotImplementedError

    def build_qcl_query(self):
        """
        Returns a QCL-query for self.pattern

        :rtype: unicode

        """
        q = []
        for p in self.pattern:
            # Either core, e.g. "NOUN"
            if p.isupper():
                if p != self.pos:
                    raise MalformedPatternException("Pattern requires a '%s' core, but we have '%s'."
                                                    % (p, self.pos))
                q.append(u'[lemma="%s" & pos="%s"]' % (self.lemma, p))
            # or collocator, e.g. "ajg"
            elif p.islower():
                q.append(u'[pos="%s"]' % p.upper())
            elif p == "*":
                q.append(u'[ ]{0,}') # TODO: exclude pos tags
            else:
                raise MalformedPatternException(u"Not knowing how to interpret '%s'" % p)

        q.append(u"within < s/>")
        return u" ".join(q)

    def extract_candidate_tokens(self, toks):
        """
        Removes tokens matched by * in pattern
        """
        try:
            idx = self.pattern.index(u"*")
        except ValueError:
            return toks

        l = len(self.pattern) - idx - 1
        return toks[:idx] + toks[-l:]



    def get_candidates(self):
        """

        :return:
        """
        c = Concordance(self.corpus, self.build_qcl_query(), 1000000, -1)
        c.sync()
        attr = ["word", "pos", "lemma", "fullpos"]
        lines = c.get_kwic_lines((1, c.size()), (0, 0),  attr, ["s"])

        instances = defaultdict(lambda: defaultdict(int))
        for l in lines:
            for a in attr:
                l[a] = self.extract_candidate_tokens(l[a])
            coll_wordpos = u" ".join(u"%s+%s" % (w, p) for w,p in izip(l["word"], l["fullpos"]))
            coll_lempos = u" ".join(u"%s+%s" % (w, p) for w, p in izip(l["lemma"], l["pos"]))
            instances[coll_lempos][coll_wordpos] += 1

        # TODO: filter instances
        return instances

class SimplePatternExtractor(CollocationExtractor):
    def __init__(self, corpus_path, lemma, pos, pattern):
        self._pattern = pattern
        super(SimplePatternExtractor, self).__init__(corpus_path, lemma, pos)

    @property
    def pattern(self):
        return self._pattern

PATTERNS = [["NOUN", "*", "v"], ["v", "*", "NOUN"], ["v", "*", "prep", "NOUN"],
            ["NOUN", "adj"], ["NOUN", "noun"], ["noun", "NOUN"]]

if __name__ == "__main__":
    path = "/home/mirko/Projects/arabic_corpora/manatee_corpora/registry/lcc"
    for p in PATTERNS:
        print "-------------------------------------\n%s" % p
        e = SimplePatternExtractor(path, u"اتفاقية", "NOUN", p)
        cc = e.get_candidates()
        lempos_freqs = dict((lempos, sum(freqs.itervalues())) for lempos, freqs in cc.iteritems())
        top_10 = sorted(lempos_freqs.iteritems(), key=operator.itemgetter(1), reverse=True)[:10]
        for lempos, freq in top_10:
            print freq, lempos
