"""The index file itself: what it holds and how to put things in it.

One SQLite file, three layers -- drives, the catalogs on them, and the photos
in those. It is a *snapshot*: every catalog row carries the moment it was read,
because an index that cannot say how old it is claims a currency it does not
have.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, NamedTuple, Optional

from ..logging_setup import get_logger
from . import default_index_path
from .volumes import Volume

log = get_logger("index.store")

#: Bumped when a column changes meaning. An older file is refused rather than
#: misread -- the alternative is answers that are quietly wrong.
INDEX_VERSION = 1

SCHEMA = """
create table if not exists meta (
    key   text primary key,
    value text
);

create table if not exists volumes (
    identity     text primary key,
    kind         text not null,          -- 'uuid' or 'fingerprint'
    label        text,
    mount        text,
    filesystem   text,
    total_bytes  integer,
    last_seen    text
);

create table if not exists catalogs (
    id             integer primary key,
    volume         text not null references volumes(identity),
    relative_path  text not null,        -- below the mount point, so it survives remounting
    full_path      text not null,        -- as seen when last read, for the human
    name           text not null,
    fingerprint    text,                 -- identifies a copy of the same catalog
    images         integer default 0,
    keywords       integer default 0,
    schema_version text,
    last_read      text,
    superseded_by  integer references catalogs(id),
    note           text,
    unique (volume, relative_path)
);

create table if not exists photos (
    id            integer primary key,
    catalog       integer not null references catalogs(id) on delete cascade,
    local_id      integer not null,      -- Adobe_images.id_local, to address it later
    uuid          text,                  -- Adobe_images.id_global
    folder        text,
    base_name     text,
    extension     text,
    capture_time  text,
    camera        text,
    lens          text,
    iso           integer,
    focal_length  real,
    aperture      real,                  -- f-number, already converted from APEX
    shutter       real,                  -- seconds, already converted from APEX
    width         integer,
    height        integer,
    file_format   text,
    rating        integer,
    color_label   text,
    latitude      real,
    longitude     real,
    is_copy       integer default 0,     -- a virtual copy
    sameness      text                   -- the key two identical photographs share
);

create table if not exists photo_keywords (
    photo   integer not null references photos(id) on delete cascade,
    keyword text not null
);

create table if not exists catalog_sample (
    catalog integer not null references catalogs(id) on delete cascade,
    uuid    text not null
);

