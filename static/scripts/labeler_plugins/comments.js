/**
 * name: comments
 * description: A plugin adding a text field to a marker's context menu, potentially shared between markers
 * admin_filter: boolean
 * author: Dmytro Kalpakchi
 */

var plugin = function(cfg, labeler) {
  var config = {
    name: "comments",
    verboseName: 'Add a comment',
    store_for: "label", // one of "label", "relation",
    update: false,
    initOnce: false
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
    update: config.update,
    initOnce: config.initOnce,
    isAllowed: function(obj) {
      return labeler.markersArea != null;
    },
    exec: function(label, menuItem) {
      var id = label.getAttribute('data-i'),
          storage = this.storage,
          commentInput = document.createElement("input"),
          scope = undefined;

      if (config.store_for == "label") {
        scope = "l" + id;
      } else if (config.store_for == "relation") {
        var rel = label.querySelector('[data-m="r"]');
        if (rel) {
          scope = "r" + rel.textContent;
        }
      }

      if (scope !== undefined) {
        commentInput.setAttribute('data-s', scope);
        commentInput.setAttribute('value', storage[scope] || '');
        commentInput.addEventListener('change', function(e) {
          var target = e.target;
          storage[target.getAttribute('data-s')] = target.value;
        }, false);

        tippy(isDefined(menuItem) ? menuItem : label, {
          content: commentInput,
          interactive: true,
          placement: "right",
          trigger: 'click'
        });  
      }
      
    }
  }
};