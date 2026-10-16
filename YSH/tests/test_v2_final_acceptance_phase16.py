"""Final cross-module acceptance across real project close/reopen boundaries."""
from dataclasses import replace
from pathlib import Path

import pytest

from database.library_database import LibraryDatabase
from database.project_database import ProjectDatabase
from engineering.module_registry import ModuleCode, module_availability
from engineering.pipe_design.transfer import revise_selection, PipeLinkStatus
from engineering.pipe_design.v2_calculator import PipeDesignV2Calculator
from engineering.pipe_design.v2_models import PipeProvenance
from engineering.provenance import EngineeringValue, SourceReference, SourceType, OverridePolicy
from engineering.snapshots.builders import build_snapshot, build_pipe_v2_snapshot
from engineering.transfer_pump.v2_models import TransferPumpDesignInput, TransferPumpEmpiricalInput
from i18n.translator import Translator
from paths import ApplicationPaths
from repositories.calculation_repository import CalculationRepository
from repositories.project_repository import ProjectRepository
from repositories.project_state_repository import ProjectStateRepository
from services.discharge_head_loss_service import DischargeHeadLossService
from services.discharge_workflow import DischargeWorkflow
from services.pipe_source_discovery import PipeSourceDiscovery
from services.project_persistence_service import ProjectPersistenceService
from services.project_service import ProjectService
from services.snapshot_history_service import SnapshotHistoryService
from services.suction_npsh_service import SuctionNPSHService
from services.suction_workflow import SuctionWorkflow
from ui.widgets.formula_steps import step_sections
from .test_discharge_v2_phase8 import inputs
from .test_pipe_design_v2 import request, candidate
from .test_suction_v2_phase9 import suction_input, enpy_input
from .test_system_context_phase12 import context
from .test_transfer_pump_v2_phase10 import service as transfer_service


def persistence(database: ProjectDatabase) -> ProjectPersistenceService:
    """Compose actual repositories without accessing a user's runtime profile."""
    return ProjectPersistenceService(ProjectService(ProjectRepository(database)), ProjectStateRepository(database))


