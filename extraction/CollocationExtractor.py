# coding=utf-8
"""
Created on Mar 13, 2018

@author: mirko
"""

import manatee
from collections import defaultdict
from itertools import izip

import operator

from Concordance import Concordance

from operator import itemgetter


class MalformedPatternException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg.encode("utf-8"))


class CollocationExtractor(object):
    """
    Base class for all collocation extractors. Extracts collocations for a given
    core (lemma and pos) and a given pattern.
    """

    def __init__(self, corpus_path, lemma):
        """
        Constructs a ColllocationExtractor
        """

        self.corpus = manatee.Corpus(corpus_path)
        self.lemma = lemma
        self.candidates = []

    def extract_candidate_tokens(self, toks):
        """
        Removes tokens matched by * in pattern
        """
        if not self.asterix_pos_in_pattern:
            return toks

        l = len(self.pattern) - self.asterix_pos_in_pattern - 1
        return toks[:self.asterix_pos_in_pattern] + toks[-l:]

    def fetch_candidates(self):
        """
        Fetches collocation candidates using the candidate query template,
        storing them in self.candidates.

        """
        q = self.candidate_query_template % self.lemma
        c = Concordance(self.corpus, q, 1000000, -1)
        c.sync()
        attr = ["word", "pos", "lemma", "fullpos"]
        lines = c.get_kwic_lines((1, c.size()), (0, 0), attr, ["s"])

        instance_counts = defaultdict(lambda: defaultdict(int))
        for l in lines:
            for a in attr:
                l[a] = self.extract_candidate_tokens(l[a])
            coll_wordpos = u" ".join(u"%s+%s" % (w, p) for w, p in izip(l["word"], l["fullpos"]))
            coll_lempos = u" ".join(u"%s+%s" % (w, p) for w, p in izip(l["lemma"], l["pos"]))
            instance_counts[coll_lempos][coll_wordpos] += 1

        self.candidates = sorted((CollocationCandidate(lempos, freqs, self)
                                  for lempos, freqs in instance_counts.iteritems()),
                                 key=lambda c: c.freq, reverse=True)

    def filter_candidates(self, min_freq=0, min_score=0):
        """
        Filters for non-letter characters, frequency, score ...

        :param min_freq:
        :param min_score:
        :return:
        """
        filters = [
            lambda c: c.freq >= min_freq,
            lambda c: set(c.lemma).isdisjoint(u"\"'.,،-()[]{}")
        ]
        all_filters = lambda x: all(f(x) for f in filters)
        self.candidates = filter(all_filters, self.candidates)

    def get_examples(self, n=10):
        """

        :param n:
        :return:
        """
        for c in self.candidates:
            c.examples = self.__get_examples(c.lemma.split(" "), attributes=["word", "pos"], n=n)

    def __get_examples(self, candidate, inflected=False, attributes=["word"], n=10):
        """
        Returns sentences containing the collocation candidate.

        :param candidate: list of surface forms or lemmas
        :param inflected:
        :param attributes:
        :param n:
        :return:
        """

        # Query
        if inflected:
            q = self.example_by_word_query_template % tuple(candidate)
        else:
            q = self.example_by_lemma_query_template % tuple(candidate)

        c = Concordance(self.corpus, q, n, -1)
        c.sync()
        lines = c.get_kwic_lines((0, n), ("-1:s", "1:s"), attributes, ["s"])

        # Add collocation token indexes
        for l in lines:
            m = l.pop("metadata")
            pos = [n for n, cls in enumerate(m) if cls == u"col0 coll"]
            l["coll_pos"] = self.extract_candidate_tokens(pos)

        return lines

    # -- Properties of extracted candidates

    @property
    def candidate_count(self):
        """
        Returns the number of candidate "types", that is the number of distinct
        matches of the pattern on lemma level

        """
        return len(self.candidates)

    @property
    def instance_count(self):
        """
        Returns the number of instances, that is the number of matches of the pattern
        in the corpus.

        """
        return sum(c.freq for c in self.candidates)

    # -- Core-related properties

    @property
    def core_pos(self):
        return next(p for p in self.pattern if p.isupper())

    @property
    def core_lempos(self):
        return "%s+%s" % (self.lemma, self.core_pos)

    # -- Pattern-related properties

    @property
    def pattern(self):
        """
        e.g. [u"V", u"*", u"noun"]

        :rtype: list[unicode]
        """
        raise NotImplementedError

    @property
    def friendly_pattern(self):
        """
        e.g. "V + noun"

        :rtype: unicode
        """
        return " + ".join(p for p in self.pattern if p != u"*")

    @property
    def pattern_length(self):
        return len(self.pattern) - self.pattern.count(u"*")

    @property
    def pattern_pos_tags(self):
        """ Returns the uppercased pos tags of the pattern, dropping asterixes """
        return [p.upper() for p in self.pattern if p != u"*"]

    @property
    def core_pos_in_pattern(self):
        return next(n for n, p in enumerate(self.pattern) if p.isupper())

    @property
    def asterix_pos_in_pattern(self):
        """
        Returns the position of the asterix in the pattern. Returns none if the pattern
        does not contain an asterix.
        """
        try:
            return self.pattern.index(u"*")
        except ValueError:
            return None

    # -- Query templates

    @property
    def candidate_query_template(self):
        raise NotImplementedError

    @property
    def example_by_lemma_query_template(self):
        raise NotImplementedError

    @property
    def example_by_word_query_template(self):
        return self.example_by_lemma_query_template.replace("lemma", "word")

    def __build_qcl_query(self):
        """
        Returns a QCL-query for self.pattern

        :rtype: unicode

        # Build example query - TODO: merge with self.build_qcl_query
        q_template = '[word="%s" & pos="%s"]'
        if not is_inflected:
            q_template = '[lemma="%s" & pos="%s"]'
        query = [q_template % (c, p) for (c, p) in zip(candidate, self.pattern_pos_tags())]
        query.insert(self.asterix_pos_in_pattern, u'[ ]{0,}')


        """
        q = []
        for n, p in enumerate(self.pattern):
            # Either core, e.g. "NOUN"
            if p.isupper():
                q.append(u'[lemma="%s" & pos="%s"]' % (self.lemma, p))
            # or collocator, e.g. "ajg"
            elif p.islower():
                q.append(u'[pos="%s"]' % p.upper())
            elif p == "*":
                # TODO: exclude pos tags
                # q.append(u'[pos!="%s" & pos!="%s"]{0,}') % (self.pattern[n-1].upper(), self.pattern[n-1].upper())
                q.append(u'[ ]{0,}')
            else:
                raise MalformedPatternException(u"Not knowing how to interpret '%s'" % p)

        q.append(u"within < s/>")
        return u" ".join(q)


