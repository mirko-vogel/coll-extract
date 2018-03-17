# coding=utf-8

class Pattern(object):
    u"""
    Represents a collocation extraction pattern.

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

    def __init__(self, p, asterix="[]{0,}", within="< s/>"):
        """

        :param p: The pattern as a sequence of pos tags where uppercase marks
            the core, the collocator is lowercase, e.g. "NOUN adj".
        :type p: unicode
        :param asterix: how to render the asterix in the query
        :type asterix: unicode
        :param within: last element of query
        :type within: unicode
        """

        self.p = p.split(" ")
        self.asterix = asterix
        self.within = within

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

        if self.within:
            p.append("within %s" % self.within)

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
