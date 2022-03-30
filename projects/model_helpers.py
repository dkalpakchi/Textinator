class DatapointInfo:
    def __init__(self, dp_id=None, text=None, ds=None, ds_def=None, is_empty=False, no_data=False, is_dialogue=False):
        self.id = dp_id
        self.text = text
        if ds:
            self.source_size = ds.size()
            self.source_name = ds.get_source_name(self.id)
        else:
            self.source_size, self.source_name = 0, ''
        
        if ds_def:
            self.source_id = ds_def.pk
            self.source_formatting = ds_def.formatting
        else:
            self.source_id, self.source_formatting = None, None

        self.is_empty = is_empty
        self.no_data = no_data
        self.is_dialogue = is_dialogue

    def to_json(self):
        return {
            'id': self.id,
            'text': self.text,
            'source_size': self.source_size,
            'source_name': self.source_name,
            'source_id': self.source_id,
            'source_formatting': self.source_formatting,
            'is_empty': self.is_empty
        }