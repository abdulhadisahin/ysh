"""Authoritative human-facing report tokens; frozen codes stay unchanged internally."""
import re
from i18n.translator import Translator
from i18n.messages_tr import MESSAGES as TR

LABELS={'Vfuel':'field.fuel_capacity','Qpump':'field.pump_capacity','Vtransfer':'transfer.design.volume',
 'tdef':'transfer.design.target_time','Qgerekli':'word.transfer.average','Qtulumba':'transfer.design.pump_capacity',
 'ttransfer':'word.transfer.time'}
PREFIXES=('engineering.status.','engineering.verification.','engineering.method.','engineering.nature.',
 'formula2.source_type.','formula2.verification_status.','formula2.reason.','formula2.classification.',
 'discharge.pipe.status.','pipe.status.','transfer.design.status.','fire.ui.source.')
STATUS_KEYS={}
for prefix in PREFIXES:
    for key in TR:
        code=key.removeprefix(prefix)
        if key.startswith(prefix) and re.fullmatch(r'[A-Z][A-Z0-9_]*',code):STATUS_KEYS.setdefault(code,key)
STATUS_KEYS.update({'MANUAL':'source.state.manual','LINKED':'source.state.linked','OVERRIDE':'word.manual_override',
 'STALE':'source.state.stale','USER_INPUT':'formula2.source_type.USER_INPUT','USER_SUPPLIED':'source.state.manual','DESIGN':'word.transfer.design',
 'EMPIRICAL':'word.transfer.empirical','VOLUME':'word.volume_mode','MASS':'word.mass_mode',
 'RULE_NOT_CONFIGURED':'formula2.check.NOT_CONFIGURED','BLOCKED_APPLICABILITY':'center.status.BLOCKED',
 'WARNING':'word.status.warning','ERROR':'word.status.error','BLOCKED':'word.status.blocked',
 'CRITICAL':'word.status.critical','OUT_OF_RANGE':'word.status.out_of_range','SOURCE_REQUIRED':'word.source_required',
 'VERIFIED':'formula2.verification_status.VERIFIED','UNVERIFIED':'formula2.verification_status.UNVERIFIED',
 'PARTIALLY_VERIFIED':'formula2.verification_status.PARTIALLY_VERIFIED',
 'PROJECT':'engineering.status.LINKED','PROJECT_LINKED':'engineering.status.LINKED',
 'LINKED_STALE':'discharge.pipe.status.LINKED_STALE','RECOMMENDED_RANGE':'engineering.nature.RECOMMENDED_RANGE',
 'HARD_LIMIT':'engineering.nature.HARD_LIMIT','D243_CRITERION':'engineering.nature.D243_CRITERION',
 'DERIVED_MIDPOINT':'engineering.method.DERIVED_MIDPOINT','SOURCE_NOMINAL':'engineering.method.SOURCE_NOMINAL',
 'LIMITED_APPLICABILITY':'engineering.verification.LIMITED_APPLICABILITY','RECOMMENDATION':'engineering.verification.RECOMMENDATION'})

