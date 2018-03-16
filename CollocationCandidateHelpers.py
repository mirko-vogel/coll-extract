# coding=utf-8
'''
Created on Mar 11, 2018

@author: mirko
'''

import re

def get_example(c):
    """
    
    """
    ic = c.get("inflected_forms", {})
    ics = sorted(ic.iteritems(), key=lambda (_, ic): ic["freq"],
                 reverse=True)
    for (ic_key, ic) in ics:
        for e in ic["examples"].itervalues():
            # Check for rating
            return (ic_key, e)
    
    return None, None


def get_canonical_form(c):
    """
    Returns most frequent form without determination if this form exists, too
    
    """
    return c["lemma"]

    # ics = sorted(c["inflected_forms"].itervalues(), key = lambda ic: ic["freq"])
    # if not ics:
    #         return "%s %s" % (c["core_lemma"], c["coll_lemma"])
    #
    # candidates = [(ic["core_word"], ic["coll_word"]) for ic in ics]
    # core, coll = candidates[-1]
    # core_indet = core[2:] if core.startswith(u"ال") else core
    # coll_indet = coll[2:] if coll.startswith(u"ال") else coll
    #
    # if (core_indet, coll_indet) in candidates:
    #     return "%s %s" % (core_indet, coll_indet)
    # return "%s %s" % (core, coll)


def get_rating(o):
    """
    Maps the o["ratings"] dict to a string: "none", "mixed" or a rating"""
    try:
        s = set(o["ratings"].itervalues())
    except:
        return None
    
    if len(s) == 0:
        return None
    if len(s) > 1:
        return "mixed"
    return next(iter(s))

def pretty_print_example(e):
    hl_toks = ["<b>%s</b>" % w if n in e["coll_pos"] else w
               for (n, w) in enumerate(e["word"])]
    hl = u" ".join(hl_toks)
    # TODO: Decent postprocessing
    return re.sub(u" ،", u"،", re.sub(u" [.]", u".", hl))


if __name__ == '__main__':
    pass
