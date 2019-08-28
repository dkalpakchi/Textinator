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
        inputFormData = $inputForm.serializeObject();

    $.ajax({
      method: "POST",
      url: $inputForm.attr('action'),
      dataType: "json",
      data: inputFormData,
      success: function(data) {
        console.log("SUCCESS!")
        if (data['result'] == 'joined')
          $target.val('Leave');
        else
          $target.val('Join');
        $target.blur();

        $.ajax({
          method: 'GET',
          url: encodeURI('/textinator/projects/participations/update?n=' + inputFormData['n']),
          success: function(data) {
            console.log(data)
            var $tab = null;
            if (inputFormData['n'] == 'o') {
              $tab = $('div[data-content="participations"]');  
            } else if (inputFormData['n'] == 'p') {
              $tab = $('div[data-content="open-projects"]');
            }
            if ($tab)
              $tab.html(data['template']);
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


  const tour = new Shepherd.Tour({
    defaultStepOptions: {
      scrollTo: {
        behavior: 'smooth',
        block: 'center'
      },
      showCancelLink: true,
      tippyOptions: {
        maxWidth: 500
      }
    },
    theme: 'default',
    useModalOverlay: true
  });

  tour.addStep('challenges', {
    text: 'This step is attached to the bottom of the <code>.example-css-selector</code> element.',
    attachTo: { 
      element: '.challenges', 
      on: 'bottom'
    },
    buttons: [
      {
        text: 'Next',
        action: tour.next
      }
    ]
  });

  $('.intro-button').on('click', function() {
    tour.start();
  })

  var countdown = null,
      interval = null;

  $('.countdown').on('cdAnimate', function() {
    var countdownNumberEl = document.querySelector('.countdown-number');
    if (countdown == null) {
      countdown = 60;
      var circle = $('.countdown svg circle:last-child');
      circle.removeClass('countdown-animate')
      circle.outerWidth();
      circle.addClass('countdown-animate');
    }

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
        else
          countdown = null;
      }, 1000);
    }
  });
});