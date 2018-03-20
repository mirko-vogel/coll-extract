# coding=utf-8
import logging
import manatee
import tempfile

import os

from datetime import datetime
from itertools import izip, repeat, chain


def parse_stream(s, attributes):
    u"""
    The format of the keyword-in-context lines depends on number of attributes,
    where `attrs` affects the return value of get_kwic(), whereas `ctxattr` affect
    the output of get_left() and get_right().

      * If only one attribute is requested, the return value is a concatenated sequence of pairs,
        where the first element is a space-separated concatenation of attributes and the second
        element the corresponding metadata.

      * If several attributes are requested, the return value is a concatenation of four-tuples
        (word, _, attributes, metadata), e.g. (w1, _, attr1, meta1, w2, _, attr2, meta2,...).
        `attributes` is a slash separated string with trailing slash
        e.g. "/PUNC/.+PUNC/PUNC"

    >>> s = [u'\u062a\u0636\u064a\u0641\u0647', u'{}', u'/V/\u0623\u0636\u0627\u0641/V', u'attr', u' \u0645\u062d\u0643\u0645\u0629', u'{}', u'/NOUN/\u0645\u062d\u0643\u0645\u0629/NOUN-FS', u'attr', u' \u0627\u0644\u062c\u0646\u0627\u064a\u0627\u062a', u'{}', u'/NOUN/\u062c\u0646\u0627\u064a\u0629/NOUN-FP', u'attr', u' \u0627\u0644\u062f\u0648\u0644\u064a\u0629', u'{}', u'/ADJ/\u062f\u0648\u0644\u064a/ADJ-FS', u'attr', u' \u0625\u0644\u0649', u'{}', u'/PREP/\u0625\u0644\u0649/PREP', u'attr', u' \u0645\u0633\u0627\u0631', u'{}', u'/NOUN/\u0645\u0633\u0627\u0631/NOUN-MS', u'attr', u' \u0627\u0644\u0623\u0632\u0645\u0629', u'{}', u'/NOUN/\u0623\u0632\u0645\u0629/NOUN-FS', u'attr', u' \u0627\u0644\u0633\u0648\u0631\u064a\u0629', u'{}', u'/ADJ/\u0633\u0648\u0631\u064a/ADJ-FS', u'attr', u' \u0625\u0630\u0627', u'{}', u'/PART/\u0625\u0630\u0627/PART', u'attr', u' \u062a\u0645\u062a', u'{}', u'/V/\u062a\u0645/V', u'attr', u' \u0625\u062d\u0627\u0644\u0629', u'{}', u'/NOUN/\u0625\u062d\u0627\u0644\u0629/NOUN-FS', u'attr', u' \u0627\u0644\u0645\u0644\u0641', u'{}', u'/NOUN/\u0645\u0644\u0641/NOUN-MS', u'attr', u' \u0625\u0644\u064a\u0647\u0627', u'{}', u'/PREP/\u0625\u0644\u0649/PREP', u'attr', u' \u061f', u'{}', u'/PUNC/\u061f/PUNC', u'attr', u'</s><s>', u'strc', u'\u0625\u0630\u0646', u'{}', u'/ADV/\u0625\u0630\u0646/ADV', u'attr', u' \u0628', u'{}', u'/PREP/\u0628/PREP', u'attr', u'<g/>', u'strc', u'\u0645\u0628\u0627\u062f\u0631\u0629', u'{}', u'/NOUN/\u0645\u0628\u0627\u062f\u0631\u0629/NOUN-FS', u'attr', u' \u0648\u062c\u0647\u0648\u062f', u'{}', u'/NOUN/\u062c\u0647\u062f/NOUN-FP', u'attr', u' \u0633\u0648\u064a\u0633\u0631\u064a\u0629', u'{}', u'/ADJ/\u0633\u0648\u064a\u0633\u0631\u064a/ADJ-FD', u'attr', u' \u062f\u0627\u0645\u062a', u'{}', u'/V/\u062f\u0627\u0645/V', u'attr', u' \u0633\u0628\u0639\u0629', u'{}', u'/NUM/\u0633\u0628\u0639/NUM-FS', u'attr', u' \u0623\u0634\u0647\u0631', u'{}', u'/NOUN/\u0634\u0647\u0631/NOUN-FP', u'attr', u' \u0648\u062c\u0647', u'{}', u'/V/\u0648\u062c\u0647/V', u'attr', u' \u0639\u062f\u062f', u'{}', u'/NOUN/\u0639\u062f\u062f/NOUN-MS', u'attr', u' \u0645\u0646', u'{}', u'/PREP/\u0645\u0646/PREP', u'attr', u' \u0627\u0644\u062f\u0648\u0644', u'{}', u'/NOUN/\u062f\u0648\u0644\u0629/NOUN-FS', u'attr', u' \u0631\u0633\u0627\u0644\u0629', u'{}', u'/NOUN/\u0631\u0633\u0627\u0644\u0629/NOUN-FS', u'attr', u' \u0625\u0644\u0649', u'{}', u'/PREP/\u0625\u0644\u0649/PREP', u'attr', u' \u0645\u062c\u0644\u0633', u'{}', u'/NOUN/\u0645\u062c\u0644\u0633/NOUN-MS', u'attr', u' \u0627\u0644\u0623\u0645\u0646', u'{}', u'/NOUN/\u0623\u0645\u0646/NOUN-MS', u'attr', u' \u062a\u062d\u062b\u0647', u'{}', u'/V/\u062d\u062b/V', u'attr', u' \u0639\u0644\u0649', u'{}', u'/PREP/\u0639\u0644\u0649/PREP', u'attr', u' \u0625\u062d\u0627\u0644\u0629', u'{}', u'/NOUN/\u0625\u062d\u0627\u0644\u0629/NOUN-FS', u'attr', u' \u062a\u0647\u0645', u'{}', u'/NOUN/\u062a\u0647\u0645\u0629/NOUN-FP', u'attr', u' \u0644', u'{}', u'/PREP/\u0644/PREP', u'attr', u'<g/>', u'strc', u'\u0627\u0644\u0646\u0638\u0627\u0645', u'{}', u'/NOUN/\u0646\u0638\u0627\u0645/NOUN-MS', u'attr', u' \u0627\u0644\u0633\u0648\u0631\u064a', u'{}', u'/NOUN/\u0633\u0648\u0631\u064a/NOUN-MS', u'attr', u' \u0628', u'{}', u'/PREP/\u0628/PREP', u'attr', u'<g/>', u'strc', u'\u0627\u0631\u062a\u0643\u0627\u0628', u'{}', u'/NOUN/\u0627\u0631\u062a\u0643\u0627\u0628/NOUN-MP', u'attr', u' \u062c\u0631\u0627\u0626\u0645', u'{}', u'/NOUN/\u062c\u0631\u064a\u0645\u0629/NOUN-FP', u'attr', u' \u0628', u'{col0 coll}', u'/PREP/\u0628/PREP', u'attr', u'<g/>', u'strc', u'\u062d\u0642', u'{}', u'/NOUN/\u062d\u0642/NOUN-MS', u'attr', u' \u0634\u0639\u0628\u0647', u'{}', u'/NOUN/\u0634\u0639\u0628/NOUN-MS', u'attr', u' \u0639\u0644\u0649', u'{}', u'/PREP/\u0639\u0644\u0649/PREP', u'attr', u' \u0645\u062d\u0643\u0645\u0629', u'{}', u'/NOUN/\u0645\u062d\u0643\u0645\u0629/NOUN-FS', u'attr', u' \u0627\u0644\u062c\u0646\u0627\u064a\u0627\u062a', u'{}', u'/NOUN/\u062c\u0646\u0627\u064a\u0629/NOUN-FP', u'attr', u' \u0627\u0644\u062f\u0648\u0644\u064a\u0629', u'{}', u'/ADJ/\u062f\u0648\u0644\u064a/ADJ-FS', u'attr', u' \u0644', u'{}', u'/PREP/\u0644/PREP', u'attr', u'<g/>', u'strc', u'\u0627\u0644\u062a\u062d\u0642\u064a\u0642', u'{}', u'/NOUN/\u062a\u062d\u0642\u064a\u0642/NOUN-MS', u'attr', u' \u0648\u062a\u062a\u0628\u0639', u'{}', u'/NOUN/\u062a\u062a\u0628\u0639/NOUN-MS', u'attr', u' \u0627\u0644\u0645\u0633\u0624\u0648\u0644\u064a\u0627\u062a', u'{}', u'/NOUN/\u0645\u0633\u0624\u0648\u0644\u064a\u0629/NOUN-FP', u'attr', u' \u060c', u'{}', u'/PUNC/\u060c/PUNC', u'attr', u' \u062a\u0647\u0645', u'{}', u'/NOUN/\u062a\u0647\u0645\u0629/NOUN-FP', u'attr', u' \u0648\u062b\u0642', u'{}', u'/NOUN/\u0648\u062b\u0642/NOUN-FP', u'attr', u' \u0644', u'{}', u'/PREP/\u0644/PREP', u'attr', u'<g/>', u'strc', u'\u0647\u0627', u'{}', u'/PRON/\u0644/PRON', u'attr', u' \u062a\u0642\u0631\u064a\u0631', u'{}', u'/NOUN/\u062a\u0642\u0631\u064a\u0631/NOUN-MS', u'attr', u' \u0644', u'{}', u'/PREP/\u0644/PREP', u'attr', u'<g/>', u'strc', u'\u0645\u0646\u0638\u0645\u0629', u'{}', u'/NOUN/\u0645\u0646\u0638\u0645\u0629/NOUN-FS', u'attr', u' \u0647\u064a\u0648\u0645\u0646', u'{}', u'/NOUN/\u0647\u064a\u0648\u0645\u0646/NOUN-MS', u'attr', u' \u0631\u0627\u064a\u062a\u0633', u'{}', u'/NOUN/\u0631\u0627\u064a\u062a\u0633/NOUN-MS', u'attr', u' \u0648\u0648\u062a\u0634', u'{}', u'/NOUN/\u0648\u0648\u062a\u0634/NOUN-MS', u'attr', u' \u062a\u0633\u062a\u0646\u062f', u'{}', u'/V/\u0627\u0633\u062a\u0646\u062f/V', u'attr', u' \u0625\u0644\u0649', u'{}', u'/PREP/\u0625\u0644\u0649/PREP', u'attr', u' \u0623\u062f\u0644\u0629', u'{}', u'/NOUN/\u062f\u0644\u064a\u0644/NOUN-FP', u'attr', u' \u062a\u062b\u0628\u062a', u'{}', u'/V/\u0623\u062b\u0628\u062a/V', u'attr', u' \u0623\u0646', u'{}', u'/PART/\u0623\u0646/PART', u'attr', u' \u0642\u0648\u0627\u062a', u'{}', u'/NOUN/\u0642\u0648\u0629/NOUN-FP', u'attr', u' \u0627\u0644\u0623\u0633\u062f', u'{}', u'/NOUN/\u0623\u0633\u062f/NOUN-MS', u'attr', u' \u0628\u0627\u062a\u062a', u'{}', u'/V/\u0628\u0627\u062a/V', u'attr', u' \u062a\u0642\u0635\u0641', u'{}', u'/V/\u0642\u0635\u0641/V', u'attr', u' \u0645\u0646\u0627\u0637\u0642', u'{}', u'/NOUN/\u0645\u0646\u0637\u0642\u0629/NOUN-FP', u'attr', u' \u0645\u062f\u0646\u064a\u0629', u'{}', u'/ADJ/\u0645\u062f\u0646\u064a/ADJ-FS', u'attr', u' \u0628', u'{}', u'/PREP/\u0628/PREP', u'attr', u'<g/>', u'strc', u'\u0630\u062e\u0627\u0626\u0631', u'{}', u'/NOUN/\u0630\u062e\u064a\u0631\u0629/NOUN-FP', u'attr', u' \u0639\u0646\u0642\u0648\u062f\u064a\u0629', u'{}', u'/NOUN/\u0639\u0646\u0642\u0648\u062f\u064a/NOUN-FS', u'attr', u' \u062a\u0637\u0644\u0642\u0647\u0627', u'{}', u'/V/\u0623\u0637\u0644\u0642/V', u'attr', u' \u0645\u062f\u0627\u0641\u0639', u'{}', u'/NOUN/\u0645\u062f\u0627\u0641\u0639/NOUN-MS', u'attr', u' \u0623\u0631\u0636\u064a\u0629', u'{}', u'/NOUN/\u0623\u0631\u0636\u064a\u0629/NOUN-FS', u'attr', u' .', u'{}', u'/PUNC/./PUNC', u'attr', u'</s><s>', u'strc']
    >>> print u" ".join(parse_stream(s, ["word", "pos", "lemma", "fullpos"])["word"])
    تضيفه محكمة الجنايات الدولية إلى مسار الأزمة السورية إذا تمت إحالة الملف إليها ؟ </s><s> إذن ب <g/> مبادرة وجهود سويسرية دامت سبعة أشهر وجه عدد من الدول رسالة إلى مجلس الأمن تحثه على إحالة تهم ل <g/> النظام السوري ب <g/> ارتكاب جرائم ب <g/> حق شعبه على محكمة الجنايات الدولية ل <g/> التحقيق وتتبع المسؤوليات ، تهم وثق ل <g/> ها تقرير ل <g/> منظمة هيومن رايتس ووتش تستند إلى أدلة تثبت أن قوات الأسد باتت تقصف مناطق مدنية ب <g/> ذخائر عنقودية تطلقها مدافع أرضية . </s><s>

    :type s: str
    :type attributes: list[str]

    """
    s = [e.decode("utf-8") if type(e) == str else e for e in s]
    if len(attributes) == 1:
        concat_values, concat_metadata = s[0::2], s[1::2]
        values, metadata = [], []
        for v, m in izip(concat_values, concat_metadata):
            v_split = v.strip(" ").split(" ")
            values += v_split
            metadata += repeat(m.strip("{}"), len(v_split))
        return {attributes[0]: values, "metadata": metadata}

    # HACK, structures do not have a attributes and metadata #FIXME
    n = 1
    while n < len(s):
        if s[n] == "strc":
            s[n+1:n+1] = ["/" * (len(attributes) - 1), ""]
            n += 2
        n += 1

    # Strange, sometimes the "word" attribute has an extra space ...
    r = {attributes[0]: [a.strip(" ") for a in s[0::4]],
         "metadata": [m.strip("{}") for m in s[1::4]]}
    # Drop the first other attribute, it is always empty
    other_attrs = [a.split("/")[1:] for a in s[2::4]]
    for n, attr in enumerate(attributes[1:]):
        r[attr] = [attrs[n] for attrs in other_attrs]

    return r


class Concordance(manatee.Concordance):
    """

    """

    def __init__(self, corpus, q, max_hits=None, async=True):
        """

        :param corpus:
        :type corpus: manatee.Corpus
        :param q:
        :param max_hits: defaults to corpus size
        :param async:

        """
        if not max_hits:
            max_hits = corpus.size()

        logging.debug("Querying corpus %s: %s", corpus.get_conffile(), q)  # TODO corpus name
        manatee.Concordance.__init__(self, corpus, q, max_hits, -1)
        if not async:
            self.sync()

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

    def copy(self, tmpdir=None):
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
    c = Concordance(corp, query4)
    c.sync()
    print c.size()
    print datetime.now() - t
    r = c.get_kwic_lines((1, 5), ("-1:s", "1:s"), ["word", "pos", "lemma", "fullpos"], ["s"], "ltr")
    # r = c.get_kwic_lines((1, 5), ("-1:s", "1:s"), ["word", "pos"], ["s"], ["ltr"])
    for l in c.get_kwic_lines_as_strings((1, 5)):
        print l
