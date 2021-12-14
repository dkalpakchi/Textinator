;(function($) {
  // fix for nested_admin deletion
  // for some reasons djn-delete-handler from django_nested_admin disables clicking on delete checkboxes
  // so we fix it by simply autoclicking all nested delete checkboxes if the parent was clicked
  $('[id$="-DELETE"]').on('click', function() {
    var $form = $(this).closest('div[id*="_set-"]');

    if ($form.length) {
      var $groups = $form.find('div[id*="_set-group"]');

      if ($groups.length) {
        $groups.find('[id$="-DELETE"]').prop("checked", true);
      }
    }
  })
})(jQuery);