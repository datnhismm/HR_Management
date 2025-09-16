"""
Helper script to train a spaCy NER model for extracting employee fields.

Usage (local dev):
  - Prepare training data in spaCy JSONL format with entities for labels: NAME, EMAIL, DOB, JOB_TITLE, ROLE, YEAR_START, YEAR_END, CONTRACT_TYPE
  - Install spaCy and a base model: `pip install spacy && python -m spacy download en_core_web_sm`
  - Run: `python ml/train_spacy_ner.py --train data/train.spacy --output ./models/employee_ner --n_iter 20`

This script is intentionally lightweight; it checks for spaCy and exits with a helpful message if not available.
"""

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Train spaCy NER model for employee fields"
    )
    parser.add_argument(
        "--train",
        required=True,
        help="Path to training data in spaCy binary format or JSONL",
    )
    parser.add_argument(
        "--output", required=True, help="Output directory for trained model"
    )
    parser.add_argument("--n_iter", type=int, default=20)
    args = parser.parse_args()

    try:
        import spacy

        # compounding may be exported from util or util.schedules depending on spaCy version
        from spacy.util import minibatch

        try:
            from spacy.util import compounding  # type: ignore
        except Exception:
            try:
                from spacy.util.schedules import compounding  # type: ignore
            except Exception:
                compounding = None
        from spacy.training import Example
    except Exception:
        logger.error(
            "spaCy is not installed. Install it with: pip install spacy and download a model (python -m spacy download en_core_web_sm)"
        )
        sys.exit(2)

    train_path = Path(args.train)
    if not train_path.exists():
        logger.error("Training file not found: %s", train_path)
        sys.exit(2)

    nlp = spacy.blank("en")
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner")
    else:
        ner = nlp.get_pipe("ner")
    # static analyzers sometimes think nlp.add_pipe is a function; ensure ner is not callable
    if callable(ner):
        # try getting by name again; worst-case leave as-is and guard later
        try:
            ner = nlp.get_pipe("ner")
        except Exception:
            pass

    # load training data (expects spaCy JSONL of (text, {'entities': [...]}) )
    examples = []
    import json

    with open(train_path, "r", encoding="utf-8") as f:
        import types

        for line in f:
            obj = json.loads(line)
            text = obj.get("text")
            ents = obj.get("entities", [])
            for e in ents:
                # guard that ner is a pipeline component with add_label and not a plain function
                if not isinstance(ner, types.FunctionType):
                    add_label = getattr(ner, "add_label", None)
                    if callable(add_label):
                        try:
                            add_label(e[2])
                        except Exception:
                            # ignore malformed labels
                            pass
            examples.append((text, {"entities": ents}))

    # Convert to Example objects for training
    examples_spacy = []
    for text, ann in examples:
        doc = nlp.make_doc(text)
        example = Example.from_dict(doc, ann)
        examples_spacy.append(example)

    optimizer = nlp.initialize()
    for i in range(args.n_iter):
        losses = {}
        # ensure compounding is callable; if not, fallback to a simple fixed-size generator
        comp_fn = (
            compounding
            if callable(compounding)
            else (lambda a, b, c: (4 for _ in range(1)))
        )
        batches = minibatch(examples_spacy, size=comp_fn(4.0, 32.0, 1.001))
        for batch in batches:
            nlp.update(batch, sgd=optimizer, losses=losses)
        logger.info("Iteration %d, losses=%s", i + 1, losses)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(out_dir)
    logger.info("Saved model to %s", out_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
