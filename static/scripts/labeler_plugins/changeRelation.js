/**
 * name: change_rel
 * description: A plugin allowing to change a relationship of a label
 * author: Dmytro Kalpakchi
 */

var plugin = function(cfg, labeler) {
  var config = {
    name: "change_rel",
    verboseName: 'Change relation'
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
    update: 'labeler_relationschange',
    isAllowed: function(obj) {
      // only if it's part of the relation
      return document.querySelector('div.marker[data-s="' + obj.getAttribute('data-s') + '"]')
                     .getAttribute('data-submittable') == 'false';
    },
    exec: function(label, menuItem) {
      function createOption(val, idx) {
        var option = document.createElement('option');
        option.value = idx;
        option.textContent = val;
        return option;
      }

      var select = document.createElement('select'),
          relSpan = label.querySelector('[data-m="r"]'),
          relId = isDefined(relSpan) ? parseInt(relSpan.textContent) : -1;

      select.appendChild(createOption("no", -1));
      var lst = labeler.getAvailableRelationIds();
      for (var k in lst) {
        select.appendChild(createOption(lst[k], lst[k]));
      }
      select.value = relId;

      select.addEventListener('change', function(e) {
        var target = e.target,
            idx = parseInt(target.value);
        labeler.changeRelation(label, relId, idx);
        instance.hide();
      }, false);

      const instance = tippy(isDefined(menuItem) ? menuItem : label, {
        content: select,
        trigger: 'click',
        interactive: true,
        placement: "right",
        interactiveBorder: 100
      });
    }
  }
};