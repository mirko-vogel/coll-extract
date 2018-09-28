# coding=utf-8
import codecs
from collections import defaultdict

import conllu.parser, conllu.tree_helpers
import nltk.corpus


class TreeNode():
    def __init__(self, data, parent, children):
        self.data, self.parent, self.children = data, parent, children


def create_tree(node_children_mapping, parent, start=0):
    subtree = []
    for child in node_children_mapping[start]:
        n = TreeNode(child, parent, None)
        n.children = create_tree(node_children_mapping, n, child["id"])
        subtree.append(n)

    return subtree


def sent_to_tree(sentence):
    head_indexed = defaultdict(list)
    for token in sentence:
        if token["id"] == None:
            continue
        # If HEAD is negative, treat it as child of the root node
        head = max(token["head"], 0)
        head_indexed[head].append(token)

    return create_tree(head_indexed, None)


# The last field "misc" is broken, the fields separator is used to transliterate initial
# hamza al-madd?! "Vform=آنى|Translit=|nY".
FIELDS = ('id', 'form', 'lemma', 'upostag', 'xpostag', 'feats', 'head', 'deprel', 'deps')


def parse_tree(text, fields=FIELDS):
    result = conllu.parser.parse(text, fields)

    if "head" not in result[0][0]:
        raise Exception("Can't parse tree, missing 'head' field.")

    trees = []
    for sentence in result:
        trees += sent_to_tree(sentence)

    return trees


def print_tree(node, depth=0, indent=4, exclude_fields=["id", "deprel", "xpostag", "feats", "head", "deps", "misc"]):
    relevant_data = node.data.copy()
    map(lambda x: relevant_data.pop(x, None), exclude_fields)
    node_repr = " ".join([
        "{key}:{value}".format(key=key.encode("utf-8"), value=value.encode("utf-8"))
        for key, value in relevant_data.items()
    ])

    print(" " * indent * depth + "(deprel:{deprel}) {node_repr} [{idx}]".format(
        deprel=node.data["deprel"],
        node_repr=node_repr,
        idx=node.data["id"]
    ))
    for child in node.children:
        print_tree(child, depth + 1, indent=indent, exclude_fields=exclude_fields)


def read_conllu(stream):
    #nltk.corpus.reader.util.read_blankline_block()
    data = ""
    for l in stream:
        if l == "\n":
            t = parse_tree(data)[0]
            t.conllu = data
            yield t
            data = ""
        else:
            data += l

    if data:
        yield parse_tree(data)[0]


def iter_tree(t):
    yield t
    for subtree in t.children:
        for n in iter_tree(subtree):
            yield n


#import ufal.udpipe

if __name__ == "__main__":
    fn = "/home/mirko/Projects/coll_extract/conllu/data/ittifaqia.parsed.conllu"
    parsed = list(read_conllu(codecs.open(fn, "r", "utf-8")))
    print len(parsed)
    print_tree(parsed[0])
    print_tree(parsed[-1])
