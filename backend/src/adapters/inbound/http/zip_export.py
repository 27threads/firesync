import csv
from io import BytesIO, TextIOWrapper
import json
from zipfile import ZipFile, ZIP_DEFLATED


def audit_zip(files, metadata):
    output = BytesIO()
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name, (fields, rows) in files.items():
            # Rows go straight into the compressed entry: detections.csv can hold up to 500,000 of them.
            with archive.open(name, 'w') as raw, TextIOWrapper(raw, encoding='utf-8-sig', newline='') as text:
                writer = csv.DictWriter(text, fieldnames=fields, extrasaction='ignore')
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: str(value).lower() if isinstance(value, bool) else value
                                     for key, value in row.items()})
        archive.writestr('metadata.json', json.dumps(metadata, ensure_ascii=False, allow_nan=False, indent=2))
    return output.getvalue()