class ReportLanguage:
    def __init__(self,language):
        self.language=language;self.tr=Translator(language).translate
    def status(self,code):
        key=STATUS_KEYS.get(str(code),'word.unknown_status')
        return self.tr(key)
    def text(self,value):
        text=str(value)
        for code in sorted(STATUS_KEYS,key=len,reverse=True):
            text=re.sub(r'(?<![\w])'+re.escape(code)+r'(?![\w])',lambda match,code=code:self.status(code),text)
        for symbol,key in LABELS.items():
            label=self.tr(key)
            label=re.sub(r'\s*\('+re.escape(symbol)+r'\)','',label)
            text=re.sub(r'(?<!\w)'+re.escape(symbol)+r'(?!\w)',lambda match,label=label:label,text)
        text=text.replace('Calculation-only manual override',self.tr('word.manual_override'))
        # SourceReference rows previously printed code + translated text. Keep one human label.
        for separator in (' · ',' - '):
            parts=text.split(separator);seen=set();result=[]
            for part in parts:
                if part.casefold() not in seen:result.append(part);seen.add(part.casefold())
            text=separator.join(result)
        return text
    def label(self,label,symbol='',unit=''):
        label=re.sub(r'\s*\('+'|'.join(re.escape(x) for x in (symbol,unit) if x)+r'\)\s*','',label) if symbol or unit else label
        return self.text(label)
    def number(self,value):
        if isinstance(value,bool):return self.tr('library2.yes' if value else 'library2.no')
        if isinstance(value,(int,float)):
            if 0<abs(value)<.01:text=f'{value:.4g}'
            else:
                digits=len(str(int(abs(value)))) if abs(value)>=1 else 0
                places=max(2,4-digits);text=f'{value:.{places}f}'
                while places>2 and text.endswith('0'):text=text[:-1];places-=1
            return text.replace('.',',') if self.language=='tr' else text
        return self.text(value)
    def plain(self,value):
        """User-entered or catalog names: never rewritten as status codes."""
        return str(value)
    def severity(self,code):
        colors={'WARNING':'yellow','OUT_OF_RANGE':'red','ERROR':'red','BLOCKED':'red','CRITICAL':'black'}
        prefix=self.tr('word.color.'+colors[code])+' — ' if code in colors else ''
        return prefix+self.status(code)


def basis_explanations(payload,language):
    ui=ReportLanguage(language);tr=ui.tr;paragraphs=[]
    for key,value in payload.get('fluid_conditions',{}).items():
        if value is not None:paragraphs.append(tr('hydro.condition.'+key)+': '+(str(value).replace('.',',') if language=='tr' else str(value)))
    for item in payload.get('values',()):
        ref=item['reference'];name=ui.text(ref.get('name') or payload.get('fluid') or '')
        if item.get('pending'):paragraphs.append(tr('engineering.pending')+': '+ui.status('SOURCE_REQUIRED' if item['pending'].get('default_value') is None else 'LINKED'))
        if ref.get('record_kind')=='OPERATING_POINT':
            for field,key in (('reference_temperature_c','temperature_c'),('reference_salinity_g_kg','salinity_g_kg'),('reference_pressure_mpa','pressure_mpa')):
                if ref.get(field) is not None:
                    value=str(ref[field]).replace('.',',') if language=='tr' else str(ref[field])
                    paragraphs.append(tr('engineering.reference')+' / '+tr('hydro.condition.'+key)+': '+value)
        property_name=tr('engineering.property.'+ref['property_name']);unit=ref.get('unit','')
        low,high=ref.get('source_min'),ref.get('source_max');temperature=ref.get('reference_temperature_c')
        default,used=ref.get('default_value'),item.get('used_value')
        if low is not None and high is not None:
            paragraphs.append(tr('word.explain.range',name=name,property=property_name.lower(),low=ui.number(low),high=ui.number(high),unit=unit,
                temperature=tr('word.explain.temperature',value=ui.number(temperature)) if temperature is not None else ''))
        if ref.get('default_method')=='DERIVED_MIDPOINT' and low is not None and high is not None and default is not None:
            paragraphs.append(tr('word.explain.midpoint',default=ui.number(default),unit=unit) if ref.get('source_nominal') is None else tr('word.explain.default',default=ui.number(default),unit=unit))
        elif default is not None:paragraphs.append(tr('word.explain.default',default=ui.number(default),unit=unit))
        if used is not None and item.get('use_role')=='REFERENCE_ONLY':
            paragraphs.append(tr('hydro.reference_only')+': '+ui.number(used)+' '+unit)
        elif used is not None:
            paragraphs.append(tr('word.explain.override' if item.get('status')=='OVERRIDE' else 'word.explain.used',used=ui.number(used),unit=unit))
        from engineering.source_verification import evidence_rows
        paragraphs.extend(label+': '+value for label,value in evidence_rows(ref.get('source_evidence'),tr))
    for rule in payload.get('rules',()):
        from engineering.source_verification import evidence_rows
        paragraphs.extend(label+': '+value for label,value in evidence_rows(rule.get('source_evidence'),tr))
    return tuple(paragraphs)
