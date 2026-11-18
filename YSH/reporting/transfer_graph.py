"""Frozen transfer graph data and plotting of an already fitted line; never refit."""
from dataclasses import dataclass
from io import BytesIO

@dataclass(frozen=True,slots=True)
class ReferencePoint:
    name:str
    fuel_capacity_m3:float
    pump_capacity_m3_h:float
    source:str=''
    verification:str='SOURCE_REQUIRED'

@dataclass(frozen=True,slots=True)
class TransferGraph:
    references:tuple[ReferencePoint,...]
    slope:float
    intercept:float
    r_squared:float|None
    project_volume_m3:float|None
    predicted_capacity_m3_h:float|None
    transfer_time_h:float|None=None
    required_average_m3_h:float|None=None


def frozen_transfer_graph(snapshot):
    if snapshot.module_code.value!='transfer_pump' or snapshot.stage!='empirical':return None
    record=snapshot.evidence['facts'].get('calculation',{})
    estimate=record.get('estimate') or {};model=estimate.get('regression_model') or {}
    if model.get('slope') is None or model.get('intercept') is None:return None
    references=[]
    for row in record.get('references',()):
        source=row.get('source') or {}
        status=source.get('verification_status')
        verification=status if status in ('VERIFIED','PARTIALLY_VERIFIED') else 'SOURCE_REQUIRED'
        references.append(ReferencePoint(row['ship_name'],row['fuel_capacity_m3'],row['pump_capacity_m3_h'],
            ' · '.join(source[n] for n in ('source_organization','document','revision','notes') if source.get(n)),verification))
    if not references:return None  # Legacy missing facts remain missing; never read current Library.
    resolution=record.get('resolution') or {}
    return TransferGraph(tuple(references),model['slope'],model['intercept'],model.get('r_squared'),
        resolution.get('volume_m3'),estimate.get('predicted_pump_capacity_m3h'),
        estimate.get('estimated_emptying_time_hours'),resolution.get('required_capacity_12h_m3h'))


def render_transfer_graph(graph,translate):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig=Figure(figsize=(6.8,3.7),dpi=180);FigureCanvasAgg(fig)
    axes=fig.add_subplot(111)
    xs=[p.fuel_capacity_m3 for p in graph.references];ys=[p.pump_capacity_m3_h for p in graph.references]
    axes.scatter(xs,ys,color='#163047',s=35,label=translate('word.graph.references'),zorder=3)
    bounds=xs+([graph.project_volume_m3] if graph.project_volume_m3 is not None else [])
    endpoints=(min(bounds),max(bounds))
    # Display evaluation of the frozen line, not a regression calculation.
    axes.plot(endpoints,[graph.slope*x+graph.intercept for x in endpoints],color='#119EAD',label=translate('word.graph.line'))
    if graph.project_volume_m3 is not None and graph.predicted_capacity_m3_h is not None:
        axes.scatter([graph.project_volume_m3],[graph.predicted_capacity_m3_h],marker='D',s=55,color='#B46C13',
            label=translate('word.graph.project'),zorder=4)
    axes.set_xlabel(translate('word.graph.x'));axes.set_ylabel(translate('word.graph.y'))
    axes.grid(alpha=.2);axes.legend(fontsize=8);fig.tight_layout(pad=1.2)
    output=BytesIO();fig.savefig(output,format='png',metadata={'Software':'D243'})
    return output.getvalue()
