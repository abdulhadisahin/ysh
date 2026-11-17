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
        self.reload()
    def reload(self):
        self.fluid_records=self.fluid_repository.get_all(active_only=True)
        self.property_records=self.properties.get_all(active_only=True)
        self.surface_records=self.surfaces.get_all(active_only=True)
        self.rule_records=self.rules.get_all(active_only=True)
        profile_ids={rule.profile_id for rule in self.rule_records}
        self.profile_records=tuple(r for r in self.profile_repository.get_all() if r.is_active and r.id in profile_ids)
        self.material_records=tuple(self.material_repository.get_all())
    def references(self,context):
        active_fluids={row.id for row in self.fluid_records}
        values={row.property_name:record_payload(row) for row in self.property_records if row.fluid_id==context.fluid_id and row.fluid_id in active_fluids}
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
    def matching_rules(self,context,family,module):
        group=next((r.fluid_group for r in self.property_records if r.fluid_id==context.fluid_id),'')
        material=next((r.material_name for r in self.surface_records if r.id==context.surface_profile_id),'')
        line={'discharge_head_loss':'DELIVERY','suction_npsh':'SUCTION'}.get(module,context.line_type)
        active_profiles={row.id for row in self.profile_records}
        records=tuple(row for row in self.rule_records if row.profile_id in active_profiles or row.code=='D243_FUEL_MAX')
        return applicable_rules(records,family=family,profile_id=context.rule_set_id,
            fluid_group=group,line_type=line,material=material,scope=context.applicability_scope,service=context.service)
