"""Explicitly refreshed engineering library cache; no calculator or UI dependency."""
from repositories.engineering_catalog_repository import FluidSpecificationRepository,MaterialSurfaceRepository,EngineeringRuleRepository
from repositories.fluid_repository import FluidRepository
from repositories.rule_set_repository import RuleSetRepository
from engineering.rule_evaluation import applicable_rules,record_payload
from engineering.catalog_seeds import identity

class EngineeringCatalogService:
    def __init__(self,database):
        self.properties=FluidSpecificationRepository(database);self.surfaces=MaterialSurfaceRepository(database)
        self.rules=EngineeringRuleRepository(database);self.fluid_repository=FluidRepository(database);self.profile_repository=RuleSetRepository(database)
        from repositories.material_repository import MaterialRepository
        self.material_repository=MaterialRepository(database)
        from repositories.material_property_repository import MaterialPropertyRepository
        from repositories.source_repository import SourceRepository
        self.material_properties=MaterialPropertyRepository(database)
        self.sources=SourceRepository(database)
        self.reload()
    def reload(self):
        self.fluid_records=self.fluid_repository.get_all(active_only=True)
        self.property_records=self.properties.get_all(active_only=True)
        self.surface_records=self.surfaces.get_all(active_only=True)
        self.rule_records=self.rules.get_all(active_only=True)
        profile_ids={rule.profile_id for rule in self.rule_records}
        self.profile_records=tuple(r for r in self.profile_repository.get_all() if r.is_active and r.id in profile_ids)
        self.material_records=tuple(self.material_repository.get_all())
        self.material_property_records=tuple(r for material in self.material_records
            for r in self.material_properties.get_by_material(material.id))
        self.source_records={row.id:row.reference for row in self.sources.get_all()}
    def project_fluids(self,family):
        """Filter V6 fluid identities by classification, never by display names.

        Temperature/specification variants stay properties of the same fluid.
        Missing or conflicting classifications are not offered at creation.
        Seawater is outside supported Hazen-Williams project applicability.
        """
        allowed={'fuel':{'DIESEL_FUEL','AVIATION_FUEL','HEAVY_FUEL'},
                 'fire':{'FRESH_WATER'},'seawater':{'SEA_WATER'}}.get(family,set())
        groups={}
        for record in self.property_records:
            groups.setdefault(record.fluid_id,set()).add(record.fluid_group)
        return tuple(fluid for fluid in self.fluid_records
                     if groups.get(fluid.id) and groups[fluid.id]<=allowed)
    def references(self,context):
        active_fluids={row.id for row in self.fluid_records}
        values={row.property_name:record_payload(row) for row in self.property_records if row.fluid_id==context.fluid_id and row.fluid_id in active_fluids}
        seawater=any(r.fluid_id==context.fluid_id and r.fluid_group=='SEA_WATER' for r in self.property_records)
        if seawater:
            for name in tuple(values):
                candidates=[r for r in self.property_records if r.fluid_id==context.fluid_id and r.property_name==name
                    and r.verification=='VERIFIED' and r.source_authority and r.source_document
                    and context.fluid_temperature_c is not None and context.fluid_salinity_g_kg is not None
                    and r.reference_temperature_c==context.fluid_temperature_c
                    and r.reference_salinity_g_kg==context.fluid_salinity_g_kg and r.default_value is not None]
                if len(candidates)==1:
                    values[name]=record_payload(candidates[0])
                else:
                    # Ambiguity or missing condition/source is never last-row-wins.
                    values[name]={**values[name],'default_value':None,'default_method':'SOURCE_REQUIRED',
                        'verification':'SOURCE_REQUIRED'}
        surface=next((r for r in self.surface_records if r.id==context.surface_profile_id),None)
        if surface:
            row=record_payload(surface);row.update(property_name='absolute_roughness',unit='mm',default_value=surface.roughness_mm,
                default_method='ENGINEERING_DEFAULT' if surface.roughness_mm is not None else 'SOURCE_REQUIRED',source_min=None,source_max=None,reference_temperature_c=None)
            values['absolute_roughness']=row
        import json
        defaults=json.loads(context.engineering_defaults_json)
        for name,row in tuple(values.items()):
            if row['id'] in defaults:
                values[name]={**row,'library_default':row['default_value'],'default_value':defaults[row['id']],'default_method':'USER_DEFINED'}
        return values
    def seawater_basis(self,context,module):
        """Resolve exact source-backed scope; unsupported legacy values stay manual."""
        from engineering.provenance import VerificationStatus
        refs=self.references(context)
        fluid_ready=all(refs.get(name,{}).get('default_value') is not None and
                        refs[name].get('verification')=='VERIFIED' for name in ('density','kinematic_viscosity'))
        properties=[]
        if context.material_id is not None and context.rule_set_id is not None:
            for row in self.material_property_records:
                source=self.source_records.get(row.source_id)
                if row.property_name in ('Rm','ReH','Rp0.2','allowable_stress') and row.unit in ('MPa','N/mm²','N/mm2') and row.material_id==context.material_id and row.rule_set_id==context.rule_set_id and (
                    row.verification_status is VerificationStatus.VERIFIED and source is not None
                    and source.verification_status is VerificationStatus.VERIFIED
                    and source.document and source.source_organization
                    and (row.reference_temperature_c is None or row.reference_temperature_c==context.fluid_temperature_c)):
                    properties.append({'record':record_payload(row),'source':record_payload(source)})
        corrosion=[]
        for rule in self.matching_rules(context,'seawater',module):
            if rule.parameter=='corrosion_allowance' and rule.verification=='VERIFIED' and rule.material and rule.service and (
                rule.source_authority and rule.source_document and rule.source_clause):
                lo,hi=(rule.hard_min,rule.hard_max) if rule.rule_nature=='HARD_LIMIT' else (rule.recommended_min,rule.recommended_max)
                if lo is not None and lo==hi:corrosion.append(record_payload(rule))
        return {'fluid_ready':fluid_ready,'material_properties':properties,'corrosion_criteria':corrosion,
                'temperature_c':context.fluid_temperature_c,'salinity_g_kg':context.fluid_salinity_g_kg,
                'hw_applicability':'SOURCE_REQUIRED'}
    def matching_rules(self,context,family,module):
        group=next((r.fluid_group for r in self.property_records if r.fluid_id==context.fluid_id),'')
        material=next((r.material_name for r in self.surface_records if r.id==context.surface_profile_id),'')
        grade=next((r.designation for r in self.material_records if r.id==context.material_id),'')
        if grade and family=='seawater':material=grade
        line={'discharge_head_loss':'DELIVERY','suction_npsh':'SUCTION'}.get(module,context.line_type)
        active_profiles={row.id for row in self.profile_records}
        records=tuple(row for row in self.rule_records if row.profile_id in active_profiles or row.code=='D243_FUEL_MAX')
        return applicable_rules(records,family=family,profile_id=context.rule_set_id,
            fluid_group=group,line_type=line,material=material,scope=context.applicability_scope,service=context.service)
