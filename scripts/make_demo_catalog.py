"""Build a throwaway Lightroom library to demonstrate against.

Recording a screencast of the real thing means running it on somebody's
photographs, and nobody should have to do that to make a video. This builds a
small library -- catalog plus files on disk -- that behaves like a real one:
several days in one folder, a themed folder, a session folder with an extra
label, and one photo whose date disagrees with the folder it sits in, so the
findings table has something in it.

    python scripts/make_demo_catalog.py ~/Desktop/lrfc-demo

Delete the directory afterwards. Nothing in it is precious.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

#: (file name, taken at, folder) -- enough shapes to show every decision the
#: tool can be asked to make, and small enough to run in front of a camera.
PHOTOS = [
    ("A0001.CR2", "2019-01-03T09:14:00", "raw2019/"),
    ("A0002.CR2", "2019-01-03T09:31:00", "raw2019/"),
    ("A0003.CR2", "2019-01-19T16:02:00", "raw2019/"),
    ("A0004.CR2", "2019-02-11T11:48:00", "raw2019/"),
    ("A0005.CR2", "2019-02-24T14:20:00", "raw2019/"),
    ("B0001.CR2", "2020-06-08T10:05:00", "raw2020/"),
    ("B0002.CR2", "2020-06-08T10:07:00", "raw2020/"),
    ("B0003.CR2", "2020-09-30T18:41:00", "raw2020/"),
    # A themed folder, the kind you would want left alone or moved unchanged.
    ("P0001.CR2", "2019-05-20T11:00:00", "raw2019/Portfolio/"),
    ("P0002.CR2", "2021-08-02T11:00:00", "raw2019/Portfolio/"),
    # A session folder already named by date, with a label worth keeping.
    ("F0001.CR2", "2019-03-10T13:00:00", "raw2019/2019-03-10 Fasching/"),
    # ... and the one photo in it that was taken on a different day.
    ("F0002.CR2", "2019-07-07T13:00:00", "raw2019/2019-03-10 Fasching/"),
]


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    directory = Path(argv[1]).expanduser()
    if directory.exists() and any(directory.iterdir()):
        print("{d} is not empty -- refusing to build into it.".format(d=directory))
        return 1
    directory.mkdir(parents=True, exist_ok=True)

    from conftest import CatalogBuilder

    builder = CatalogBuilder(directory, catalog_name="Demo.lrcat")
    for name, taken, folder in PHOTOS:
        builder.add_photo(name, taken, folder=folder)
    catalog = builder.catalog_path if hasattr(builder, "catalog_path") else None
    if catalog is None:  # pragma: no cover - depends on the builder's shape
        catalog = next(directory.rglob("Demo.lrcat"))

    print("Demo library ready:")
    print("  catalog : {c}".format(c=catalog))
    print("  photos  : {n}".format(n=len(PHOTOS)))
    print()
    print("Try it:")
    print('  lrfc plan "{c}" --structure day'.format(c=catalog))
    print('  lrfc apply "{c}" --structure day'.format(c=catalog))
    print()
    print("Delete {d} when you are done.".format(d=directory))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
