/**
 * name: slider
 * description: A plugin adding a slider to a marker's context menu
 * admin_filter: range
 * author: Dmytro Kalpakchi
 */

var plugin = function (cfg, labeler) {
  let config = {
    name: "slider",
    verboseName: "Add a score",
    min: 0,
    max: 100,
    step: 10,
    default: 50,
    dispatch: {},
    subscribe: [],
  };

  function isDefined(x) {
    return x != null && x !== undefined;
  }

  if (isDefined(cfg)) {
    for (let k in cfg) {
      config[k] = cfg[k];
    }
  }

  return {
    name: config.name,
    verboseName: config.verboseName,
    storage: {},
    dispatch: config.dispatch,
    subscribe: config.subscribe,
    initOnce: false,
    isAllowed: function (obj) {
      return labeler.markersArea != null;
    },
    exec: function (label, menuItem) {
      let id = label.getAttribute("data-i"),
        storage = this.storage,
        sliderInput = document.createElement("input");
      sliderInput.setAttribute("type", "range");
      sliderInput.setAttribute("min", config.min);
      sliderInput.setAttribute("max", config.max);
      sliderInput.setAttribute("step", config.step);
      sliderInput.setAttribute("data-i", id);
      if (!(id in storage)) storage[id] = config.default;
      sliderInput.value = storage[id];
      sliderInput.addEventListener(
        "change",
        function (e) {
          let target = e.target;
          storage["l" + parseInt(target.getAttribute("data-i"), 10)] =
            target.value;
        },
        false
      );

      tippy(isDefined(menuItem) ? menuItem : label, {
        content: sliderInput,
        interactive: true,
        placement: "right",
        trigger: "click",
      });
    },
  };
};
