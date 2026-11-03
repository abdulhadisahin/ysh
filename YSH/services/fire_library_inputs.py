"""Detached live recommendation links; never resolve Library while reading history."""
from engineering.fire.library import FireEngineeringDataRecord, FIELD_PARAMETERS


class FireLibraryInputs:
    def __init__(self):
        self.contexts={'foam':'','hw':''}
        self.links={}
        self.stale={}
        self.kept={}

    def to_payload(self):
        return {'version':1,'contexts':dict(self.contexts),
                'links':{key:record.to_payload() for key,record in self.links.items()},'kept':dict(self.kept)}

    @classmethod
    def from_payload(cls,payload):
        result=cls()
        if not payload:return result
        if payload.get('version')!=1 or set(payload['contexts'])!={'foam','hw'} or not all(isinstance(v,str) for v in payload['contexts'].values()):
            raise ValueError('Invalid Fire Library project preferences')
        result.contexts=dict(payload['contexts'])
        result.kept=dict(payload.get('kept',{}))
        if not all(key in FIELD_PARAMETERS and type(value) is bool for key,value in result.kept.items()):
            raise ValueError('Invalid kept-current preference')
        for key,value in payload['links'].items():
            record=FireEngineeringDataRecord.from_payload(value)
            if key not in FIELD_PARAMETERS or record.parameter_type!=FIELD_PARAMETERS[key]:
                raise ValueError('Mismatched Fire Library parameter')
            result.links[key]=record
        return result
