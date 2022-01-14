class DatapointInfo:
    def __init__(self, dp_id=None, text=None, ds=None, ds_def=None):
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