$(document).ready(function() {
  // Guidelines "Show more" button
  var scrollTimer = setTimeout(function() {
    $('.button-scrolling').each(function(i, x) {
      if (x.scrollHeight > x.clientHeight) {
        clearTimeout(scrollTimer);
        var $button = $("<button class='scrolling is-link button'>Show more</button>"),
            $el = $(x),
            top = $el.scrollTop();

        $el.scroll(function(e) {
          var pos = $button.css('top') ? parseInt($button.css('top')) : $button.position().top;
          $button.css('top', pos + $el.scrollTop() - top);
          top = $el.scrollTop();
          if ($el.scrollTop() + $el.innerHeight() >= $el[0].scrollHeight) {
            $button.hide();
          }
        });

        $button.on('click', function(e) {
          e.preventDefault();
          $button.prop('disabled', true);
          $el.animate({ scrollTop: $el.scrollTop() + 200 }, {
            duration: 500,
            complete: function() {
              $button.prop('disabled', false);
            }
          });
          if ($el.scrollTop() + $el.innerHeight() >= $el[0].scrollHeight) {
            $button.hide();
          }
        });


        $el.append($button);
      }
    });
  }, 100);
  


  /**
   * Modals handling
   */

  $('#flagTextButton').on('click', function() {
    $('.flag.modal').addClass('is-active');
  })

  $('#flagTextForm').on('submit', function(e) {
    e.preventDefault();
    var $form = $("#flagTextForm");

    $.ajax({
      type: $form.attr('method'),
      url: $form.attr('action'),
      dataType: "json",
      data: {
        "csrfmiddlewaretoken": $('input[name="csrfmiddlewaretoken"]').val(),
        "feedback": $form.find('textarea[name="feedback"]').val(),
        "ds_id": labelerModule.selectorArea.getAttribute('data-s'),
        "dp_id": labelerModule.selectorArea.getAttribute('data-dp')
      },
      success: function(d) {
        alert("Thank you for your feedback!");
        $('.flag.modal').removeClass('is-active');
        getNewText(function() { return true; }, $('#getNewArticle'));
      },
      error: function() {
        alert("Your feedback was not recorded. Please try again later.");
      }
    })
  })

  $('#guidelinesButton').on('click', function() {
    $('.guidelines.modal').addClass('is-active');
  });

  $('.modal-close').on('click', function() {
    $('.modal').removeClass('is-active');
    // $('.countdown svg circle:last-child').trigger('cdAnimate');
  });

  $('.modal-background').on('click', function() {
    $('.modal').removeClass('is-active');
    // $('.countdown svg circle:last-child').trigger('cdAnimate');
  });

  $('#guidelinesButton').click();

  /**
   * - Modals handling
   */
});