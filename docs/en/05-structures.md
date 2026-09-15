# Folder structures and tokens

**Revision r18.0.0 · Build date 2026-08-30**

A **structure** is an ordered list of **levels**. Each level becomes one
directory, and each level is a **template** made of literal text and
placeholders in curly braces.

```
["{yyyy}", "{mm}", "{dd}"]                 ->  2019/01/03
["{camera_slug}", "{yyyy}-W{iso_week}"]    ->  canon-eos-70d/2019-W01
["{yyyy}-{mm}-{dd}"]                       ->  2019-01-03
```

On the command line the levels are separated by `/`:

```bash
lrfc plan CATALOG -s '{yyyy}/{mm}/{dd}'
lrfc plan CATALOG -s '{camera_slug}/{yyyy}-W{iso_week}'
```

Multiple grouping levels are simply multiple entries — there is no depth limit.

## Presets

| Preset | Example | Meaning |
| --- | --- | --- |
| `day` | `2019-01-03` | One folder per capture day |
| `year/day` | `2019/2019-01-03` | Year folder, day folders inside |
| `year/month/day` | `2019/01/03` | Classic three level date tree |
| `year/month` | `2019/01` | Year folder, month folders inside |
| `year-month` | `2019-01` | One folder per month |
| `year/week` | `2019/W01` | Year folder, ISO week folders inside |
| `iso-week` | `2019-W01` | One folder per ISO calendar week |
| `year/month-name` | `2019/01 January` | Year folder, numbered month names |
| `camera/day` | `canon-eos-70d/2019-01-03` | Camera folder, day folders inside |
| `day/camera` | `2019-01-03/canon-eos-70d` | Day folder, camera folders inside |
| `camera/year/month/day` | `canon-eos-70d/2019/01/03` | Camera, then full date tree |
| `year/quarter/month` | `2019/Q1/01` | Year, quarter, month |

`lrfc presets` prints this table with live examples. A preset is just a
shorthand — anything a preset does you can also write out yourself.

## Tokens

### Date and time