@pytest.mark.parametrize('bend', [False, True])
def test_all_modules_history_and_stale_links_survive_project_reopen(tmp_path, monkeypatch, bend) -> None:
    """One project retains five module/mode histories independently of today's state."""
    database = ProjectDatabase(tmp_path / 'projects.db')
    database.initialize()
    projects = persistence(database)
    project = projects.create_project('Final acceptance — synthetic data')
    history = SnapshotHistoryService(CalculationRepository(database))
    source = SourceReference(source_type=SourceType.ENGINEERING_REFERENCE,
                             document='ACCEPTANCE FIXTURE ONLY', revision='A')
    velocity = EngineeringValue(used_value=2, recommended_value=1.5, unit='m/s', symbol='V',
        source=source, override_policy=OverridePolicy.SUGGESTED, override_reason='Synthetic project choice')
    used = request(bend_allowance_enabled=bend, bend_radius_mm=300 if bend else None,
                   provenance=PipeProvenance(design_velocity=velocity))
    geometry = candidate(od=110, wall=4, inside=101, dimension_source=source)
    pipe = PipeDesignV2Calculator().calculate(used, [geometry])
    discovery = PipeSourceDiscovery()
    discharge = DischargeWorkflow(discovery=discovery)
    suction = SuctionWorkflow(discovery=discovery)
    discovery.publish(pipe)
    discharge.link(pipe.selection_id)
    suction.link(pipe.selection_id)
    loss = DischargeHeadLossService(object()).calculate_v2(inputs(discharge.pipe_input))
    enpy = SuctionNPSHService(object()).calculate_v2(suction_input(suction.pipe_input), enpy_input())
    transfer = transfer_service()
    design = transfer.calculate_v2(TransferPumpDesignInput(
        transfer_volume_m3=120, target_transfer_time_h=3, selected_pump_capacity_m3_h=40))
    empirical = transfer.calculate_v2(TransferPumpEmpiricalInput(source_capacity=250))
    snapshots = [build_pipe_v2_snapshot(pipe, used, context=context(), project_id=project.id)]
    snapshots.extend(build_snapshot(module, stage, result, context=context(), project_id=project.id)
        for module, stage, result in ((ModuleCode.DISCHARGE, 'hydraulics', loss),
            (ModuleCode.SUCTION_NPSH, 'enpy', enpy), (ModuleCode.TRANSFER_PUMP, 'design', design),
            (ModuleCode.TRANSFER_PUMP, 'empirical', empirical)))
    for snapshot in snapshots:
        history.append(snapshot)
    expected = {s.snapshot_id: s.to_json() for s in snapshots}
    # An actual new upstream calculation changes Q/Di and source metadata.
    changed_geometry = replace(geometry, inside_diameter_mm=99,
                               dimension_source=replace(source, document='Changed live source', revision='B'))
    new_pipe = PipeDesignV2Calculator().calculate(replace(used, flow_rate_m3_h=30), [changed_geometry])
    discovery.publish(revise_selection(pipe, new_pipe))
    assert discharge.pipe_input.status is suction.pipe_input.status is PipeLinkStatus.LINKED_STALE
    assert discharge.pipe_input.used_values.actual_internal_diameter_mm == 101
    assert suction.pipe_input.used_values.flow_rate_m3_h == 20
    assert loss.actual_internal_diameter_mm == enpy.actual_internal_diameter_mm == 101
    changed_context = context('FRESH_WATER')
    projects.save_with_pipe_transfer({'system_context': changed_context.to_payload(),
        'pipe_design': {'bend_enabled': bend, 'bend_mode': 'MANUAL' if bend else 'NO_BEND',
                        'fields': {'r': '300' if bend else ''}},
        'transfer_pump': {'mode': 'DESIGN'}, 'discharge_head_loss': {'fields': {'l': '20'}},
        'suction_npsh': {'fields': {'pressure': '1.2'}}}, discovery.state)
    projects.close()
    reopened_database = ProjectDatabase(database.database_path)
    reopened_database.initialize()
    reopened = persistence(reopened_database)
    _, workspace, links = reopened.open_with_pipe_transfer(project.id)
    assert workspace['system_context'] == changed_context.to_payload()
    assert workspace['pipe_design']['bend_enabled'] is bend
    assert workspace['transfer_pump']['mode'] == 'DESIGN'
    assert links.discharge.snapshot.source_revision == links.suction.snapshot.source_revision == 1
    assert links.selections[0].revision == 2 and links.discharge.status is PipeLinkStatus.LINKED_STALE
    assert links.discharge.used_values.actual_internal_diameter_mm == 101
    assert not next(a.enabled for a in module_availability(changed_context)
                    if a.definition.code is ModuleCode.TRANSFER_PUMP)
    def forbidden(*args, **kwargs):
        pytest.fail('Historical rendering invoked live calculation')
    for target in (PipeDesignV2Calculator, DischargeHeadLossService, SuctionNPSHService, type(transfer)):
        monkeypatch.setattr(target, 'calculate' if target is PipeDesignV2Calculator else 'calculate_v2', forbidden)
    reopened_history = SnapshotHistoryService(CalculationRepository(reopened_database))
    stored = reopened_history.list(project.id)
    assert {s.snapshot_id: s.to_json() for s in stored} == expected
    assert len(stored) == 5 and all(s.context == context() for s in stored)
    frozen_pipe = next(s for s in stored if s.module_code is ModuleCode.PIPE_DESIGN)
    assert frozen_pipe.evidence['facts']['input']['bend_allowance_enabled'] is bend
    assert next(s.result_value for s in frozen_pipe.formula_steps if s.step_id == 'pipe.b') == pipe.wall.bend_allowance_mm
    for language in ('tr', 'en'):
        for snapshot in stored:
            assert all(step_sections(step, Translator(language).translate) for step in snapshot.formula_steps)
    assert {s.snapshot_id: s.to_json() for s in reopened_history.list(project.id)} == expected
    other = reopened.create_project('Separate project')
    assert reopened_history.list(other.id) == ()


def test_temporary_runtime_paths_schema_idempotence_and_data_preservation(tmp_path: Path) -> None:
    """Reinitialize both runtime databases without schema changes or user-profile access."""
    paths = ApplicationPaths(local_app_data=tmp_path / 'isolated-localappdata')
    assert paths.data_directory == tmp_path / 'isolated-localappdata' / 'YSH' / 'data'
    projects = ProjectDatabase(paths.projects_database_path)
    library = LibraryDatabase(paths.libraries_database_path)
    projects.initialize()
    library.initialize()
    project = persistence(projects).create_project('Preserve this project')
    with library.connection() as connection:
        schema = tuple(tuple(row) for row in connection.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"))
        counts = {row[0]: connection.execute(f'SELECT count(*) FROM "{row[0]}"').fetchone()[0]
                  for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    for database, version in ((ProjectDatabase(paths.projects_database_path), 1),
                              (LibraryDatabase(paths.libraries_database_path), 5)):
        database.initialize()
        database.initialize()
        with database.connection() as connection:
            assert connection.execute('PRAGMA foreign_keys').fetchone()[0] == 1
            assert connection.execute('SELECT version FROM schema_version').fetchone()[0] == version
            assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not connection.execute('PRAGMA foreign_key_check').fetchall()
    assert persistence(projects).get_project(project.id).name == project.name
    with library.connection() as connection:
        assert tuple(tuple(row) for row in connection.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")) == schema
        assert {table: connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                for table in counts} == counts
