/**
 * name: comments
 * description: A plugin adding a text field to a marker's context menu
 * author: dmytro
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
    isAllowed: function() {
      return labeler.markersArea == null ? false : labeler.markersArea.getAttribute('data-comment') == 'true';
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