# coding=utf-8

NOUN_PATTERNS = ['NOUN * v', 'v * NOUN', 'NOUN adj', 'NOUN noun', 'noun NOUN',
            'v * prep NOUN', "noun prep NOUN", "NOUN adj prep"]

class Pattern(object):
    u"""
    Represents a collocation pattern, e.g. "v * prep NOUN".

    This pattern can be instantiated to produce queries representing different
    cells in the contingency table, namely:

    * a  = #(u, v)
    * N  = #(*, *)
    * R1 = #(u, *)
    * C1 = #(*, v)

    These values are sufficient to calculate the remaining values. (Note that
    there are no queries to directly obtain the numbers b, c and d as there
    is not easy way to negate a multi-word pattern in QCL.)

    >>> p = Pattern("v * prep NOUN", asterix='[pos!="V"]{0,}')
    >>> print p.get_all_query()
    [pos="V"] [pos!="V"]{0,} [pos="PREP"] [pos="NOUN"] within < s/>
    >>> print p.get_by_core_query([u"اتفاقية"])
    [pos="V"] [pos!="V"]{0,} [pos="PREP"] [lempos="اتفاقية\+NOUN"] within < s/>
    >>> print p.get_by_coll_query([u"وافق", u"على"])
    [lempos="وافق\+V"] [pos!="V"]{0,} [lempos="على\+PREP"] [pos="NOUN"] within < s/>
    >>> print p.get_by_core_coll_query([u"اتفاقية"], [u"وافق", u"على"])
    [lempos="وافق\+V"] [pos!="V"]{0,} [lempos="على\+PREP"] [lempos="اتفاقية\+NOUN"] within < s/>

    """

    def __init__(self, p, asterix="[]{0,}", within_structure="s"):
        """

        :param p: The pattern as a sequence of pos tags where uppercase marks
            the core, the collocator is lowercase, e.g. "NOUN adj".
        :type p: unicode
        :param asterix: how to render the asterix in the query
        :type asterix: unicode
        :param within_structure: limit query matches to given structure
            (is translated as "within < x/> in query)
        :type within_structure: unicode
        """

        self.p = p.split(" ")
        self.asterix = asterix
        self.within_structure = within_structure

        self.core_idx, self.core_pos = {}, []
        self.coll_idx, self.coll_pos = {}, []
        self.asterix_idx = {}

        # Build reverse lookup lists pos_in_pattern -> pos_in_core / pos_in_coll
        for n, s in enumerate(self.p):
            if s.isupper():
                self.core_idx[n] = len(self.core_idx)
                self.core_pos.append(s)
            elif s.islower():
                self.coll_idx[n] = len(self.coll_idx)
                self.coll_pos.append(s.upper())
            elif s == u"*":
                self.asterix_idx[n] = len(self.asterix_idx)
            else:
                raise Exception("Pattern token invalid '%s'" % s)

    def __unicode__(self):
        return u" ".join(self.p)

    def as_string(self, core_lemma=None, coll_lemma=None):
        """ Returns a partially of fully instantiated pattern as string """
        pass # TODO

    @property
    def pos(self):
        """
        Returns the pos tags of the pattern

        >>> Pattern("v * prep NOUN").pos
        ['V', 'PREP', 'NOUN']

        """
        return [s.upper() for s in self.p if s != u"*"]

    def get_toks_from_matched_line(self, line, match_begin=0, match_end=None):
        """
        Helper returning the indexes of the core and of the collocator in a match.

        >>> p = Pattern("NOUN adj")
        >>> p.get_toks_from_matched_line(range(10), 0, 3)
        ([0], [1])
        >>> p = Pattern("v * prep NOUN")
        >>> p.get_toks_from_matched_line(["V", "PREP", "NOUN"])
        (['NOUN'], ['V', 'PREP'])
        >>> p.get_toks_from_matched_line(range(10), 2, 8) # asterix matched 5 tokens
        ([8], [2, 7])
        >>> p.get_toks_from_matched_line(range(10), 2, 4) # asterix matched 0 tokens
        ([4], [2, 3])

        :param line: A list of tokens containing a match of this pattern
        :type line: list()
        :param match_begin: first index of match
        :param match_end: last index of match
        :rtype: tuple[list,list]
        """

        # Cannot handle case with more than one asterix ...
        if len(self.asterix_idx) > 1:
            raise NotImplementedError

        if match_end is None:
            match_end = len(line) - 1

        asterix_pos_in_pattern = next(iter(self.asterix_idx), len(self.p))
        match_length = match_end - match_begin + 1
        asterix_length =  match_length - len(self.core_idx) - len(self.coll_idx)

        def f(idx):
            if idx < asterix_pos_in_pattern:
                return match_begin + idx
            return match_begin + idx + asterix_length - 1

        core_toks = [s for (n, s) in enumerate(line) if n in map(f, self.core_idx)]
        coll_toks = [s for (n, s) in enumerate(line) if n in map(f, self.coll_idx)]
        return core_toks, coll_toks

    def instantiate(self, core_attr=None, coll_attr=None, inject_pos=True):
        u"""
        Instantiates the pattern by injecting the given attributes,
        optimizes pos and lemma to lempos.

        >>> p = Pattern("NOUN adj")
        >>> p.instantiate()
        u'[pos="NOUN"] [pos="ADJ"] within < s/>'
        >>> print p.instantiate({"lemma": [u"اتفاقية"]})
        [lempos="اتفاقية\+NOUN"] [pos="ADJ"] within < s/>
        >>> p = Pattern("v * prep NOUN", asterix='[pos!="V"]{0,}')
        >>> print p.instantiate({"lemma": [u"اتفاقية"]}, {"lemma": [u"وافق", u"على"]})
        [lempos="وافق\+V"] [pos!="V"]{0,} [lempos="على\+PREP"] [lempos="اتفاقية\+NOUN"] within < s/>

        :param core_attr:
        :type core_attr: dict[unicode,list[unicode]]
        :param coll_attr:
        :type coll_attr: dict[unicode,list[unicode]]
        :param inject_pos: Add pos tags from pattern, eventually overwriting pos tags
            in core_attr and coll_attr
        :rtype: unicode

        """
        if not core_attr: core_attr = {}
        if not coll_attr: coll_attr = {}

        if inject_pos:
            core_attr["pos"] = self.core_pos
            coll_attr["pos"] = self.coll_pos

        assert all(len(v) == len(self.core_pos) for v in core_attr.itervalues())
        assert all(len(v) == len(self.coll_pos) for v in coll_attr.itervalues())

        p = []
        for n, d in enumerate(self.p):
            # Asterix have a predefined instantiation
            if n in self.asterix_idx:
                p.append(self.asterix)
                continue

            # For core / coll positions, instantiate pattern
            if n in self.core_idx:
                d = dict((a, v[self.core_idx[n]]) for a, v in core_attr.iteritems())
            else:
                d = dict((a, v[self.coll_idx[n]]) for a, v in coll_attr.iteritems())

            # Optimize lempos
            if "lemma" in d and "pos" in d:
                d["lempos"] = u"%s\+%s" % (d.pop("lemma"), d.pop("pos"))

            p.append(u"[%s]" % u" & ".join('%s="%s"' % (a, v) for (a, v) in d.iteritems()))

        if self.within_structure:
            p.append("within < %s/>" % self.within_structure)

        return u" ".join(p)

    def get_by_core_query(self, lemmas):
        """
        Returns the QCL-query for getting all instances of the pattern for the
        given core.

        This query corresponds to (u, *) respectively R_1 in the contingency table.

        :param lemmas:
        :type lemmas: list[unicode]
        :return: a cql query
        :rtype: unicode
        """
        return self.instantiate(core_attr={"lemma": lemmas})

    def get_by_coll_query(self, lemmas):
        """
        Returns the QCL-query for getting all instances of the pattern for the
        given collocator.

        This query corresponds to (*, v) respectively C_1 in the contingency table.

        :param lemmas:
        :type lemmas: list[unicode]
        :return: a cql query
        :rtype: unicode
        """
        return self.instantiate(coll_attr={"lemma": lemmas})

    def get_by_core_coll_query(self, core_lemmas, coll_lemmas):
        """
        Returns the QCL-query for getting all instances of the pattern for the
        given core and the given collocator. (That is, examples of the collocation)

        This query corresponds to (u, v) respectively `a` in the contingency table.

        :param core_lemmas:
        :type core_lemmas: list[unicode]
        :param coll_lemmas:
        :type coll_lemmas: list[unicode]
        :return: a cql query
        :rtype: unicode
        """
        return self.instantiate({"lemma": core_lemmas}, {"lemma": coll_lemmas})

    def get_all_query(self):
        """
        Returns the QCL-query for getting all instances of the pattern.

        This query corresponds to (*, *) respectively `N` in the contingency table.

        :return: a cql query
        :rtype: unicode
        """
        return self.instantiate()
