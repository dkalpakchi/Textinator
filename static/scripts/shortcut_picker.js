;(function($) {
  $(document).ready(function() {
    $('#id_shortcut').on('keydown', function(e) {
      e.preventDefault();
      var $target = $(e.target);
      if (e.shiftKey)
        $target.val("SHIFT" + (e.which === 16 ? "" : " + " + String.fromCharCode(e.which)));
      else if (e.ctrlKey && e.which)
        $target.val("CTRL" + (e.which === 17 ? "" : " + " + String.fromCharCode(e.which)));
      else 
        $target.val(String.fromCharCode(e.which));
    });
  });
})(django.jQuery);
