(function ($) {
  const utils = {
    isDefined: function (x) {
      return x != null && x !== undefined;
    },
    unique: function (arr) {
      const seen = new Set();
      return arr.filter(function (elem) {
        const key = elem["start"] + " -- " + elem["end"];
        let isDuplicate = seen.has(key);
        if (!isDuplicate) seen.add(key);
        return !isDuplicate;
      });
    },
    hex2rgb: function (hex) {
      let m = hex.match(/^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i);
      return {
        r: parseInt(m[1], 16),
        g: parseInt(m[2], 16),
        b: parseInt(m[3], 16),
      };
    },
    removeAllChildren: function (parentNode) {
      while (parentNode.lastChild) {
        parentNode.removeChild(parentNode.lastChild);
      }
    },
    resetSelect: function (sel) {
      sel.selectedIndex = 0;
    },
  };

  const explorer = {
    init: function () {
      this.textWidget = document.querySelector("#textWidget");
      this.textSelector = this.textWidget.querySelector("select#text");
      this.textContentArea = this.textWidget.querySelector("div#text");
      this.annotatorSelectors = {
        an1: document.querySelector("select#an1"),
        an2: document.querySelector("select#an2"),
      };
      this.annotationAreas = {
        an1: document.querySelector('[data-id="an1"]'),
        an2: document.querySelector('[data-id="an2"]'),
      };

      this.initEvents();
    },
    initEvents: function () {
      let ctx = this;

      this.textSelector.addEventListener("change", function (e) {
        let target = e.target;

        utils.removeAllChildren(ctx.textContentArea);

        if (target.selectedIndex !== 0) {
          ctx.loadText(target.options[target.selectedIndex].value);
        }
      });

      for (let s in this.annotatorSelectors) {
        this.annotatorSelectors[s].addEventListener(
          "change",
          function (e) {
            let target = e.target;

            utils.removeAllChildren(ctx.annotationAreas[target.id]);

            if (
              target.selectedIndex !== 0 &&
              ctx.textSelector.selectedIndex !== 0
            ) {
              let userSelected = target.options[target.selectedIndex].value,
                textSelected =
                  ctx.textSelector.options[ctx.textSelector.selectedIndex]
                    .value;

              ctx.loadAnnotations(textSelected, userSelected, target.id);
            }
          },
          false
        );
      }
    },
    loadText: function (textId) {
      let ctx = this;
      $.ajax({
        method: "GET",
        url: this.textWidget.getAttribute("data-u1"),
        dataType: "json",
        data: {
          c: textId,
        },
        success: function (data) {
          for (let ann in ctx.annotationAreas) {
            utils.removeAllChildren(ctx.annotationAreas[ann]);
            utils.resetSelect(ctx.annotatorSelectors[ann]);
          }

          if (!data.hasOwnProperty("error") && data.hasOwnProperty("context"))
            ctx.textContentArea.innerText = data.context;
        },
      });
    },
    loadAnnotations: function (textId, userId, annotatorKey) {
      let ctx = this;
      $.ajax({
        method: "GET",
        url: this.textWidget.getAttribute("data-u2"),
        dataType: "json",
        data: {
          c: textId,
          u: userId,
        },
        success: function (data) {
          ctx.populateAnnotations(annotatorKey, data.annotations);
        },
      });
    },
    createAnnotationElement: function (ann, isDivided) {
      let dataTypes = ["inputs", "labels"],
        groupContainer = document.createElement("div");
      if (!utils.isDefined(isDivided)) isDivided = false;
      groupContainer.className = "content";

      if (isDivided) groupContainer.className += " is-divided";

      for (let k in dataTypes) {
        if (utils.isDefined(ann[dataTypes[k]])) {
          for (let i = 0, len = ann[dataTypes[k]].length; i < len; i++) {
            let marker = document.createElement("div"),
              content = document.createElement("div"),
              contentWrapper = document.createElement("div"),
              inp = ann[dataTypes[k]][i];
            contentWrapper.className = "content";

            marker.innerText = inp.marker.name;
            marker.className = "tag";
            let mColor = inp.marker.color;
            marker.style.background = mColor;

            let rgb = utils.hex2rgb(mColor);
            let brightness = 0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b;
            let textColor = brightness > 125 ? "black" : "white";
            marker.style.color = textColor;

            if (dataTypes[k] == "inputs") content.innerText = inp.content;
            else content.innerText = inp.text;

            contentWrapper.appendChild(marker);
            contentWrapper.appendChild(content);
            groupContainer.appendChild(contentWrapper);
          }
        }
      }
      return groupContainer;
    },
    createAnnotationBatch: function (batch) {
      let ctx = this;
      let container = document.createElement("div"),
        header = document.createElement("header"),
        headerPart = document.createElement("div"),
        headerText = document.createElement("span"),
        contentPart = document.createElement("div");
      container.className = "card mb-2";
      contentPart.className = "card-content";
      header.className = "card-header";
      headerPart.className = "card-header-title";
      headerText.innerText = batch.created;
      headerPart.append(headerText);

      header.appendChild(headerPart);

      if (
        ctx.textWidget.hasAttribute("data-ue") &&
        batch.hasOwnProperty("id")
      ) {
        let editBatchButton = document.createElement("a"),
          bicon = document.createElement("i"),
          btext = document.createElement("span"),
          url = ctx.textWidget.getAttribute("data-ue").replace("!!!", batch.id);
        editBatchButton.href = url;
        editBatchButton.className = "is-pulled-right";
        editBatchButton.target = "_blank";
        bicon.className = "fas fa-external-link-alt mr-1";
        btext.innerText = "Edit";
        editBatchButton.appendChild(bicon);
        editBatchButton.appendChild(btext);
        headerPart.appendChild(editBatchButton);
      }

      container.appendChild(header);

      let batchKeys = Object.keys(batch).filter(
          (x) => x != "created" && x != "id"
        ),
        numBatchKeys = batchKeys.length;

      for (let bi = 0; bi < numBatchKeys; bi++) {
        contentPart.appendChild(
          ctx.createAnnotationElement(
            batch[batchKeys[bi]],
            bi != numBatchKeys - 1
          )
        );
      }
      container.append(contentPart);
      return container;
    },
    populateAnnotations: function (annotatorKey, annotations) {
      let ctx = this,
        annArea = this.annotationAreas[annotatorKey];
      for (let key in annotations) {
        let ann = annotations[key];
        annArea.appendChild(ctx.createAnnotationBatch(ann));
      }
    },
  };

  $(document).ready(function () {
    explorer.init();

    $("[id^=item-context-]").accordion({
      collapsible: true,
      active: false,
    });

    $("#flaggedCollapse").accordion({
      collapsible: true,
      active: false,
      icons: false,
    });

    $("#statsCollapse").accordion({
      collapsible: true,
      active: false,
      icons: false,
      heightStyle: "content",
    });

    $("#guidelinesButton").on("click", function () {
      $(".guidelines.modal").addClass("is-active");
    });

    $(".modal-close").on("click", function () {
      $(".modal").removeClass("is-active");
      // $('.countdown svg circle:last-child').trigger('cdAnimate');
    });

    $(".modal-background").on("click", function () {
      $(".modal").removeClass("is-active");
      // $('.countdown svg circle:last-child').trigger('cdAnimate');
    });

    $("a[download]").on("click", function () {
      var $btn = $(this),
        $form = $btn.closest("form");

      $btn.addClass("is-loading");
      $.ajax({
        method: "GET",
        url: $btn.attr("data-url"),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: $form.serializeObject(),
        success: function (data) {
          const blob = new Blob([JSON.stringify(data)], {
            type: "application/json",
          });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "export.json";

          a.addEventListener(
            "click",
            function () {
              setTimeout(function () {
                URL.revokeObjectURL(url);
                // a.removeEventListener('click', clickHandler);
                a.remove();
                // URL.revokeObjectURL(url);
              }, 150);
            },
            false
          );

          a.click();
          $btn.removeClass("is-loading");
        },
        error: function () {
          alert("Error while exporting a file!");
          $btn.removeClass("is-loading");
        },
      });
    });
  });
})(window.$);
