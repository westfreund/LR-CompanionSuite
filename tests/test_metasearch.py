"""The index across libraries: it reads, and it must never do anything else.

The folder tool earns its safety by touching two columns and no photo row. The
index earns its safety more simply: it opens catalogs read-only and writes only
into a file of its own. The one place it writes a catalog at all is a *copy* it
made itself, and that is checked here against the original's bytes.
"""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from lrcompanion.metasearch import duplicates, query, subset
from lrcompanion.metasearch.scan import find_catalogs, scan
from lrcompanion.metasearch.store import Index, IndexError_
from lrcompanion.metasearch.volumes import BY_FINGERPRINT, BY_UUID, describe


@pytest.fixture
def library(builder):
    """A small catalog with keywords, sizes and two cameras."""
    holiday = builder.add_keyword("Urlaub")
    portrait = builder.add_keyword("Portrait")
    first = builder.add_photo("A0001.CR2", "2019-01-03T11:00:00", camera="Canon EOS 70D")
    second = builder.add_photo("A0002.CR2", "2019-01-03T11:05:00", camera="Canon EOS 70D")
    third = builder.add_photo("B0001.CR2", "2020-06-08T09:00:00", camera="Nikon Z6")
    builder.tag(first, holiday)
    builder.tag(first, portrait)
    builder.tag(second, holiday)
    builder.set_size(first, 6000, 4000)
    builder.set_exif(first, isoSpeedRating=800, focalLength=50, aperture=2.0, shutterSpeed=5.0)
    builder.set_size(second, 6000, 4000)
    builder.set_size(third, 6000, 4000)
    builder._conn.execute("UPDATE Adobe_images SET rating = 4 WHERE rootFile = ?", (first,))
    builder._conn.commit()
    return builder


@pytest.fixture
def filled(library, tmp_path):
    index = Index.open(tmp_path / "index.db")
    scan([library.catalog_path], index)
    yield index
    index.close()


# -- reading only ------------------------------------------------------------


def test_a_scan_leaves_the_catalog_byte_for_byte_as_it_was(library, tmp_path):
    """The whole promise of the index in one check."""
    before = Path(library.catalog_path).read_bytes()
    with Index.open(tmp_path / "index.db") as index:
        scan([library.catalog_path], index)
    assert Path(library.catalog_path).read_bytes() == before


def test_the_folder_tool_does_not_import_the_index():
    """The guard that keeps a fault here away from the photographs.

    Importing the command line must not drag the index in: a bug in this
    package cannot then reach the code that moves files, however badly it
    misbehaves.
    """
    code = (
        "import sys; import lrcompanion.cli, lrcompanion.planner, "
        "lrcompanion.executor, lrcompanion.folders; "
        "print([m for m in sys.modules if m.startswith('lrcompanion.metasearch')])"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]", out.stdout


# -- what the scan records ---------------------------------------------------


def test_the_scan_records_photographs_keywords_and_exif(filled):
    counts = filled.counts()
    assert counts["catalogs"] == 1
    assert counts["photos"] == 3
    assert counts["keywords"] == 2

    row = filled.db.execute(
        "select camera, iso, aperture, shutter, width, rating from photos where base_name = 'A0001'"
    ).fetchone()
    assert row["camera"] == "Canon EOS 70D"
    assert row["iso"] == 800
    # APEX in the catalog, f-numbers and seconds for people.
    assert row["aperture"] == pytest.approx(2.0, abs=0.01)
    assert row["shutter"] == pytest.approx(1 / 32, abs=0.001)
    assert row["width"] == 6000
    assert row["rating"] == 4


def test_every_keyword_of_a_photograph_is_kept(filled):
    """Regression: the second keyword of any photograph used to be lost.

    The photo's row id was read from the cursor *after* the first keyword had
    been inserted, by which time it named the keyword row instead -- so every
    catalog that used keywords failed on a foreign key, which was all of them.
    """
    rows = filled.db.execute(
        "select k.keyword from photo_keywords k join photos p on p.id = k.photo"
        " where p.base_name = 'A0001' order by k.keyword"
    ).fetchall()
    assert [r[0] for r in rows] == ["Portrait", "Urlaub"]


def test_a_catalog_that_cannot_be_read_leaves_nothing_behind(tmp_path):
    """Half a library in the index is worse than none: the gap is invisible."""
    broken = tmp_path / "broken.lrcat"
    broken.write_bytes(b"this is not a database")
    with Index.open(tmp_path / "index.db") as index:
        outcomes = scan([broken], index)
        assert [o.state for o in outcomes] == ["failed"]
        assert index.counts()["catalogs"] == 0


def test_an_index_from_another_revision_is_refused(tmp_path):
    path = tmp_path / "old.db"
    with Index.open(path) as index:
        index.db.execute("update meta set value = '999' where key = 'version'")
        index.db.commit()
    with pytest.raises(IndexError_):
        Index.open(path)


# -- copies of catalogs ------------------------------------------------------


def test_a_copy_of_a_catalog_is_recognised_as_one(library, tmp_path):
    """By the photo UUIDs it carries, not by its name, size or count."""
    original = Path(library.catalog_path)
    elsewhere = tmp_path / "backup"
    elsewhere.mkdir()
    copy = elsewhere / "quite-different-name.lrcat"
    shutil.copy2(original, copy)

    with Index.open(tmp_path / "index.db") as index:
        outcomes = scan([original, copy], index)
        states = sorted(o.state for o in outcomes)
        assert states == ["copy", "read"]
        assert index.counts()["catalogs"] == 1
        assert len(duplicates.catalog_copies(index)) == 1


