$(document).ready(function() {
  $(".survey-description").accordion({
    collapsible: true,
    active: false
  });

  $('form').validate({
    errorClass: "error tag is-danger",
    invalidHandler: function(event, validator) {
      event.preventDefault();
    },
    errorPlacement: function(label, element) {
      if (element.parent().prop('tagName') == 'LABEL') {
        element.parent().parent().append(label);
      } else {
        element.parent().append(label);
      }
    },
    highlight: function(element, errorClass, validClass) {
      $(element).addClass(errorClass).removeClass(validClass).removeClass('tag is-danger');
    },
    unhighlight: function(element, errorClass, validClass) {
      $(element).removeClass(errorClass).addClass(validClass);
    }
  });

  $('input[type!="hidden"]').each(function() {
    $(this).rules('add', {
      required: true
    });
  });
});