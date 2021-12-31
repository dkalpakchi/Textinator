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

    var $target = $(e.target).closest('a'),
        $inputForm = $target.find('form'),
        inputFormData = $inputForm.serializeObject(),
        $newlyShared = $('#newShared');

    $.ajax({
      method: "POST",
      url: $inputForm.attr('action'),
      dataType: "json",
      data: inputFormData,
      success: function(data) {
        if (data['result'] == 'joined')
          $target.find('span').text('Leave');
        else
          $target.find('span').text('Join');
        $target.blur();
      },
      error: function() {
        console.log("ERROR!")
      }
    })
  }

  $('a#joinButton').on('click', joinFormSubmit);
  
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

  $('.masonry-grid').masonry({
    // options...
    itemSelector: '.masonry-grid-item',
    horizontalOrder: true,
    fitWidth: true,
    gutter: 14
  });
});