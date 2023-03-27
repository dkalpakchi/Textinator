(function ($, tippy, bulmaSlider) {
  $(document).ready(function () {
    // Guidelines "Show more" button
    let scrollTimer = setTimeout(function () {
      $(".button-scrolling").each(function (i, x) {
        if (x.scrollHeight > x.clientHeight) {
          clearTimeout(scrollTimer);
          let $button = $(
              "<button class='scrolling is-info button'>Show more</button>"
            ),
            $el = $(x),
            top = $el.scrollTop();

          $el.scroll(function () {
            let pos = $button.css("top")
              ? parseInt($button.css("top"), 10)
              : $button.position().top;
            $button.css("top", pos + $el.scrollTop() - top);
            top = $el.scrollTop();
            if ($el.scrollTop() + $el.innerHeight() >= $el[0].scrollHeight) {
              $button.hide();
            }
          });

          $button.on("click", function (e) {
            e.preventDefault();
            $button.prop("disabled", true);
            $el.animate(
              { scrollTop: $el.scrollTop() + 200 },
              {
                duration: 500,
                complete: function () {
                  $button.prop("disabled", false);
                },
              }
            );
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

    $("#guidelinesButton").on("click", function () {
      $(".guidelines.modal").addClass("is-active");
      $("[data-align]").on("click", function () {
        let $e = $(this),
          alignAttr = $e.attr("data-align"),
          $referent = $("#" + $e.attr("data-id"));

        $("[data-align]").removeClass("is-info is-selected");

        if (alignAttr == "left") {
          $referent.removeClass("right half center").addClass("left half");
        } else if (alignAttr == "right") {
          $referent.removeClass("left half center").addClass("right half");
        } else {
          $referent.removeClass("left right half").addClass("center");
        }
        $e.addClass("is-info is-selected");
      });
    });

    $(".modal-close").on("click", function () {
      $(".modal").removeClass("is-active");
      // $('.countdown svg circle:last-child').trigger('cdAnimate');
    });

    $(".modal-background").on("click", function () {
      $(".modal").removeClass("is-active");
      // $('.countdown svg circle:last-child').trigger('cdAnimate');
    });

    $("#guidelinesButton").click();

    /**
     * - Modals handling
     */

    bulmaSlider.attach();

    tippy("[data-meta]", {
      content: function (x) {
        let table = document.createElement("table"),
          tbody = document.createElement("tbody"),
          data = JSON.parse(x.querySelector("script").innerText);

        for (let x in data) {
          let row = document.createElement("tr"),
            keyCell = document.createElement("td"),
            valueCell = document.createElement("td");
          keyCell.innerText = x;
          if (Array.isArray(data[x])) valueCell.innerText = data[x].join("\n");
          else valueCell.innerText = data[x];
          row.appendChild(keyCell);
          row.appendChild(valueCell);
          tbody.appendChild(row);
        }
        table.appendChild(tbody);
        return table;
      },
      interactive: true,
      placement: "bottom",
      trigger: "click",
    });
  });
})(window.$, window.tippy, window.bulmaSlider);