class CollocationCandidate(object):
    def __init__(self, lempos, freqs, extractor, examples=None):
        """

        :param lempos:
        :param freqs: maps word-fullpos -> count
        :param extractor:
        :type extractor: CollocationExtractor

        """
        self.extractor = extractor
        self.lempos = lempos
        self.freqs = freqs
        self.examples = examples if examples else []

    def get_inflected_counts(self):
        """ Returns a descendingly sorted list of word+fullpos count tuples """
        return sorted(self.freqs.iteritems(), key=itemgetter(1), reverse=True)

    @property
    def core_lempos(self):
        return self.extractor.core_lempos

    @property
    def pattern(self):
        return self.extractor.friendly_pattern

    @property
    def lemma(self):
        return u" ".join(x.partition("+")[0] for x in self.lempos.split(" "))

    @property
    def freq(self):
        return sum(self.freqs.itervalues())

    def get_as_json(self):
        return {"core_lempos": self.core_lempos, "lempos": self.lempos,
                "lemma": self.lemma, "pattern": self.pattern,
                "freq": self.freq, "score": 0,  # TODO: Add score info
                "wordpos_freqs": self.get_inflected_counts(),
                "examples": self.examples}


class SimplePatternExtractor(CollocationExtractor):
    def __init__(self, corpus_path, lemma, pattern):
        self._pattern = pattern
        super(SimplePatternExtractor, self).__init__(corpus_path, lemma)

    @property
    def pattern(self):
        return self._pattern


PATTERNS = [["NOUN", "*", "v"], ["v", "*", "NOUN"], ["v", "*", "prep", "NOUN"],
            ["NOUN", "adj"], ["NOUN", "noun"], ["noun", "NOUN"]]

