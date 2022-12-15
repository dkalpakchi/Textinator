(function ($, bulmaSlider) {
  $(document).ready(function () {
    $(".survey-description").accordion({
      collapsible: true,
      active: parseInt($("progress").val(), 10) === 0 ? 0 : false,
    });

    $("form").validate({
      errorClass: "error tag is-danger",
      invalidHandler: function (event, validator) {
        event.preventDefault();
        if (validator !== undefined && validator !== null) validator();
      },
      errorPlacement: function (label, element) {
        if (element.parent().prop("tagName") == "LABEL") {
          element.parent().parent().append(label);
        } else {
          element.parent().append(label);
        }
      },
      highlight: function (element, errorClass, validClass) {
        $(element)
          .addClass(errorClass)
          .removeClass(validClass)
          .removeClass("tag is-danger");
      },
      unhighlight: function (element, errorClass, validClass) {
        $(element).removeClass(errorClass).addClass(validClass);
      },
    });

    $('input[type!="hidden"]').each(function () {
      let isRequired =
        $(this).siblings(".criterion").attr("data-required") == "true" ||
        $(this).parent().siblings(".criterion").attr("data-required") == "true";

      if (isRequired) {
        $(this).rules("add", {
          required: true,
        });
      }
    });

    bulmaSlider.attach();
  });
})(window.jQuery, window.bulmaSlider);
