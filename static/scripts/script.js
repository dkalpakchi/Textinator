$(document).ready(function() {
  $('div[data-link]').on('click', function(e) {
    e.preventDefault();
    document.location.href = $(this).attr('data-link');
  });

  // Check for click events on the navbar burger icon
  $(".navbar-burger").click(function() {
    // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
    $(".navbar-burger").toggleClass("is-active");
    $(".navbar-menu").toggleClass("is-active");
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
            $('div[data-link]').off('click')
            $('div[data-link]').on('click', function(e) {
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

  // var countdown = null,
  //     interval = null;

  // function resetTimer() {
  //   countdown = 60;
  //   var circle = $('.countdown svg circle:last-child');
  //   circle.removeClass('countdown-animate')
  //   circle.outerWidth();
  //   circle.addClass('countdown-animate');
  // }

  // $('.countdown').on('cdAnimate', function() {
  //   var countdownNumberEl = document.querySelector('.countdown-number');

  //   resetTimer();

  //   countdownNumberEl.textContent = countdown;

  //   if (interval == null) {
  //     interval = setInterval(function() {
  //       if (countdown == null) {
  //         clearInterval(interval);
  //         interval = null;
  //       }
  //       countdown = --countdown;

  //       if (countdown >= 0)
  //         countdownNumberEl.textContent = countdown;
  //     }, 1000);
  //   }
  // });

  // $('.countdown').on('cdAnimateReset', function() {
  //   if (interval != null) {
  //     resetTimer();
  //   }
  // });

  $('nav .dropdown').on('click', function() {
    $(this).toggleClass('is-active');
  })

  /**
   * Adapted from:
   * https://css-tricks.com/value-bubbles-for-range-inputs/
   */

  document.addEventListener("input", function(e) {
    var target = e.target;
    if (target.nodeName == "INPUT" && target.getAttribute("type") == 'range') {
      var bubble = target.parentNode.querySelector('.bubble');
      setBubble(target, bubble);
    }
  });

  document.querySelectorAll('input[type="range"]').forEach(function(x) {
    var bubble = x.parentNode.querySelector('.bubble');
    setBubble(x, bubble);
    setBubbleDisplay(x, "none");
  })

  document.addEventListener('mousedown', function(e) {
    var target = e.target;
    if (target.nodeName == "INPUT" && target.getAttribute("type") == 'range') {
      setBubbleDisplay(target, "block");
    }
  })

  document.addEventListener('mouseup', function(e) {
    var target = e.target;
    if (target.nodeName == "INPUT" && target.getAttribute("type") == 'range') {
      setBubbleDisplay(target, "none");
    }
  })

  function setBubbleDisplay(range, display) {
    var bubble = range.parentNode.querySelector('.bubble');
    bubble.style.display = display;
  }

  function setBubble(range, bubble) {
    const val = range.value;
    const min = range.min ? range.min : 0;
    const max = range.max ? range.max : 100;
    const newVal = Number(((val - min) * 100) / (max - min));
    bubble.innerHTML = val;

    // Sorta magic numbers based on size of the native UI thumb
    bubble.style.left = `calc(${newVal}% + (${8 - newVal * 0.15}px))`;
  }

  $( "#sortable" ).sortable();
  $( "#sortable" ).disableSelection();

  $('form').validate({
    errorClass: "help is-danger"
  });

  $('input[type!="hidden"]').each(function() {
    if ($(this).attr('data-required') == "true") {
      $(this).rules('add', {
        required: true
      });
    }
  });
});