create index if not exists sample_by_uuid    on catalog_sample(uuid);
create index if not exists sample_by_catalog on catalog_sample(catalog);
create index if not exists photos_by_catalog  on photos(catalog);
create index if not exists photos_by_sameness on photos(sameness);
create index if not exists photos_by_name     on photos(base_name);
create index if not exists photos_by_capture  on photos(capture_time);
create index if not exists photos_by_camera   on photos(camera);
create index if not exists keywords_by_name   on photo_keywords(keyword);
create index if not exists keywords_by_photo  on photo_keywords(photo);
"""


class IndexError_(Exception):
    """The index file cannot be used as it is."""


class CatalogRow(NamedTuple):
    id: int
    volume: str
    full_path: str
    name: str
    fingerprint: str
    images: int
    keywords: int
    last_read: str
    superseded_by: Optional[int]
    volume_label: str
    volume_kind: str


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Index:
    """An open index file."""

    def __init__(self, path: Path, connection: sqlite3.Connection):
        self.path = path
        self.db = connection
        self.db.row_factory = sqlite3.Row

    # -- lifecycle ------------------------------------------------------

    @classmethod
    def open(cls, path: Optional[str | Path] = None, create: bool = True) -> Index:
        target = Path(path).expanduser() if path else default_index_path()
        if not target.exists() and not create:
            raise IndexError_("no index at {p}".format(p=target))
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(target))
        connection.execute("pragma foreign_keys = on")
        index = cls(target, connection)
        index._prepare()
        return index

    def _prepare(self) -> None:
        self.db.executescript(SCHEMA)
        row = self.db.execute("select value from meta where key = 'version'").fetchone()
        if row is None:
            self.db.execute(
                "insert into meta (key, value) values ('version', ?)", (str(INDEX_VERSION),)
            )
            self.db.commit()
            return
        if int(row[0]) != INDEX_VERSION:
            raise IndexError_(
                "the index at {p} was written by another revision (version {v}); "
                "delete it and scan again".format(p=self.path, v=row[0])
            )

    def close(self) -> None:
        self.db.commit()
        self.db.close()

    def __enter__(self) -> Index:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- writing --------------------------------------------------------

    def remember_volume(self, volume: Volume) -> None:
        self.db.execute(
            "insert into volumes (identity, kind, label, mount, filesystem, total_bytes, last_seen)"
            " values (?, ?, ?, ?, ?, ?, ?)"
            " on conflict(identity) do update set"
            "   label = excluded.label, mount = excluded.mount,"
            "   filesystem = excluded.filesystem, total_bytes = excluded.total_bytes,"
            "   last_seen = excluded.last_seen",
            (
                volume.identity,
                volume.kind,
                volume.label,
                volume.mount,
                volume.filesystem,
                volume.total_bytes,
                now(),
            ),
        )

    def forget_catalog(self, volume: str, relative_path: str) -> None:
        """Drop what was previously known about this catalog, before re-reading."""
        row = self.db.execute(
            "select id from catalogs where volume = ? and relative_path = ?",
            (volume, relative_path),
        ).fetchone()
        if row is None:
            return
        self.db.execute(
            "delete from photo_keywords where photo in (select id from photos where catalog = ?)",
            (row[0],),
        )
        self.db.execute("delete from photos where catalog = ?", (row[0],))
        self.db.execute("delete from catalog_sample where catalog = ?", (row[0],))
        self.db.execute("delete from catalogs where id = ?", (row[0],))

    def add_catalog(
        self,
        volume: str,
        relative_path: str,
        full_path: str,
        name: str,
        fingerprint: str,
        images: int,
        keywords: int,
        schema_version: str,
        note: str = "",
    ) -> int:
        cursor = self.db.execute(
            "insert into catalogs (volume, relative_path, full_path, name, fingerprint,"
            " images, keywords, schema_version, last_read, note)"
            " values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                volume,
                relative_path,
                full_path,
                name,
                fingerprint,
                images,
                keywords,
                schema_version,
                now(),
                note,
            ),
        )
        return int(cursor.lastrowid)

    def add_photos(self, catalog_id: int, rows: Iterable[tuple]) -> int:
        """Insert photo rows; returns how many landed.

        Takes an iterable so a catalog with fifty thousand photographs is
        streamed rather than assembled in memory first.
        """
        cursor = self.db.cursor()
        count = 0
        for row in rows:
            cursor.execute(
                "insert into photos (catalog, local_id, uuid, folder, base_name, extension,"
                " capture_time, camera, lens, iso, focal_length, aperture, shutter,"
                " width, height, file_format, rating, color_label, latitude, longitude,"
                " is_copy, sameness)"
                " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (catalog_id,) + row[:21],
            )
            # Read once and held: the next insert moves lastrowid on to the
            # keyword row, and every keyword after the first would then be
            # hung on a photo id that does not exist.
            photo_id = cursor.lastrowid
            for keyword in row[21]:
                cursor.execute(
                    "insert into photo_keywords (photo, keyword) values (?, ?)",
                    (photo_id, keyword),
                )
            count += 1
        return count

    def remember_sample(self, catalog_id: int, uuids: list) -> None:
        """Keep a sample of this catalog's photo UUIDs, to recognise copies."""
        self.db.executemany(
            "insert into catalog_sample (catalog, uuid) values (?, ?)",
            [(catalog_id, str(u)) for u in uuids],
        )

    def find_twin(self, uuids: list, threshold: float = 0.9) -> Optional[int]:
        """A catalog already in the index that shares most of these photographs.

        Overlap rather than equality. A copy and its original drift apart -- two
        real catalogs differed by two photographs out of 3,296 and were plainly
        the same library -- so asking whether the samples are *identical* gets
        the answer wrong exactly when it matters. It also cannot work at all for
        a catalog with fewer photographs than the sample size, where every
        addition changes the sample.
        """
        if not uuids:
            return None
        marks = ",".join("?" for _ in uuids)
        rows = self.db.execute(
            "select cs.catalog, count(*) shared,"
            " (select count(*) from catalog_sample x where x.catalog = cs.catalog) size"
            " from catalog_sample cs where cs.uuid in ({m})"
            " group by cs.catalog order by shared desc".format(m=marks),
            [str(u) for u in uuids],
        ).fetchall()
        for catalog_id, shared, size in rows:
            smaller = min(len(uuids), int(size)) or 1
            if shared / smaller >= threshold:
                return int(catalog_id)
        return None

    def find_twin_excluding(self, uuids: list, catalog_id: int) -> Optional[int]:
        """A twin other than the catalog just written, which matches itself."""
        marks = ",".join("?" for _ in uuids)
        if not uuids:
            return None
        rows = self.db.execute(
            "select cs.catalog, count(*) shared,"
            " (select count(*) from catalog_sample x where x.catalog = cs.catalog) size"
            " from catalog_sample cs where cs.uuid in ({m}) and cs.catalog <> ?"
            " and cs.catalog in (select id from catalogs where superseded_by is null)"
            " group by cs.catalog order by shared desc".format(m=marks),
            [str(u) for u in uuids] + [int(catalog_id)],
        ).fetchall()
        for other, shared, size in rows:
            smaller = min(len(uuids), int(size)) or 1
            if shared / smaller >= 0.9:
                return int(other)
        return None

    def describe_catalog(self, catalog_id: int) -> dict:
        row = self.db.execute(
            "select name, full_path, images from catalogs where id = ?", (catalog_id,)
        ).fetchone()
        return {"name": row[0], "full_path": row[1], "images": int(row[2] or 0)}

    def mark_superseded(self, catalog_id: int, by: int, note: str) -> None:
        self.db.execute(
            "update catalogs set superseded_by = ?, note = ? where id = ?", (by, note, catalog_id)
        )

    # -- reading --------------------------------------------------------

    def catalogs(self, include_superseded: bool = False) -> list[CatalogRow]:
        where = "" if include_superseded else " where c.superseded_by is null"
        rows = self.db.execute(
            "select c.id, c.volume, c.full_path, c.name, c.fingerprint, c.images,"
            " c.keywords, c.last_read, c.superseded_by, v.label, v.kind"
            " from catalogs c join volumes v on v.identity = c.volume" + where + " order by c.name"
        ).fetchall()
        return [CatalogRow(*row) for row in rows]

    def counts(self) -> dict:
        one = self.db.execute(
            "select (select count(*) from volumes),"
            " (select count(*) from catalogs where superseded_by is null),"
            " (select count(*) from catalogs where superseded_by is not null),"
            " (select count(*) from photos),"
            " (select count(distinct keyword) from photo_keywords)"
        ).fetchone()
        return {
            "volumes": one[0],
            "catalogs": one[1],
            "copies": one[2],
            "photos": one[3],
            "keywords": one[4],
        }
