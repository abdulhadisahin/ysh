"""Collision-safe editable DOCX export from the frozen report model."""
from pathlib import Path
import re


def default_word_filename(report):
    project=report.project_name or "Proje"
    name=f"D243_{project}_{report.module}_{report.created_at:%Y%m%d}"
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name).strip(" ._")+'.docx'


def export_word(report, output):
    target=Path(output)
    if target.suffix.lower()!='.docx':target=target.with_suffix('.docx')
    from reporting.word_renderer import render_word
    data=render_word(report)
    for index in range(10000):
        candidate=target if not index else target.with_name(f"{target.stem}_{index}{target.suffix}")
        try:stream=candidate.open('xb')
        except FileExistsError:continue
        try:
            with stream:stream.write(data)
        except BaseException:
            candidate.unlink(missing_ok=True);raise
        return candidate
    raise FileExistsError('Word report name collision limit reached')
