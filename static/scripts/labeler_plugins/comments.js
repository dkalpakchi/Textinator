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
    storeFor: "label", // one of "label", "relation",
    dispatch: {},   // an event to be dispatched on update
    subscribe: [],
    sharedBetweenMarkers: false
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
    dispatch: config.dispatch,
    subscribe: config.subscribe,
    storeFor: config.storeFor,
    sharedBetweenMarkers: config.sharedBetweenMarkers,
    isAllowed: function(obj) {
      return labeler.markersArea != null;
    },
    exec: function(label, menuItem) {
      var id = label.getAttribute('data-i'),
          storage = this.storage,
          commentInput = document.createElement("input"),
          scope = undefined,
          prefix = undefined;

      if (this.storeFor == "label") {
        scope = "l" + id;
        prefix = "label";
      } else if (this.storeFor == "relation") {
        var rel = label.querySelector('[data-m="r"]');
        if (rel) {
          scope = "r" + rel.textContent;
          prefix = "relation";
        }
      }

      if (scope !== undefined) {
        commentInput.setAttribute('data-s', scope);
        commentInput.setAttribute('value', storage[scope] || '');
        commentInput.addEventListener('change', function(e) {
          var target = e.target;
          storage[target.getAttribute('data-s')] = target.value;
        }, false);
        commentInput.addEventListener('blur', function(e) {
          var target = e.target;
          const event = new Event("labeler_" + prefix + "_blur", {bubbles: true});
          target.dispatchEvent(event);
        })

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