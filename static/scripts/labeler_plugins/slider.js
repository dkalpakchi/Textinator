/**
 * name: slider
 * description: A plugin adding a slider to a marker's context menu
 * author: Dmytro Kalpakchi
 */

var plugin = function(cfg, labeler) {
  var config = {
    name: "slider",
    verboseName: 'Add a score',
    min: 0,
    max: 100,
    step: 10,
    default: 50
  }

  function isDefined(x) {
    return x != null && x !== undefined;
  }

  if (isDefined(cfg)) {
    for (var k in cfg) {
      config[k] = cfg[k];
    }
  }

  return {
    name: config.name,
    verboseName: config.verboseName,
    storage: {},
    update: false,
    isAllowed: function(obj) {
      return labeler.markersArea != null;
    },
    exec: function(label, menuItem) {
      var id = label.getAttribute('data-i'),
          storage = this.storage,
          sliderInput = document.createElement("input");
      sliderInput.setAttribute('type', 'range');
      sliderInput.setAttribute('min', config.min);
      sliderInput.setAttribute('max', config.max);
      sliderInput.setAttribute('step', config.step);
      sliderInput.setAttribute('data-i', id);
      if (!(id in storage))
        storage[id] = config.default
      sliderInput.setAttribute('value', storage[id]);
      sliderInput.addEventListener('change', function(e) {
        var target = e.target;
        storage[parseInt(target.getAttribute('data-i'))] = target.value;
      }, false);

      tippy(isDefined(menuItem) ? menuItem : label, {
        content: sliderInput,
        interactive: true,
        placement: "right",
        trigger: 'click'
      });
    }
  }
};