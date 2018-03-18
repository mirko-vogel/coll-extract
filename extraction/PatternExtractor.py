# coding=utf-8
import logging
import manatee
from collections import defaultdict
from itertools import izip
from operator import itemgetter

from Pattern import Pattern, NOUN_PATTERNS
from Concordance import Concordance


class PatternExtractor(object):
    """

    """

    def __init__(self, corpus_path, pattern):
        """

        :param corpus_path:
        :type corpus_path: unicode
        :param pattern:
        :type pattern: Pattern
        """

        self.corpus = manatee.Corpus(corpus_path)
        self.pattern = pattern
        self.candidates = []

        logging.info("Getting N for pattern %s", unicode(self.pattern))
        q = self.pattern.get_all_query()
        self.N = Concordance(self.corpus, q, async=False).size()
        logging.info("Done. N = %d", self.N)

    def fetch_candidates(self, core_lemmas):
        """
        Fetches collocation candidates using the candidate query template,
        storing them in self.candidates.

        :type core_lemmas; list[unicode]
        :rtype: list[CollocationCandidate]
        """
        logging.info("Getting instances for core '%s' ...", " ".join(core_lemmas))
        q = self.pattern.get_by_core_query(core_lemmas)
        c = Concordance(self.corpus, q, 10000000, -1)
        c.sync()
        R1 = c.size()
        logging.info("Done, got %d instances.", R1)

        attr = ["word", "pos", "lemma", "fullpos"]
        candidates = {}

        logging.info("Collecting instances ...")
        lines = c.get_kwic_lines((1, c.size()), (0, 0), attr, ["s"])

        for l in lines:
            # Extract actual match of pattern
            core_idx, coll_idx = self.pattern.get_toks_from_matched_line(range(len(l["word"])))
            for a in attr:
                l[a] = [s for (n, s) in enumerate(l[a]) if n in core_idx + coll_idx]

            # Either create a new candidate or add an instance
            k = u" ".join(l["lemma"])
            c = candidates.get(k)
            if not c:
                candidates[k] = c = CollocationCandidate(l["lemma"], self, R1)
            c.add_instance(l)

        logging.info("Done, there are %d candidates.", len(candidates))
        return sorted(candidates.itervalues(), key=lambda c: c.freq, reverse=True)


class CollocationCandidate(object):
    def __init__(self, lemmas, extractor, R1):
        """

        :param lemmas:
        :param extractor:
        :type extractor: CollocationExtractor

        """
        self.extractor = extractor
        self.lemmas = lemmas

        p = self.extractor.pattern
        self.core_lemmas, self.coll_lemmas = p.get_toks_from_matched_line(lemmas)
        self.core_pos, self.coll_pos = p.get_toks_from_matched_line(p.pos)

        self.instance_counts = defaultdict(int)
        self.examples = []
        self.R1 = R1
        self.C1 = 0

    def add_instance(self, l):
        k = " ".join(l["word"])
        self.instance_counts[k] += 1

    def get_instance_counts(self):
        """ Returns a descendingly sorted list of word count tuples """
        return sorted(self.instance_counts.iteritems(), key=itemgetter(1), reverse=True)

    def fetch_marginal_count(self):
        """ Fetches R1 """
        logging.debug("Getting C1 for %s ...", self.lemma)
        q = self.pattern.get_by_coll_query(self.coll_lemmas)
        self.C1 = Concordance(self.extractor.corpus, q, async=False).size()
        logging.debug("Done")

    def fetch_examples(self, attributes=None, n=10):
        """ Fetches examples """
        if not attributes:
            attributes = ["word"]

        logging.debug("Getting examples for %s ...", self.lemma)
        q = self.pattern.get_by_core_coll_query(self.core_lemmas, self.coll_lemmas)
        c = Concordance(self.extractor.corpus, q, async=False)
        lines = c.get_kwic_lines((0, n), ("-1:s", "1:s"), attributes, ["s"])

        # Add collocation token indexes
        for e in lines:
            m = e.pop("metadata")
            pos = [n for n, cls in enumerate(m) if cls == u"col0 coll"]
            e["core_idx"], e["coll_idx"] \
                = self.pattern.get_toks_from_matched_line(range(len(m)), pos[0], pos[-1])
            self.examples.append(e)

        logging.debug("Done")

    def contingency_table(self):
        """ Returns the constituency table as a dict. """
        a = self.freq
        b = self.R1 - a
        N = self.extractor.N
        # Without the marginal count C1, we have to put of with an incomplete table
        if not self.C1:
            return {"a": a, "b": b, "N": N}

        c = self.C1 - a
        d = N - a - b - c
        return {"a": a, "b": b, "c": c, "d": d}

    @property
    def pattern(self):
        return self.extractor.pattern

    @property
    def core_lempos(self):
        return " ".join("%s+%s" % (l, p)
                        for (l, p) in izip(self.core_lemmas, self.core_pos))

    @property
    def lemma(self):
        return " ".join(self.lemmas)

    @property
    def freq(self):
        return sum(self.instance_counts.itervalues())

    def get_as_json(self):
        r = {}
        r["core_lempos"] = self.core_lempos
        r["lemma"] = self.lemma
        r["pattern"] = unicode(self.pattern)
        r["freq"] = self.freq
        r["contingency_table"] = self.contingency_table()
        r["scores"] = {}  # TODO: Add score info
        r["instance_counts"] = self.get_instance_counts()
        r["examples"] = self.examples
        return r


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

    path = "/home/mirko/Projects/arabic_corpora/manatee_corpora/registry/lcc"
    for p in NOUN_PATTERNS:
        e = PatternExtractor(path, Pattern(p))
        cc = e.fetch_candidates([u"حرب"])
        c = cc[0]
        c.fetch_marginal_count()
        c.fetch_examples()
        print c.get_as_json()
