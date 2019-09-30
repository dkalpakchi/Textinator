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
      'key': ''
    }
  }


  $('#id_source_type').on('change', function(e) {
    var $target = $(e.target),
        option = $target.find("option:selected").val();

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
        console.log(options);
        spec_editor.setValue(options)
      }
    })
  })
});