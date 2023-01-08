(function ($) {
  // fix for nested_admin deletion
  // for some reasons djn-delete-handler from django_nested_admin disables clicking on delete checkboxes
  // so we fix it by simply autoclicking all nested delete checkboxes if the parent was clicked
  $('[id$="-DELETE"]').on("click", function () {
    let $form = $(this).closest('div[id*="_set-"]');

    if ($form.length) {
      let $groups = $form.find('div[id*="_set-group"]');

      if ($groups.length) {
        $groups.find('[id$="-DELETE"]').each(function () {
          $(this).prop("checked", !$(this).prop("checked"));
        });
      }
    }
  });

  $(['[id$="-custom_color"']).each(function () {
    if ($(this).attr("placeholder")) {
      $(this).val($(this).attr("placeholder"));
    }
  });
})(window.$);
