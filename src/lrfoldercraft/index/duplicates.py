"""Finding the same photograph twice, and finding near misses.

Two questions that look alike and are not:

* **Sameness** is answerable from the catalogs alone -- capture time, camera,
  file name and pixel size together. It therefore works with every drive in a
  cupboard, which is the whole point of having an index.
* **Nearness** -- a burst, a bracket, a raw beside its JPEG -- is also
  answerable from the catalogs, because those photographs differ in ways the
  catalog records.

What is *not* here is visual similarity: telling two different frames apart by
what they show. That needs the pixels, and reading the pixels of a raw file
needs a decoder this tool does not ship and would rather not. Rather than offer
a weak version of it under a name that promises more, the limit is stated.

SPDX-License-Identifier: MIT OR GPL-3.0-or-later
"""

from __future__ import annotations

from typing import NamedTuple

from .store import Index


class Copy(NamedTuple):
    """One photograph inside a group that exists more than once."""

    catalog: str
    volume: str
    folder: str
    file_name: str
    capture_time: str


class Group(NamedTuple):
    """A set of photographs the index believes to be the same, or near it."""

    key: str
    reason: str
    members: list[Copy]

    @property
    def spans_catalogs(self) -> bool:
        return len({m.catalog for m in self.members}) > 1

    @property
    def wasted(self) -> int:
        """How many of the members are surplus."""
        return len(self.members) - 1


MEMBERS = """
select c.name, v.label, p.folder,
       p.base_name || '.' || coalesce(p.extension, ''), coalesce(p.capture_time, '')
from photos p
join catalogs c on c.id = p.catalog
join volumes  v on v.identity = c.volume
where p.sameness = ? and c.superseded_by is null
order by c.name, p.folder
"""


def identical(index: Index, across_catalogs_only: bool = False, limit: int = 0) -> list[Group]:
    """Photographs that are the same file, however many places it sits in."""
    sql = (
        "select p.sameness, count(*) n, count(distinct p.catalog) c"
        " from photos p join catalogs cat on cat.id = p.catalog"
        " where p.sameness is not null and cat.superseded_by is null"
        " group by p.sameness having n > 1"
    )
    if across_catalogs_only:
        sql += " and c > 1"
    sql += " order by n desc"
    if limit:
        sql += " limit {n}".format(n=int(limit))

    groups = []
    for key, _n, _c in index.db.execute(sql).fetchall():
        members = [Copy(*row) for row in index.db.execute(MEMBERS, (key,))]
        if len(members) > 1:
            groups.append(Group(key, "same file", members))
    return groups


def catalog_copies(index: Index) -> list[tuple[str, str, str, str]]:
    """The catalogs the scan judged to be copies of another, and of which."""
    return [
        (row[0], row[1], row[2], row[3])
        for row in index.db.execute(
            "select c.name, c.full_path, coalesce(k.full_path, ''), coalesce(c.note, '')"
            " from catalogs c left join catalogs k on k.id = c.superseded_by"
            " where c.superseded_by is not null order by c.name"
        )
    ]


NEAR = """
select p.camera, p.width, p.height,
       strftime('%Y-%m-%dT%H:%M', p.capture_time) as minute,
       count(*) n
from photos p
join catalogs c on c.id = p.catalog and c.superseded_by is null
where p.capture_time is not null and p.camera is not null and p.is_copy = 0
group by p.camera, p.width, p.height, minute
having n > 1
order by n desc
"""


def near(index: Index, limit: int = 0) -> list[Group]:
    """Frames taken in the same minute, by the same camera, at the same size.

    A burst, a bracket, or the same scene shot twice. Not the same file -- the
    exact duplicates are reported by :func:`identical` and are excluded here,
    so a group means "worth a look", not "delete one".
    """
    sql = NEAR + (" limit {n}".format(n=int(limit)) if limit else "")
    groups = []
    for camera, width, height, minute, _n in index.db.execute(sql).fetchall():
        rows = index.db.execute(
            "select c.name, v.label, p.folder,"
            " p.base_name || '.' || coalesce(p.extension, ''), coalesce(p.capture_time, '')"
            " from photos p join catalogs c on c.id = p.catalog and c.superseded_by is null"
            " join volumes v on v.identity = c.volume"
            " where p.camera = ? and p.width is ? and p.height is ?"
            " and strftime('%Y-%m-%dT%H:%M', p.capture_time) = ? and p.is_copy = 0"
            " order by p.capture_time",
            (camera, width, height, minute),
        ).fetchall()
        members = [Copy(*row) for row in rows]
        # A group whose members are all the same file is an exact duplicate,
        # which the other report already covers.
        if len({m.file_name for m in members}) > 1:
            groups.append(
                Group(
                    "{c}|{m}".format(c=camera, m=minute),
                    "same camera, same minute, same size",
                    members,
                )
            )
    return groups


def summary(index: Index) -> dict:
    """The headline numbers, for a report that has to fit on a screen."""
    exact = identical(index)
    return {
        "groups": len(exact),
        "surplus": sum(g.wasted for g in exact),
        "across_catalogs": sum(1 for g in exact if g.spans_catalogs),
        "catalog_copies": len(catalog_copies(index)),
    }
