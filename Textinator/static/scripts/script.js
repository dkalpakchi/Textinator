(function ($) {
  $(document).ready(function () {
    $("div[data-link]").on("click", function (e) {
      e.preventDefault();
      document.location.href = $(this).attr("data-link");
    });

    $("[data-replace-closest]").on("click", function (e) {
      e.preventDefault();
      let $this = $(this),
        selector = $this.attr("data-replace-closest"),
        $form = $this.closest("form"),
        url = $form.attr("action"),
        method = $form.attr("method");
      $.ajax({
        url: url,
        type: method,
        dataType: "json",
        data: $form.serializeObject(),
        success: function () {
          $this.closest(selector).remove();
        },
        error: function () {
          alert("Error dismissing the announcement!");
        },
      });
    });

    $(".tabs li[data-tab]").on("click", function () {
      var tab = $(this).data("tab"),
        $ul = $(this).closest("ul"),
        $container = $ul.parent();

      $ul.find("li").removeClass("is-active");
      $(this).addClass("is-active");

      $('div[data-from="' + $container.data("for") + '"]').removeClass(
        "is-active"
      );
      $('div[data-content="' + tab + '"]').addClass("is-active");
      const ev = new Event("Textinator:tab:switch");
      document.dispatchEvent(ev);
    });

    // Check for click events on the navbar burger icon
    $(".navbar-burger").click(function () {
      // Toggle the "is-active" class on both the "navbar-burger" and the "navbar-menu"
      $(".navbar-burger").toggleClass("is-active");
      $(".navbar-menu").toggleClass("is-active");
    });

    var joinFormSubmit = function (e) {
      e.preventDefault();
      e.stopPropagation();

      var $target = $(e.target).closest("a"),
        $inputForm = $target.find("form"),
        inputFormData = $inputForm.serializeObject(),
        $footer = $target.closest("footer");

      $.ajax({
        method: "POST",
        url: $inputForm.attr("action"),
        dataType: "json",
        data: inputFormData,
        success: function (data) {
          if (data["result"] == "joined") {
            $target.find("span").text("Leave");
            $footer.prepend($(data["template"]));
          } else {
            $target.find("span").text("Join");
            $footer.find("a:first-child").remove();
          }
          $target.blur();
        },
        error: function () {
          console.log("ERROR!");
        },
      });
    };

    $("a#joinButton").on("click", joinFormSubmit);

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

    $("nav .dropdown").on("click", function () {
      $(this).toggleClass("is-active");
    });

    if ($.prototype.sortable !== undefined) {
      $("#sortable").sortable();
      $("#sortable").disableSelection();
    }

    if ($.prototype.validate !== undefined) {
      $("form").validate({
        errorClass: "help is-danger",
      });
    }

    $('input[type!="hidden"]').each(function () {
      if ($(this).attr("data-required") == "true") {
        $(this).rules("add", {
          required: true,
        });
      }
    });

    if ($.prototype.masonry !== undefined) {
      $(".masonry-grid").masonry({
        itemSelector: ".masonry-grid-item",
        horizontalOrder: true,
        fitWidth: true,
        gutter: 14,
      });
    }

    if ($.prototype.accordion !== undefined) {
      $('[data-id="accordion"]').accordion({
        collapsible: true,
        active: false,
      });
    }
  });
})(window.jQuery);
