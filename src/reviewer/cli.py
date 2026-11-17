import argparse
import json
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reviewer.pipeline import load_bundle, review_bundle
from reviewer.model import FakeClient

EXIT_CODES = {"PASS": 0, "CHANGES_REQUIRED": 1, "INCOMPLETE": 2}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Review a requirements / spec / workflow / code bundle.")
    parser.add_argument("bundle", help="path to a bundle JSON file")
    parser.add_argument("--fake-model", default=None,
                        help="fake client mode (use a mode defined in model.py, e.g. timeout)")
    parser.add_argument("--max-retries", type=int, default=None, help="override model retry limit")
    parser.add_argument("--out", default=None, help="also write the report to this file")
    args = parser.parse_args(argv)

    with open(args.bundle) as f:
        raw = json.load(f)

    mode = args.fake_model or raw.get("model_mode")
    client = FakeClient(mode) if mode else None

    config = {}
    if args.max_retries is not None:
        config["max_retries"] = args.max_retries

    try:
        bundle = load_bundle(raw)
    except Exception as error:
        report = {"status": "INCOMPLETE", "summary": "bundle could not be loaded",
                  "findings": [], "coverage": [], "checks": [],
                  "unreviewed": ["load error: " + str(error)]}
    else:
        report = review_bundle(bundle, client=client, config=config)

    report["model_note"] = ("fake client only, real model not measured"
                            if client is not None else "model not used")
    text = json.dumps(report, indent=2, default=str)
    print(text)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    return EXIT_CODES.get(report["status"], 2)


if __name__ == "__main__":
    sys.exit(main())