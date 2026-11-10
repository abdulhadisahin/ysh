"""Transfer Pump design-only inputs and stored-result presentation."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import logging
import tkinter as tk
from ui.widgets.input_guidance import localize_guidance
from ui.widgets.numeric_input import numeric_entry, numeric_pair
from tkinter import ttk

from engineering.input_parsing import parse_engineering_float
from engineering.transfer_pump.v2_models import TransferPumpDesignInput
from engineering.transfer_pump.v2_state import TransferPumpPageState
from engineering.validation import ValidationError
from i18n.validation import render_validation_issue
from services.transfer_pump_service import TransferPumpService
from ui.formatting import format_user_number
from ui.widgets.cards import InputCard, ResultCard, ResultMetric
from ui.widgets.formula_view import FormulaSection
from ui.widgets.rounded_button import TRANSFER_PRIMARY_PALETTE, NEUTRAL_BUTTON_PALETTE

from ui.widgets.calculation_presentation import calculation_button as create_rounded_button, set_result_state


class TransferPumpDesignPanel(ttk.Frame):
    """Design inputs/results never share empirical input variables or result storage."""

    def __init__(self, parent: tk.Misc, service: TransferPumpService,
                 translate: Callable[[str], str], changed: Callable[[], None]) -> None:
        """Create direct m³/h sizing with an optional actual selected pump capacity."""
        super().__init__(parent)
        self._service, self._translate, self._changed = service, translate, changed
        self._state = TransferPumpPageState()
        self._suppress = False
        self._fields = {key: tk.StringVar() for key in ('volume','target_time','pump_capacity')}
        self._flow = tk.StringVar(value='—'); self._time = tk.StringVar(value='—')
        self._status = tk.StringVar(value=''); self._error = tk.StringVar(value='')
        self._inputs = InputCard(self, '')
        self._inputs.grid(row=0, column=0, sticky='new', padx=(0,8))
        self._labels = {}
        for row,key in enumerate(self._fields):
            label = ttk.Label(self._inputs)
            label.grid(row=row,column=0,sticky='w',pady=4)
            pair, entry = numeric_pair(self._inputs, textvariable=self._fields[key],
                unit={'volume':'m³', 'target_time':'h', 'pump_capacity':'m³/h'}[key])
            pair.grid(row=row, column=1, columnspan=2, sticky='w', padx=8, pady=4)
            self._labels[key] = label
        self._calculate = create_rounded_button(self._inputs, '', self.calculate,
            style='TransferRoundedPrimary.TButton', palette=TRANSFER_PRIMARY_PALETTE,
            primary=True, icon_name='calculate')
        self._calculate.grid(row=3,column=0,sticky='w',pady=8)
        self._clear = create_rounded_button(self._inputs, '', self.clear,
            style='RoundedNeutral.TButton', palette=NEUTRAL_BUTTON_PALETTE, icon_name='clear')
        self._clear.grid(row=3,column=1,sticky='w',pady=8)
        self._results = ResultCard(self, '')
        self._results.grid(row=1,column=0,sticky='ew',pady=(8,0))
        self._empty_result=ttk.Label(self._results,wraplength=540)
        self._empty_result.grid(row=0,column=0,sticky='w',pady=8)
        self._flow_metric = ResultMetric(self._results, '', self._flow, 'm³/h', normal_style_prefix='TransferResultMetric')
        self._flow_metric.grid(row=0,column=0,sticky='ew')
        self._time_metric = ResultMetric(self._results, '', self._time, 'h', normal_style_prefix='TransferSecondaryMetric')
        self._time_metric.grid(row=1,column=0,sticky='ew',pady=6)
        ttk.Label(self._results,textvariable=self._status,wraplength=720).grid(row=2,column=0,sticky='w')
        ttk.Label(self,textvariable=self._error,wraplength=720).grid(row=2,column=0,sticky='w',pady=6)
        self.columnconfigure(0,weight=1)
        for variable in self._fields.values():
            variable.trace_add('write', self._invalidate)
        self.refresh_texts()

    def form_state(self) -> TransferPumpPageState:
        """Return raw form inputs with their configured source/context facts."""
        return replace(self._state, volume_text=self._fields['volume'].get(),
            target_time_text=self._fields['target_time'].get(),
            pump_capacity_text=self._fields['pump_capacity'].get())

    def load(self, state: TransferPumpPageState) -> None:
        """Restore input state without calculating or marking the project dirty."""
        self._suppress = True
        try:
            self._state = state
            for key,value in (('volume',state.volume_text),('target_time',state.target_time_text),('pump_capacity',state.pump_capacity_text)):
                self._fields[key].set(value)
            self.__dict__.pop('_last_result', None)
            self._error.set('')
            self._render()
        finally:
            self._suppress = False

    def calculate(self) -> None:
        """Parse/validate and delegate to the pure design path; no regression/library reads."""
        try:
            from services.system_context_integration import pump_context
            def number(key: str, optional: bool = False) -> float | None:
                return parse_engineering_float(self._fields[key].get(), field_name=key,
                    field_key=f'transfer.design.{key}', allow_empty=optional)
            self._last_result = self._service.calculate_v2(TransferPumpDesignInput(
                transfer_volume_m3=number('volume'), target_transfer_time_h=number('target_time'),
                selected_pump_capacity_m3_h=number('pump_capacity', True),
                context=pump_context(self._state.context, getattr(self, "_project_context", None)), volume_source=self._state.volume_source,
                target_time_source=self._state.target_time_source))
            self._error.set('')
            self._render()
            self._changed()
            from services.snapshot_events import notify_success
            notify_success(self,"design",self._last_result)
        except ValidationError as error:
            proxy = type('TranslatorProxy', (), {'translate':self._translate})()
            self._error.set(render_validation_issue(error.issue, proxy))
        except Exception:
            logging.getLogger(__name__).exception('Transfer pump design failed')
            self._error.set(self._translate('validation.unexpected_error'))

    def clear(self) -> None:
        """Clear only the design form/result, preserving the other calculation mode."""
        self.load(TransferPumpPageState())
        self._changed()

    def refresh_texts(self) -> None:
        """Rerender stored results and labels without calculating."""
        localize_guidance(self, 'transfer_design', self._translate)
        self._inputs.configure(text=self._translate('transfer.design.inputs'))
        self._results.configure(text=self._translate('transfer.design.results'))
        self._empty_result.configure(text=self._translate('guidance.empty.transfer_design'))
        for key,label in self._labels.items():
            label.configure(text=self._translate(f'transfer.design.{key}.label'))
        self._calculate.configure(text=self._translate('calculation.calculate'))
        self._clear.configure(text=self._translate('common.clear'))
        self._flow_metric.set_label(self._translate('transfer.design.required_flow'))
        self._time_metric.set_label(self._translate('transfer.design.transfer_time'))
        self._render()

    def _render(self) -> None:
        result = getattr(self, '_last_result', None)
        set_result_state(self._results,result is not None)
        (self._empty_result.grid_remove if result else self._empty_result.grid)()
        for metric in (self._flow_metric,self._time_metric):(metric.grid if result else metric.grid_remove)()
        self._flow.set(format_user_number(result.required_flow_m3_h) if result else '—')
        self._time.set(format_user_number(result.transfer_time_h) if result and result.transfer_time_h is not None else '—')
        self._status.set(self._translate(f'transfer.design.status.{result.status.value}') if result else '')

    def _invalidate(self, *_args: object) -> None:
        if not self._suppress:
            self.__dict__.pop('_last_result', None)
            self._error.set('')
            self._render()
            self._changed()

    def formula_sections(self) -> list[FormulaSection]:
        """Project stored design values into the existing Formula View; never calculate."""
        result = getattr(self, '_last_result', None)
        text = self._translate('message.available_after_calculation')
        if result:
            text = (f'Vtransfer = {format_user_number(result.input.transfer_volume_m3)} m³\n'
                    f'tdef = {format_user_number(result.input.target_transfer_time_h)} h\n'
                    f'Qgerekli = {format_user_number(result.required_flow_m3_h)} m³/h')
            if result.transfer_time_h is not None:
                text += f'\nQtulumba = {format_user_number(result.input.selected_pump_capacity_m3_h)} m³/h\nttransfer = {format_user_number(result.transfer_time_h)} h'
        return [FormulaSection('FORMULA','Qgerekli = Vtransfer / tdef\nttransfer = Vtransfer / Qtulumba',self._translate('transfer.mode.DESIGN'),'formula'),
                FormulaSection('RESULT',text,self._translate('transfer.mode.DESIGN'),'result')]