Values come from the photo's capture time (see
[04-usage.md](04-usage.md#photos-without-a-capture-date) for how that is resolved).

| Token | Example | Meaning |
| --- | --- | --- |
| `{yyyy}` | `2019` | Four digit year |
| `{yy}` | `19` | Two digit year |
| `{mm}` | `01` | Month, zero padded |
| `{m}` | `1` | Month, no padding |
| `{dd}` | `03` | Day, zero padded |
| `{d}` | `3` | Day, no padding |
| `{hh}` | `17` | Hour, 24h zero padded |
| `{mi}` | `42` | Minute, zero padded |
| `{month_name}` | `January` | Full month name |
| `{month_short}` | `Jan` | Abbreviated month name |
| `{quarter}` | `Q1` | Calendar quarter |
| `{iso_week}` | `01` | ISO-8601 calendar week, zero padded |
| `{iso_year}` | `2019` | ISO-8601 week-numbering year |
| `{weekday}` | `Thursday` | Full weekday name |
| `{weekday_short}` | `Thu` | Abbreviated weekday name |
| `{doy}` | `003` | Day of year, zero padded |

### Camera and lens

| Token | Example | Meaning |
| --- | --- | --- |
| `{camera}` | `Canon EOS 70D` | Camera model as stored by Lightroom |
| `{camera_slug}` | `canon-eos-70d` | Camera model, lower case and hyphenated |
| `{camera_sn}` | `053022010127` | Camera serial number |
| `{lens}` | `EF-S18-55mm f/3.5-5.6 IS STM` | Lens as stored by Lightroom |
| `{lens_slug}` | `ef-s18-55mm-f-3-5-5-6-is-stm` | Lens, lower case and hyphenated |

### File

| Token | Example | Meaning |
| --- | --- | --- |
| `{format}` | `RAW` | Lightroom file format class |
| `{ext}` | `CR2` | File extension, upper case |
| `{ext_lower}` | `cr2` | File extension, lower case |
| `{orig_folder}` | `raw2019` | Name of the folder the file is in today |
| `{folder_label}` | `Makro Blume im Garten` | Text after the date in that folder's name, empty if none |

`lrfc tokens` prints the same reference. `--lang de` gives German descriptions.

## Language

`{month_name}`, `{month_short}`, `{weekday}` and `{weekday_short}` follow
`--lang`:

```bash
lrfc plan CATALOG -s '{yyyy}/{mm} {month_name}'              # 2019/01 January
lrfc plan CATALOG -s '{yyyy}/{mm} {month_name}' --lang de    # 2019/01 Januar
```

The names are built in, so no system locale has to be installed.

## ISO calendar weeks

`{iso_week}` and `{iso_year}` follow ISO 8601, where a week belongs to the year
that contains its Thursday. Around New Year that matters:

| Date | `{yyyy}` | `{iso_year}` | `{iso_week}` |
| --- | --- | --- | --- |
| 2019-12-29 | 2019 | 2019 | 52 |
| 2019-12-30 | 2019 | **2020** | **01** |
| 2020-01-01 | 2020 | 2020 | 01 |

Always pair `{iso_week}` with `{iso_year}`, never with `{yyyy}` — otherwise
photos from 30 December 2019 land in a folder called `2019-W01`, next to
photos from early January 2019.

```bash
lrfc plan CATALOG -s '{iso_year}-W{iso_week}'      # correct
lrfc plan CATALOG -s '{yyyy}-W{iso_week}'          # surprising at year end
```

## Name sanitising

Rendered names are made safe for every supported platform, in this order:

1. optional ASCII folding (`--ascii`): `Grün` → `Grun`
2. characters illegal on at least one OS (`< > : " / \ | ? *` and control
   characters) become `-`
3. runs of whitespace collapse to a single space, the result is trimmed
4. trailing dots and spaces are removed — Windows silently drops them
5. Windows device names get an underscore: `CON` → `_CON`
6. names longer than 100 characters are truncated
7. an empty result becomes `unnamed`

This runs on macOS and Linux too, so a library stays portable.

## Missing metadata

A token whose value is unknown does not produce an empty folder name:

| Token | Fallback |
| --- | --- |
| `{camera}` | `Unknown Camera` |
| `{camera_slug}` | `unknown-camera` |
| `{camera_sn}` | `unknown-sn` |
| `{lens}` | `Unknown Lens` |
| date tokens | the photo goes to `_unsorted`, see `--on-missing-date` |

## Worked examples

```bash
# one folder per day, inside the year folder you already have
lrfc apply CATALOG -s day

# classic three level tree
lrfc apply CATALOG -s year/month/day

# German month names, day with weekday
lrfc apply CATALOG -s '{yyyy}/{mm} {month_name}/{dd} {weekday_short}' --lang de

# separate the two bodies you shot with, then by day
lrfc apply CATALOG -s '{camera_slug}/{yyyy}-{mm}-{dd}'

# by camera serial number -- useful with two identical bodies
lrfc apply CATALOG -s '{camera}-{camera_sn}/{yyyy}-{mm}-{dd}'

# calendar weeks, correctly
lrfc apply CATALOG -s '{iso_year}/W{iso_week}'

# raw and JPEG apart
lrfc apply CATALOG -s '{yyyy}-{mm}-{dd}/{format}'

# quarters for a business archive
lrfc apply CATALOG -s '{yyyy}/{quarter}/{mm}'
```

Always run `plan` first and read the target folder list.



### ASCII names

`--ascii` (the *ASCII names* box in the window) restricts folder names to plain
ASCII, for a drive or a backup target that cannot carry anything else.

Letters an accent cannot carry are **spelled out** rather than dropped:

| | |
| --- | --- |
| `Völki` | `Voelki` |
| `Tabaksmühle` | `Tabaksmuehle` |
| `Straße` | `Strasse` |
| `MÜNCHEN` | `MUENCHEN` — an all-caps word stays all caps |
| `Ærø` | `Aeroe` |
| `Café`, `Señor` | `Cafe`, `Senor` — here dropping the mark *is* the romanisation |

Covered: ä ö ü ß æ ø œ å þ ð đ ł ı and their capitals. Everything else keeps
its base letter, which is correct for French, Spanish, Polish accents and the
rest.

## Date levels that name the whole date

By default `{yyyy}/{mm}/{dd}` builds `2019/01/03`: each level names only its
own part. Switch **cumulative dates** on and it builds

```
2019/2019-01/2019-01-03
```

Every folder name is then complete on its own — a folder still says which day
it is when it turns up in a search result, a file dialog, or dragged out of its
tree.

```bash
lrfc plan CATALOG -s year/month/day --cumulative-dates
```

In the window it is the checkbox **"Every date level names the whole date"**,
and the live preview shows the cumulative form as soon as it is ticked.

Only date levels take part. `{camera_slug}/{yyyy}/{mm}` becomes
`{camera_slug}/{yyyy}/{yyyy}-{mm}` — the camera is not a date and is not
repeated. A level that already spells the whole date gains nothing, because
each level inherits only from the date levels **above** it.

The structure you typed is kept as you typed it: turning the option off gives
back exactly `{yyyy}/{mm}/{dd}`. Two presets have it built in if you would
rather not use the switch:

| Preset | Result |
| --- | --- |
| `year/year-month/full-day` | `2019/2019-01/2019-01-03` |
| `year/full-day` | `2019/2019-01-03` |

## Levels that render empty

A level whose tokens all render to nothing is **dropped**, not turned into a
folder called `unnamed`. This is what makes `{folder_label}` usable as a level
of its own:

| Folder the photo is in | `{yyyy}-{mm}-{dd}/{folder_label}` gives |
| --- | --- |
| `2026-06-28 Makro Blume im Garten` | `2026-06-28/Makro Blume im Garten` |
| `2026-06-28` | `2026-06-28` |
| `raw2020` | `2020-01-03` |

The same holds anywhere in the structure: `{yyyy}/{folder_label}/{mm}-{dd}`
collapses to `2026/06-28` when there is no text to place.

A structure whose levels *all* render empty puts the photo at the anchor
itself. `{folder_label}` alone is therefore a structure that files everything
without a folder label into one directory — legal, rarely what anyone means.