def test_a_copy_that_has_since_grown_is_still_matched(library, tmp_path):
    """The fingerprint is a sample in a stable order, on purpose.

    Two real catalogs differed by two photographs out of 3,296 and were the
    same library; comparing everything would have called them unrelated.
    """
    original = Path(library.catalog_path)
    copy = tmp_path / "older.lrcat"
    shutil.copy2(original, copy)
    library.add_photo("C0001.CR2", "2021-02-02T12:00:00")

    with Index.open(tmp_path / "index.db") as index:
        outcomes = scan([original, copy], index)
        assert sorted(o.state for o in outcomes) == ["copy", "read"]
        # The one with more photographs is the surviving state of the two.
        kept = index.catalogs()[0]
        assert kept.images == 4


# -- searching ---------------------------------------------------------------


def test_searching_by_keyword_and_rating(filled):
    hits = query.search(filled, query.Filter(keywords=("Urlaub",)))
    assert sorted(h.file_name for h in hits) == ["A0001.CR2", "A0002.CR2"]

    starred = query.search(filled, query.Filter(keywords=("Urlaub",), min_rating=4))
    assert [h.file_name for h in starred] == ["A0001.CR2"]


def test_searching_by_camera_and_date(filled):
    assert len(query.search(filled, query.Filter(camera="Nikon"))) == 1
    assert len(query.search(filled, query.Filter(since="2020-01-01"))) == 1
    assert len(query.search(filled, query.Filter(until="2019-12-31"))) == 2


def test_an_empty_filter_is_recognisable_as_empty(filled):
    assert query.Filter().is_empty
    assert not query.Filter(camera="x").is_empty


def test_the_keyword_list_counts_photographs(filled):
    assert dict(query.keywords(filled)) == {"Urlaub": 2, "Portrait": 1}


# -- sameness ----------------------------------------------------------------


def test_the_same_file_in_two_libraries_is_found(builder, tmp_path):
    second = tmp_path / "other"
    second.mkdir()
    from conftest import CatalogBuilder

    other = CatalogBuilder(second, catalog_name="second.lrcat")
    for catalog in (builder, other):
        file_id = catalog.add_photo("SHARED.CR2", "2019-05-05T10:00:00", camera="Canon EOS 70D")
        catalog.set_size(file_id, 6000, 4000)
    other.close()

    with Index.open(tmp_path / "index.db") as index:
        scan([builder.catalog_path, other.catalog_path], index)
        groups = duplicates.identical(index, across_catalogs_only=True)
        assert len(groups) == 1
        assert groups[0].spans_catalogs
        assert groups[0].wasted == 1


def test_a_virtual_copy_is_not_reported_as_a_duplicate(builder, tmp_path):
    """It shares its file with its master; counting it would report every edit."""
    file_id = builder.add_photo("V0001.CR2", "2019-05-05T10:00:00", virtual_copies=2)
    builder.set_size(file_id, 6000, 4000)
    with Index.open(tmp_path / "index.db") as index:
        scan([builder.catalog_path], index)
        assert duplicates.identical(index) == []


# -- reducing a catalog ------------------------------------------------------


def test_a_reduced_catalog_keeps_only_the_selection(filled, library, tmp_path):
    hits = query.search(filled, query.Filter(keywords=("Portrait",)))
    assert len(hits) == 1
    target = tmp_path / "out"
    results = subset.build(filled, [h.photo_id for h in hits], target)

    assert len(results) == 1
    assert results[0].kept == 1
    assert results[0].removed == 2

    made = sqlite3.connect(str(results[0].target))
    names = [r[0] for r in made.execute("select baseName from AgLibraryFile")]
    made.close()
    assert names == ["A0001"]


def test_reducing_never_writes_to_the_original(filled, library, tmp_path):
    before = Path(library.catalog_path).read_bytes()
    hits = query.search(filled, query.Filter(keywords=("Portrait",)))
    subset.build(filled, [h.photo_id for h in hits], tmp_path / "out")
    assert Path(library.catalog_path).read_bytes() == before


def test_a_reduced_catalog_is_one_file_and_not_three(filled, tmp_path):
    """A stray -wal beside it makes the result look unfinished, and can be."""
    hits = query.search(filled, query.Filter(keywords=("Portrait",)))
    target = tmp_path / "out"
    subset.build(filled, [h.photo_id for h in hits], target)
    assert sorted(p.name for p in target.iterdir()) == ["test.lrcat"]


def test_reducing_refuses_to_overwrite(filled, tmp_path):
    hits = query.search(filled, query.Filter(keywords=("Portrait",)))
    target = tmp_path / "out"
    subset.build(filled, [h.photo_id for h in hits], target)
    with pytest.raises(subset.SubsetError):
        subset.build(filled, [h.photo_id for h in hits], target)


# -- drives ------------------------------------------------------------------


def test_a_drive_is_identified_by_something_other_than_its_name(tmp_path):
    volume = describe(tmp_path)
    assert volume.identity
    assert volume.kind in (BY_UUID, BY_FINGERPRINT)
    # Whatever it is, it must not simply be the label.
    assert volume.identity != volume.label


def test_finding_catalogs_ignores_appledouble_companions(tmp_path):
    (tmp_path / "real.lrcat").write_bytes(b"")
    (tmp_path / "._real.lrcat").write_bytes(b"")
    found = find_catalogs([tmp_path])
    assert [p.name for p in found] == ["real.lrcat"]
