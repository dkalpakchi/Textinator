/**
 * name: select
 * description: A plugin allowing to select from the list of alternatives
 * author: Dmytro Kalpakchi
 */

var plugin = function(cfg, labeler) {
  var config = {
    name: "select",
    verboseName: 'Select from a list'
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
    isAllowed: function() {
      return labeler.markersArea != null;
    },
    exec: function(label, menuItem) {
      var id = label.getAttribute('data-i'),
          storage = this.storage,
          commentInput = document.createElement("input");
      commentInput.setAttribute('data-i', id);
      commentInput.setAttribute('value', storage[id] || '');
      commentInput.addEventListener('change', function(e) {
        var target = e.target;
        storage[parseInt(target.getAttribute('data-i'))] = target.value;
      }, false);

      tippy(isDefined(menuItem) ? menuItem : label, {
        content: commentInput,
        interactive: true,
        distance: 0,
        placement: "right"
      });
    }
  }
};