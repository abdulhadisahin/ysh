"""Read-only Library projections; never canonical records or foreign-key choices."""
from dataclasses import dataclass
from uuid import UUID, uuid5, NAMESPACE_URL

from engineering.provenance import SourceReference, SourceType, VerificationStatus


@dataclass(frozen=True, slots=True)
class PropertyView:
    id: UUID
    name_tr: str
    property_name: str
    value: float
    unit: str
    source: str
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED


@dataclass(frozen=True, slots=True)
class SourceView:
    id: UUID
    reference: SourceReference
    publication_date: str | None = None
    verification_date: str | None = None
    source_url: str | None = None
    applicability: str | None = None
    audit_scope: str | None = None
    effective_date: str | None = None
    amendments: str | None = None


def material_properties(materials, existing, parent_id):
    """Expose recorded legacy values without promoting their verification status."""
    occupied = {(r.material_id, r.property_name) for r in existing}
    rows = []
    for material in materials:
        if parent_id is not None and material.id != parent_id:
            continue
        for name, value, unit in (("yield_strength_mpa", material.yield_strength_mpa, "MPa"),
                                  ("roughness", material.roughness_mm, "mm")):
            if value is None or (material.id, name) in occupied:
                continue
            rows.append(PropertyView(uuid5(material.id, 'library-view:'+name),
                material.designation, name, value, unit, material.source))
    return tuple(rows)


def catalog_sources(records, existing):
    """Preserve recorded facts and uncertainty; never infer dates or new sources."""
    seen = {row.reference for row in existing}
    rows = []
    for record in records:
        authority, document = record.source_authority, getattr(record, 'source_document', '')
        if not authority and not document:
            continue
        status = {'VERIFIED': VerificationStatus.VERIFIED,
                  'LIMITED_APPLICABILITY': VerificationStatus.PARTIALLY_VERIFIED}.get(
                      record.verification, VerificationStatus.UNVERIFIED)
        notes = '\n'.join(value for value in (
            getattr(record, 'source_note', ''), getattr(record, 'applicability', ''),
            getattr(record, 'notes', '')) if value)
        reference = SourceReference(
            source_type=SourceType.D243_CRITERION if getattr(record, 'rule_nature', '') == 'D243_CRITERION'
                        else SourceType.ENGINEERING_REFERENCE,
            source_organization=authority or None, document=document or None,
            revision=getattr(record, 'source_edition', '') or None,
            section=getattr(record, 'source_clause', '') or None,
            verification_status=status, notes=notes or None)
        if reference not in seen:
            seen.add(reference)
            from engineering.source_verification import record_evidence
            proof=record_evidence(record)
            rows.append(SourceView(uuid5(NAMESPACE_URL, 'd243:library-source-view:'+repr(reference)), reference,
                proof.publication_date if proof else None, proof.verification_date if proof else None,
                proof.url if proof else None, proof.applicability if proof else None, proof.scope if proof else None,
                proof.effective_date if proof else None, proof.amendments if proof else None))
    return tuple(rows)
