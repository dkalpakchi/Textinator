/**
 * name: change_color
 * description: A plugin allowing to change a color of a label, potentially shared between labels
 * admin_filter: boolean
 * author: Dmytro Kalpakchi
 */

var plugin = function (cfg, labeler) {
  var config = {
    name: "change_color",
    verboseName: "Change color",
    storeFor: "label", // one of "label", "relation"
    dispatch: {}, // an event to be dispatched on update
    subscribe: [],
    allowSingletons: false, // takes effect only if storeFor = "relation"
  };

  const COLOR_CHANGE_EVENT = "labeler_color_change";
  const COLOR_CHANGED_EVENT = "labeler_color_changed";

  function isDefined(x) {
    return x != null && x !== undefined;
  }

  // taken from https://gist.github.com/THEtheChad/1297590/c67e4e44b190252e9bddb44183341027bdbf6e74
  function parseColor(color) {
    var cache,
      p = parseInt, // Use p as a byte saving reference to parseInt
      color = color.replace(/\s/g, ""); // Remove all spaces

    // Checks for 6 digit hex and converts string to integer
    if ((cache = /#([\da-fA-F]{2})([\da-fA-F]{2})([\da-fA-F]{2})/.exec(color)))
      cache = [p(cache[1], 16), p(cache[2], 16), p(cache[3], 16)];
    // Checks for 3 digit hex and converts string to integer
    else if ((cache = /#([\da-fA-F])([\da-fA-F])([\da-fA-F])/.exec(color)))
      cache = [
        p(cache[1], 16) * 17,
        p(cache[2], 16) * 17,
        p(cache[3], 16) * 17,
      ];
    // Checks for rgba and converts string to
    // integer/float using unary + operator to save bytes
    else if (
      (cache = /rgba\(([\d]+),([\d]+),([\d]+),([\d]+|[\d]*.[\d]+)\)/.exec(
        color
      ))
    )
      cache = [+cache[1], +cache[2], +cache[3], +cache[4]];
    // Checks for rgb and converts string to
    // integer/float using unary + operator to save bytes
    else if ((cache = /rgb\(([\d]+),([\d]+),([\d]+)\)/.exec(color)))
      cache = [+cache[1], +cache[2], +cache[3]];
    // Otherwise throw an exception to make debugging easier
    else throw color + " is not supported by $.parseColor";

    // Performs RGBA conversion by default
    isNaN(cache[3]) && (cache[3] = 1);

    // Adds or removes 4th value based on rgba support
    // Support is flipped twice to prevent erros if
    // it's not defined
    return cache.slice(0, 3 + !!$.support.rgba);
  }

  function getRandomColor(seedString) {
    var seed = xmur3(seedString),
      rng = sfc32(seed(), seed(), seed(), seed()),
      r = Math.floor(rng() * 255),
      g = Math.floor(rng() * 255),
      b = Math.floor(rng() * 255);

    return "rgba(" + r + "," + g + "," + b + ", 1)";
  }

  // taken from https://stackoverflow.com/questions/521295/seeding-the-random-number-generator-in-javascript
  function xmur3(str) {
    for (var i = 0, h = 1779033703 ^ str.length; i < str.length; i++) {
      h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
      h = (h << 13) | (h >>> 19);
    }
    return function () {
      h = Math.imul(h ^ (h >>> 16), 2246822507);
      h = Math.imul(h ^ (h >>> 13), 3266489909);
      return (h ^= h >>> 16) >>> 0;
    };
  }

  // taken from https://stackoverflow.com/questions/521295/seeding-the-random-number-generator-in-javascript
  function sfc32(a, b, c, d) {
    return function () {
      a >>>= 0;
      b >>>= 0;
      c >>>= 0;
      d >>>= 0;
      var t = (a + b) | 0;
      a = b ^ (b >>> 9);
      b = (c + (c << 3)) | 0;
      c = (c << 21) | (c >>> 11);
      d = (d + 1) | 0;
      t = (t + d) | 0;
      c = (c + t) | 0;
      return (t >>> 0) / 4294967296;
    };
  }

  // taken from https://stackoverflow.com/questions/1349404/generate-random-string-characters-in-javascript
  function makeSalt(length) {
    var result = "";
    var characters =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    var charactersLength = characters.length;
    for (var i = 0; i < length; i++) {
      result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
  }

  if (isDefined(cfg)) {
    for (var k in cfg) {
      config[k] = cfg[k];
    }
  }

  return {
    name: config.name,
    verboseName: config.verboseName,
    storage: {
      salt: {},
    },
    dispatch: config.dispatch,
    subscribe: config.subscribe,
    storeFor: config.storeFor,
    allowSingletons: config.allowSingletons,
    isAllowed: function (obj) {
      if (this.storeFor == "relation") {
        var relSpan = obj.querySelector("[data-m]"),
          relSpanDefined = isDefined(relSpan);

        if (relSpanDefined) {
          return relSpan.textContent != "+";
        } else {
          return this.allowSingletons;
        }
      } else {
        return true;
      }
    },
    exec: function (label, menuItem) {
      var colorInput = document.createElement("input"),
        cpicker = new JSColor(colorInput, { format: "rgba" }),
        control = this,
        id = label.getAttribute("data-i"),
        storage = this.storage,
        scope = undefined,
        prefix = undefined,
        updateUI = function (c) {
          var rgb = parseColor(c);

          // https://www.w3.org/TR/AERT/#color-contrast
          // https://stackoverflow.com/questions/596216/formula-to-determine-perceived-brightness-of-rgb-color
          var brightness = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2];
          var textColor = brightness > 125 ? "black" : "white";

          if (control.storeFor == "label") {
            label.setAttribute(
              "style",
              "background-color: " + c + "; color: " + textColor + ";"
            );
          } else if (control.storeFor == "relation") {
            var relSpan = label.querySelector('[data-m="r"]');
            if (isDefined(relSpan)) {
              relSpan.classList.add("is-badge");
              relSpan.setAttribute(
                "style",
                "background-color: " + c + "; color: " + textColor + ";"
              );
            } else if (control.allowSingletons) {
              label.setAttribute(
                "style",
                "background-color: " + c + "; color: " + textColor + ";"
              );
            }
          }
        },
        defaultColor = "rgba(255, 255, 255, 1)";

      if (this.storeFor == "label") {
        scope = "l" + id;
        prefix = "label";
        defaultColor = label.style.backgroundColor;
      } else if (this.storeFor == "relation") {
        var rel = label.querySelector('[data-m="r"]'),
          prefix = "relation";
        if (rel) {
          scope = "r" + rel.textContent;
        } else if (this.allowSingletons) {
          scope = "sr" + id;
          defaultColor = label.style.backgroundColor;
        }
      }

      // let's additionally set an option
      cpicker.option("previewSize", 50);

      // we can also set multiple options at once
      cpicker.option({
        width: 100,
        position: "right",
        backgroundColor: "#333",
        zIndex: 10000,
        onInput: function () {
          if (isDefined(label._tippy)) label._tippy.disable();
          if (isDefined(menuItem._tippy)) menuItem._tippy.disable();
        },
        onChange: function () {
          if (isDefined(label._tippy) && isDefined(menuItem._tippy)) {
            label._tippy.enable();
            menuItem._tippy.enable();
            label._tippy.show();
            menuItem._tippy.show();
          }

          storage[scope] = colorInput.value;

          const event = new Event("labeler_" + prefix + "_color_change", {
            bubbles: true,
          });
          document.dispatchEvent(event);
        },
      });

      if (scope != undefined) {
        colorInput.setAttribute("data-s", scope);

        if (storage["sr" + id] && scope.startsWith("r")) {
          storage[scope] = storage["sr" + id];
          delete storage["sr" + id];
        }

        cpicker.fromString(storage[scope] || defaultColor);

        if (colorInput.value) updateUI(colorInput.value);

        colorInput.addEventListener("change", function (e) {
          var target = e.target;
          storage[target.getAttribute("data-s")] = target.value;
          updateUI(target.value);
        });

        label.addEventListener(COLOR_CHANGE_EVENT, function (e) {
          var relSpan = label.querySelector('[data-m="r"]');
          if (
            control.storeFor == "relation" &&
            isDefined(relSpan) &&
            relSpan.textContent == e.detail.sender
          ) {
            if (!storage.salt.hasOwnProperty(scope))
              storage.salt[scope] = makeSalt(32);
            storage[scope] = getRandomColor(
              relSpan.textContent + storage.salt[scope]
            );

            const event = new Event(COLOR_CHANGED_EVENT, { bubbles: false });
            label.dispatchEvent(event);
          }
        });

        tippy(isDefined(menuItem) ? menuItem : label, {
          content: colorInput,
          interactive: true,
          interactiveBorder: 100,
          placement: "right",
          trigger: "click",
        });
      }
    },
  };
};
