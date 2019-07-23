$(document).ready(function() {
  $('[data-link]').on('click', function(e) {
    e.preventDefault();
    console.log("HERE");
    document.location.href = $(this).attr('data-link');
  });

  $('.tabs li[data-tab]').on('click', function() {
    var tab = $(this).data('tab');
    console.log(tab);

    $('.tabs li').removeClass('is-active');
    $(this).addClass('is-active');

    $('#tab-content div').removeClass('is-active');
    $('div[data-content="' + tab + '"]').addClass('is-active');
  });

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
});