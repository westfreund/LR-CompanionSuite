"""Asking the index questions.

Everything here reads. The point of the index is that these answers come back
with the drives in a cupboard, so nothing in this module may touch a catalog or
a photograph.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

from typing import NamedTuple, Optional

from .store import Index


class Filter(NamedTuple):
    """What to look for. Every field left empty means "do not care"."""

    keywords: tuple[str, ...] = ()  # every one of them must be present
    any_keywords: tuple[str, ...] = ()  # at least one of them
    text: str = ""  # file name or folder contains this
    camera: str = ""
    lens: str = ""
    catalog: str = ""
    extension: str = ""
    since: str = ""  # capture date, inclusive, "YYYY-MM-DD"
    until: str = ""
    min_rating: int = 0
    with_gps: bool = False
    include_copies: bool = False  # virtual copies
    include_superseded: bool = False  # photographs in catalogs known to be copies
    limit: int = 0

    @property
    def is_empty(self) -> bool:
        return not any(
            [
                self.keywords,
                self.any_keywords,
                self.text,
                self.camera,
                self.lens,
                self.catalog,
                self.extension,
                self.since,
                self.until,
                self.min_rating,
                self.with_gps,
            ]
        )


class Hit(NamedTuple):
    photo_id: int
    catalog: str
    catalog_path: str
    volume: str
    volume_attached: bool
    folder: str
    file_name: str
    capture_time: str
    camera: str
    rating: int
    keywords: str


def _where(criteria: Filter) -> tuple[str, list]:
    clauses: list[str] = []
    params: list = []

    if not criteria.include_superseded:
        clauses.append("c.superseded_by is null")
    if not criteria.include_copies:
        clauses.append("p.is_copy = 0")
    if criteria.text:
        clauses.append("(p.base_name like ? or p.folder like ?)")
        params += ["%{t}%".format(t=criteria.text)] * 2
    if criteria.camera:
        clauses.append("p.camera like ?")
        params.append("%{t}%".format(t=criteria.camera))
    if criteria.lens:
        clauses.append("p.lens like ?")
        params.append("%{t}%".format(t=criteria.lens))
    if criteria.catalog:
        clauses.append("c.name like ?")
        params.append("%{t}%".format(t=criteria.catalog))
    if criteria.extension:
        clauses.append("lower(p.extension) = ?")
        params.append(criteria.extension.lower().lstrip("."))
    if criteria.since:
        clauses.append("p.capture_time >= ?")
        params.append(criteria.since)
    if criteria.until:
        # Inclusive of the whole day named.
        clauses.append("p.capture_time <= ?")
        params.append(criteria.until + "T23:59:59")
    if criteria.min_rating:
        clauses.append("coalesce(p.rating, 0) >= ?")
        params.append(criteria.min_rating)
    if criteria.with_gps:
        clauses.append("p.latitude is not null")
    for keyword in criteria.keywords:
        clauses.append(
            "exists (select 1 from photo_keywords k where k.photo = p.id and k.keyword like ?)"
        )
        params.append(keyword)
    if criteria.any_keywords:
        marks = ", ".join("?" for _ in criteria.any_keywords)
        clauses.append(
            "exists (select 1 from photo_keywords k where k.photo = p.id"
            " and k.keyword in ({m}))".format(m=marks)
        )
        params += list(criteria.any_keywords)

    return (" where " + " and ".join(clauses) if clauses else ""), params


SELECT = """
select p.id, c.name, c.full_path, v.label, v.mount, p.folder,
       p.base_name || '.' || coalesce(p.extension, ''), coalesce(p.capture_time, ''),
       coalesce(p.camera, ''), coalesce(p.rating, 0),
       (select group_concat(k.keyword, ', ') from photo_keywords k where k.photo = p.id)
from photos p
join catalogs c on c.id = p.catalog
join volumes  v on v.identity = c.volume
"""


def search(index: Index, criteria: Filter) -> list[Hit]:
    """Every photograph matching *criteria*, newest capture first."""
    import os

    clause, params = _where(criteria)
    sql = SELECT + clause + " order by p.capture_time desc, p.base_name"
    if criteria.limit:
        sql += " limit ?"
        params.append(criteria.limit)
    hits = []
    attached: dict[str, bool] = {}
    for row in index.db.execute(sql, params):
        mount = row[4] or ""
        if mount not in attached:
            attached[mount] = bool(mount) and os.path.ismount(mount)
        hits.append(
            Hit(
                row[0],
                row[1],
                row[2],
                row[3],
                attached[mount],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
                row[10] or "",
            )
        )
    return hits


def count(index: Index, criteria: Filter) -> int:
    clause, params = _where(criteria)
    sql = "select count(*) from photos p join catalogs c on c.id = p.catalog" + clause
    return int(index.db.execute(sql, params).fetchone()[0])


def keywords(index: Index, like: str = "", limit: int = 0) -> list[tuple[str, int]]:
    """Every keyword in the index with how many photographs carry it."""
    sql = (
        "select k.keyword, count(*) n from photo_keywords k"
        " join photos p on p.id = k.photo"
        " join catalogs c on c.id = p.catalog and c.superseded_by is null"
    )
    params: list = []
    if like:
        sql += " where k.keyword like ?"
        params.append("%{t}%".format(t=like))
    sql += " group by k.keyword order by n desc, k.keyword"
    if limit:
        sql += " limit ?"
        params.append(limit)
    return [(row[0], row[1]) for row in index.db.execute(sql, params)]


def cameras(index: Index) -> list[tuple[str, int]]:
    return [
        (row[0], row[1])
        for row in index.db.execute(
            "select p.camera, count(*) n from photos p"
            " join catalogs c on c.id = p.catalog and c.superseded_by is null"
            " where p.camera is not null group by 1 order by n desc"
        )
    ]


def where_is(index: Index, file_name: str) -> list[Hit]:
    """Find one file by name, wherever it is -- the everyday question."""
    return search(index, Filter(text=file_name, include_superseded=True, limit=200))


def volume_of(index: Index, photo_id: int) -> Optional[str]:
    row = index.db.execute(
        "select v.label from photos p join catalogs c on c.id = p.catalog"
        " join volumes v on v.identity = c.volume where p.id = ?",
        (photo_id,),
    ).fetchone()
    return row[0] if row else None
