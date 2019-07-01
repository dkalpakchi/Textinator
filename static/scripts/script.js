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
});