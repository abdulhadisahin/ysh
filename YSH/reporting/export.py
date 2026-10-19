"""Collision-safe Windows report export independent of Tk."""
from __future__ import annotations
from pathlib import Path
import re
from reporting.models import EngineeringReport


def default_filename(report: EngineeringReport) -> str:
    """Use frozen identity because project display names are not stored in schema 1."""
    name = f'D243_{report.snapshot_id[:8]}_{report.module}_{report.created_at:%Y%m%d_%H%M%S}'
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).rstrip(' .') + '.pdf'


def export_pdf(report: EngineeringReport, output: Path | str) -> Path:
    """Create exclusively; collisions receive suffixes and failed writes are removed."""
    from reporting.renderer import render_pdf
    target = Path(output)
    if target.suffix.lower() != '.pdf':
        target = target.with_suffix('.pdf')
    data = render_pdf(report)
    for index in range(10000):
        candidate = target if not index else target.with_name(f'{target.stem}_{index}{target.suffix}')
        try:
            stream = candidate.open('xb')
        except FileExistsError:
            continue
        try:
            with stream:
                stream.write(data)
        except BaseException:
            candidate.unlink(missing_ok=True)
            raise
        return candidate
    raise FileExistsError('Rapor adı için boş sıra bulunamadı.')
