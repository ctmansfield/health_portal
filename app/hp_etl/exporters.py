from typing import Iterable, Mapping, TextIO
import csv
import json


def to_csv(
    rows: Iterable[Mapping[str, object]], fh: TextIO, fieldnames: list[str]
) -> None:
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def to_ndjson(rows: Iterable[Mapping[str, object]], fh: TextIO) -> None:
    for row in rows:
        fh.write(json.dumps(row, separators=(",", ":")))
        fh.write("\n")
