#!/usr/bin/python
import json

from pymongo import MongoClient

from extraction import ALL_EXTRACTORS
import argparse
import logging

if __name__ == "__main__":
    known_extractors = dict( (c.__name__, c) for c in ALL_EXTRACTORS)

    p = argparse.ArgumentParser()
    p.add_argument("core", type=str,
                   help="The core word to extract collocations for")
    p.add_argument("corpus", type=argparse.FileType(),
                   help="Path to the manatee corpus registry file")

    p.add_argument("--extractors", nargs="+", type=str, default=known_extractors.keys(),
                   help="Extractors to run")

    g = p.add_argument_group("Example selection parameters")
    g.add_argument("--example-count", type=int, default=10,
                   help="Number of examples to fetch for each candidate.")

    g = p.add_argument_group("Candidate filter parameters")
    g.add_argument("--min-freq", type=int, default=0,
                   help="Drop candidates if freq is below min_freq")
    g.add_argument("--min-score", type=int, default=0,
                   help="Drop candidates if score is below min_score")

    g = p.add_argument_group("Storage parameters")
    g.add_argument("--write-to-file", type=argparse.FileType("w"), dest="out_file",
                   help="Write extracted collocatons to given file (default, write to mongodb)")
    g.add_argument("--db-url", type=str)
    g.add_argument("--db-name", type=str, default="collocation_review")
    g.add_argument("--db-collection", type=str, default="candidates")

    args = p.parse_args()
    core = args.core.decode("utf-8")

    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    logging.info("Extracting collocations for '%s' using the following extractors: %s",
                 core, ", ".join(args.extractors))

    if args.out_file:
        logging.info("Extracted collocations will be written to '%s'.", args.out_file.name)
    else:
        logging.info("Extracted collocations will be written to MongoDB (%s, %s.%s).",
                     args.db_url, args.db_name, args.db_collection)
        db = MongoClient(args.db_url).get_database(args.db_name).get_collection(args.db_collection)

    candidates = []
    for cls_name in args.extractors:
        e = known_extractors[cls_name](args.corpus.name, core)
        logging.info("Starting extraction for pattern '%s' with %s ...",
                     e.friendly_pattern, cls_name)
        e.fetch_candidates()
        logging.info("Fetched %s candidates (%d instances).", e.candidate_count, e.instance_count)

        logging.info("Filtering candidates ...")
        e.filter_candidates(min_freq=args.min_freq, min_score=args.min_score)
        logging.info("Done. %d candidates (%d instances) remaining.", e.candidate_count, e.instance_count)

        logging.info("Getting %d examples for each candidate ...", args.example_count)
        e.get_examples(n = args.example_count)
        logging.info("Done.")
        candidates.extend(e.get_as_json() for e in e.candidates)

    logging.info("Extracting finished, saving candidates ...")
    if args.out_file:
        json.dump(candidates, args.out_file, indent=2, ensure_ascii=False, encoding="utf-8")
    else:
        db.insert_many(candidates)
    logging.info("Done.")
