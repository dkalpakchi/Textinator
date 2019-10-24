$(document).ready(function() {
  var templates = {
    'TextFile': {
      'files': []
    },
    'Db': {
      'db_type': '', 
      'user': '',
      'password': '',
      'database': '' 
    },
    'Json': {
      'files': [],
      'folders': [],
      'remote': [],
      'key': ''
    },
    'PlainText': {
      'texts': []
    }
  }

  var schemas = {
    "PlainText": {
      'type': 'object',
      "properties": {
        "texts": {
          "type": "array",
          "items": {
            "type": "string",
            "format": "textarea"
          }
        }
      }
    }
  }

  function updateSchema(option) {
    // NOTE: `spec` everywhere is just the name of the field in the model
    //       if the name changes djang-admin-json-editor, changes the name of JS variable as well
    if (schemas.hasOwnProperty(option)) {
      var schema = schemas[option],
          element = spec_editor.element;
      spec_editor.destroy();
      schema['title'] = ' ';
      spec_editor = new JSONEditor(element, {
        'theme': 'bootstrap3',
        'iconlib': 'fontawesome4',
        'schema': schema
      })

      spec_editor.on('change', function () {
        var errors = spec_editor.validate();
        if (errors.length) {
            console.log(errors);
        }
        else {
            var json = spec_editor.getValue();
            document.getElementById("id_spec").value = JSON.stringify(json);
        }
      });
    }
    return spec_editor
  }


  $('#id_source_type').on('change', function(e) {
    var $target = $(e.target),
        option = $target.find("option:selected").val();

    spec_editor = updateSchema(option);    

    // defined in django-admin-json-editor
    spec_editor.setValue(templates[option]);

    $('input[name="root[db_type]"]').off('change');
    $('input[name="root[db_type]"]').on('change', function(e) {
      if (e.target.value == 'mongodb') {
        var options = { ...templates[option] };
        options['db_type'] = e.target.value;
        options['collection'] = '';
        options['field'] = '';
        spec_editor.setValue(options)
      } else if (['mysql', 'postgresql', 'postgres'].includes(e.target.value)) {
        var options = { ...templates[option] };
        options['db_type'] = e.target.value;
        options['rand_dp_query'] = '';
        options['size_query'] = '';
        spec_editor.setValue(options)
      }
    })
  })
});