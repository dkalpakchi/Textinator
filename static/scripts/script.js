$(document).ready(function() {
  $('[data-link]').on('click', function(e) {
    e.preventDefault();
    console.log("HERE");
    document.location.href = $(this).attr('data-link');
  });

  $('.tabs li[data-tab]').on('click', function() {
    var tab = $(this).data('tab');

    $('.tabs li').removeClass('is-active');
    $(this).addClass('is-active');

    $('#tab-content div').removeClass('is-active');
    $('div[data-content="' + tab + '"]').addClass('is-active');
  });

  var joinFormSubmit = function(e) {
    e.preventDefault();
    e.stopPropagation();

    var $target = $(e.target),
        $inputForm = $target.closest('.join.form'),
        inputFormData = $inputForm.serializeObject(),
        $newlyShared = $('#newShared');

    $.ajax({
      method: "POST",
      url: $inputForm.attr('action'),
      dataType: "json",
      data: inputFormData,
      success: function(data) {
        if (data['result'] == 'joined')
          $target.val('Leave');
        else
          $target.val('Join');
        $target.blur();

        $.ajax({
          method: 'GET',
          url: encodeURI('/textinator/projects/participations/update?n=' + inputFormData['n']),
          success: function(data2) {
            var $tab = null;
            if (inputFormData['n'] == 'o') {
              $tab = $('div[data-content="participations"]');  
            } else if (inputFormData['n'] == 'p') {
              $tab = $('div[data-content="open-projects"]');
            } else if (inputFormData['n'] == 's') {
              $tab = $('div[data-content="shared-projects"]');
            }
            if ($tab)
              $tab.html(data2['template']);

            if (inputFormData['n'] == 's') {
              console.log($newlyShared.text())
              if (data['result'] == 'joined') {
                var newlyShared = parseInt($newlyShared.text()) - 1;
                $newlyShared.text(newlyShared);
                if (newlyShared > 0) {
                  $newlyShared.removeClass('is-hidden');
                } else {
                  $newlyShared.addClass('is-hidden');
                }
              } else {
                var newlyShared = parseInt($newlyShared.text()) + 1;
                $newlyShared.text(newlyShared);
                if (newlyShared > 0) {
                  $newlyShared.removeClass('is-hidden');
                }
              }
            }
            $('.join.form .submit.button').off('click');
            $('.join.form .submit.button').on('click', joinFormSubmit);
            $('[data-link]').off('click')
            $('[data-link]').on('click', function(e) {
              e.preventDefault();
              document.location.href = $(this).attr('data-link');
            });
          },
          error: function() {
            console.log("ERROR [GET]!")
          }
        })
      },
      error: function() {
        console.log("ERROR!")
      }
    })
  }

  $('.join.form .submit.button').on('click', joinFormSubmit);
  
  $('.intro-button').on('click', function() {
    tour.start();
  })

  var countdown = null,
      interval = null;

  function resetTimer() {
    countdown = 60;
    var circle = $('.countdown svg circle:last-child');
    circle.removeClass('countdown-animate')
    circle.outerWidth();
    circle.addClass('countdown-animate');
  }

  $('.countdown').on('cdAnimate', function() {
    var countdownNumberEl = document.querySelector('.countdown-number');

    resetTimer();

    countdownNumberEl.textContent = countdown;

    if (interval == null) {
      interval = setInterval(function() {
        if (countdown == null) {
          clearInterval(interval);
          interval = null;
        }
        countdown = --countdown;

        if (countdown >= 0)
          countdownNumberEl.textContent = countdown;
      }, 1000);
    }
  });

  $('.countdown').on('cdAnimateReset', function() {
    if (interval != null) {
      resetTimer();
    }
  });

  $('nav .dropdown').on('click', function() {
    $(this).toggleClass('is-active');
  })
});