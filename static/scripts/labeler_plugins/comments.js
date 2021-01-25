/**
 * name: comments
 * description: A plugin adding a text field to a marker's context menu
 * admin_filter: boolean
 * author: Dmytro Kalpakchi
 */

var plugin = function(cfg, labeler) {
  var config = {
    name: "comments",
    verboseName: 'Add a comment'
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
        placement: "right",
        trigger: 'click'
      });
    }
  }
};