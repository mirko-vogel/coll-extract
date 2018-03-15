# coding=utf-8
import manatee
import tempfile

import os

from datetime import datetime
from itertools import izip, repeat, chain


def parse_stream(s, attributes):
    """
    The format of the keyword-in-context lines depends on number of attributes,
    where `attrs` affects the return value of get_kwic(), whereas `ctxattr` affect
    the output of get_left() and get_right().

      * If only one attribute is requested, the return value is a concatenated sequence of pairs,
        where the first element is a space-separated concatenation of attributes and the second
        element the corresponding metadata.

      * If several attributes are requested, the return value is a concatenation of four-tuples
        (word, _, attributes, metadata), e.g. (word_1, _, attributes_1, _, word_2, _, attributes_2, _, ...).
        `attributes` is a slash separated string with trailing slash
        e.g. "/PUNC/.+PUNC/PUNC"

    :type s: str
    :type attributes: list[str]

    """
    s = [e.decode("utf-8") for e in s]
    if len(attributes) == 1:
        concat_values, concat_metadata = s[0::2], s[1::2]
        values, metadata = [], []
        for v, m in izip(concat_values, concat_metadata):
            v_split = v.strip(" ").split(" ")
            values += v_split
            metadata += repeat(m.strip("{}"), len(v_split))
        return { attributes[0]: values, "metadata": metadata }

    # Strange, sometimes the "word" attribute has an extra space ...
    r = { attributes[0]: [a.strip(" ") for a in s[0::4]],
          "metadata": [m.strip("{}") for m in s[1::4]] }
    # Drop the first other attribute, it is always empty
    other_attrs = [a.split("/")[1:] for a in s[2::4]]
    for n, attr in enumerate(attributes[1:]):
        r[attr] = [attrs[n] for attrs in other_attrs]

    return r

class Concordance(manatee.Concordance):
    """

    """
    def extract_collocations(self, attribute, sort_key, min_freq, min_bgr, window, max_count):
        """
        Wrapper around manatee.CollocItems to extract collocation candidates

        :param attribute: the attribute to extract, e.g. "word" or "lempos"
        :param sort_key:
        :param min_freq: minimum frequency of collocator in corpus
        :param min_bgr: minimum frequency of collocator given range (e.g. minimum frequency of collocation)
        :param window: tuple specifying the left and the right border of the extraction window,
        (-3, -1) would capture the two preceding tokens.
        :param max_count:
        :return: collocation candidates as tuples: lemma, pos, frequency, score

        """
        r = manatee.CollocItems(self, attribute, sort_key, min_freq, min_bgr,
                                window[0], window[1], max_count)

        candidates = []
        while not r.eos():
            coll_lemma, _, coll_pos = r.get_item().decode("utf-8").rpartition("+")
            # We do not store the collocator frequency col.get_cnt(),
            candidates.append((coll_lemma, coll_pos, r.get_freq(), r.get_bgr("m")))
            r.next()

        return candidates


    def filter(self, query, window, rank=1):
        """
        Filters the concordance only retaining lines where the query is matched
        in a window around the keyword.

        :param query:
        :param window: Left and right context to search, e.g. ("-1:s", "1:s") for current sentence
        :param rank:

        """
        collnum = self.numofcolls() + 1
        self.set_collocation(collnum, query + ";", str(window[0]), str(window[1]), rank, exclude_kwic=True)
        self.delete_pnfilter(collnum, True)

    def copy(self, tmpdir = None):
        """
        Creates a copy of the concordance by writing it to disk and reading it again.

        :param tmpdir:
        :return:
        :rtype: Concordance

        """
        fn = tempfile.mktemp(dir=tmpdir)
        self.save(fn)
        c = Concordance(self.corp(), fn)
        os.unlink(fn)
        return c

    def get_kwic_lines(self, line_range, context_window, attrs, refs, structs=""):
        """
        Returns lines from the concordance

        :param line_range:
        :param context_window:
        :param attrs: list of attributes to return for each word, e.g. ["word", "pos"]
        :param refs: list of metadata attributes to return for each line, e.g. ["doc", "s"]
        :param structs: list of structure tags that are returned/applied, e.g. ["p","g"]
        :return: a list of lines. A line is a tuple consisting of a sequence of
            attribute tuples, a list of positions of the keywords, and a list of references.
            This list will contain a single element unless the line does crosses the boundary
            of one of the structures specified in struct.
        :rtype: list[dict]

        """
        rs = self.RS(True, line_range[0], line_range[1])
        # The second "attrs" argument specified the atrributes of the context as opposed
        # to the attributes of the keyword(s)
        kl = manatee.KWICLines(self.corp(), rs, str(context_window[0]), str(context_window[1]),
                               ",".join(attrs), ",".join(attrs), ",".join(structs), ",".join(refs))

        lines = []
        while kl.nextline():
            l, m, r = kl.get_left(), kl.get_kwic(), kl.get_right()
            l = parse_stream(l + m + r, attrs)
            l["ref"] = kl.get_refs()
            lines.append(l)

        return lines

    def get_kwic_lines_as_strings(self, line_range, context_window=("-1:s", "1:s")):
        lines = self.get_kwic_lines(line_range, context_window, ["word"], [])
        return [" ".join(line["word"]) for line in lines]

if __name__ == "__main__":
    path = "/home/mirko/Projects/arabic_corpora/manatee_corpora/registry/lcc"
    query1 = u'[lemma="%s" & pos="NOUN"]' % u"اتفاقية"
    query2 = u'[lemma="%s" & pos="V"]' % u"وافق"
    query3 = u'[lemma="%s" & pos="V"]' % u"صادق"
    verb_prep_noun_pattern = u'[pos="V"] [ ]{0,} [pos="PREP"] [lemma="%s" & pos="NOUN"] within < s/>'

    query4 = verb_prep_noun_pattern % u"اتفاقية"
    corp = manatee.Corpus(path)
    t = datetime.now()
    c = Concordance(corp, query4, 1000000, -1)
    c.sync()
    print c.size()
    print datetime.now() - t
    r = c.get_kwic_lines((1, 5), ("-1:s", "1:s"), ["word", "pos", "lemma", "fullpos"], ["s"], ["ltr"])
    #r = c.get_kwic_lines((1, 5), ("-1:s", "1:s"), ["word", "pos"], ["s"], ["ltr"])
    for l in c.get_kwic_lines_as_strings((1, 5)):
        print l
    #c2 = c.copy()
    #c2.filter(query2, ("-5", "5"))
    #c2.sync()
    #print c2.size()
    #print "\n".join(c2.get_kwic_lines_as_strings( (1,2)))

    #c3 = c.copy()
    #c3.filter(query3, ("-1:s", "1:s"))
    #c3.sync()
    #print c3.size()
    #print c3.get_kwic_lines_as_strings((1,2))[0]
    #r = c3.get_kwic_lines( (1,2), ("-1:s", "1:s"), ["word"], ["s"])
    #r =  c3.get_kwic_lines((1, 2), ("-1:s", "1:s"), ["word", "pos"], ["s"])
    #r = c3.get_kwic_lines((2, 3), ("-1:s", "1:s"), ["word", "pos"], ["s"], ["ltr"])
    #print r