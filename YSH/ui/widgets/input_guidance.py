"""Short localized hints and next-action messages; never inspect engineering data."""
from ui.widgets.tooltip import Tooltip


def localize_guidance(page, module, translate):
    """Refresh existing hints in place, preserving bindings and form values."""
    pairs=[]
    if module=='pipe':
        pairs=[(page._field_labels['v'][0],'guidance.velocity'),
               (page._field_labels['r'][0],'guidance.bend_radius')]
        empty=page._pipe_result_empty_state
    elif module=='transfer_design':
        pairs=[(page._labels['target_time'],'guidance.transfer_time'),
               (page._labels['pump_capacity'],'guidance.optional_capacity')]
        empty=None
    elif module=='transfer_empirical':
        pairs=[(page._capacity_label,'guidance.capacity_unit')]
        empty=page._result_empty_state
    elif module=='discharge':
        pairs=[(page._field_label_h,'guidance.discharge_height'),
               (page._active_roughness_label,'guidance.roughness')]
        empty=page._result_empty_state
    elif module=='suction':
        pairs=[(page._field_label_height[0],'guidance.suction_height'),
               (page._field_label_required[0],'guidance.optional_npshr')]
        empty=page._result_empty_state
    else:
        pairs=([(page.labels['application_density_lpm_m2'],'guidance.foam_density')]
               if module=='foam' else
               [(page.labels['hazen_williams_c'],'guidance.hw_c'),
                (page.labels['inside_diameter_mm'],'guidance.inside_diameter')])
        empty=None
    page._guidance_widgets=pairs
    for widget,key in pairs:
        if not hasattr(widget,'_guidance_tooltip'):
            widget._guidance_tooltip=Tooltip(widget,translate(key),wraplength=280)
            widget.configure(cursor='question_arrow')
        else:widget._guidance_tooltip.set_text(translate(key))
    if empty is not None:
        empty.set_content(translate('guidance.empty.title'),translate('guidance.empty.'+module))
        if not getattr(empty,'_guidance_wrap_bound',False):
            def fit(event):
                width=max(120,event.width-24)
                empty._title.configure(wraplength=width)
                empty._body.configure(wraplength=width)
            empty.bind('<Configure>',fit,add='+')
            empty._guidance_wrap_bound=True
