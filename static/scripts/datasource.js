$(document).ready(function() {
  var templates = {
    'TextFile': {
      'files': []
    },
    'Db': {
      'db_type': '', 
      'user': '',
      'database': '', 
      'password': '', 
      'rand_dp_query': ''
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
  })
});