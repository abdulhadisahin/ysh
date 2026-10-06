"""Compact immutable reference data from Türk Loydu Bölüm 8, Tablo 8.9."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Table89Row:
    material: str
    class_i_a: str
    class_i_b: str
    class_ii_iii_a: str
    class_ii_iii_b: str


TABLE_8_9_ROWS = (
    Table89Row("Alaşımsız ve alaşımlı karbon çeliği", "2,7", "1,6", "2,7", "1,8"),
    Table89Row("Haddelenmiş ve dövme paslanmaz çelik", "2,4", "1,6", "2,4", "1,8"),
    Table89Row("Çelik, akma mukavemeti > 400 N/mm²", "3,0", "1,7", "3,0", "1,8"),
    Table89Row("Kır dökme demir", "-", "-", "11,0", "-"),
    Table89Row("Nodüler dökme demir", "-", "-", "5,0", "3,0"),
    Table89Row("Çelik döküm", "3,2", "-", "4,0", "-"),
)

TABLE_8_9_FOOTNOTE = "Akma mukavemeti > 400 N/mm² çelik için ölçüt, 20°C'deki asgari akma mukavemeti veya %0,2 uzama sınırıdır."
