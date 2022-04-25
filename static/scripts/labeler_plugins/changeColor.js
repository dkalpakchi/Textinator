/**
 * name: change_color
 * description: A plugin allowing to change a color of a label, potentially shared between labels
 * admin_filter: boolean
 * author: Dmytro Kalpakchi
 */

var plugin = function(cfg, labeler) {
  var config = {
    name: "change_color",
    verboseName: 'Change color',
    storeFor: "label", // one of "label", "relation"
    dispatch: {},   // an event to be dispatched on update
    subscribe: [],
    sharedBetweenMarkers: false
  }

  function isDefined(x) {
    return x != null && x !== undefined;
  }

  // taken from https://gist.github.com/THEtheChad/1297590/c67e4e44b190252e9bddb44183341027bdbf6e74
  function parseColor(color) {
    var cache,
        p = parseInt, // Use p as a byte saving reference to parseInt
        color = color.replace(/\s/g,''); // Remove all spaces
    
    // Checks for 6 digit hex and converts string to integer
    if (cache = /#([\da-fA-F]{2})([\da-fA-F]{2})([\da-fA-F]{2})/.exec(color)) 
        cache = [p(cache[1], 16), p(cache[2], 16), p(cache[3], 16)];
        
    // Checks for 3 digit hex and converts string to integer
    else if (cache = /#([\da-fA-F])([\da-fA-F])([\da-fA-F])/.exec(color))
        cache = [p(cache[1], 16) * 17, p(cache[2], 16) * 17, p(cache[3], 16) * 17];
        
    // Checks for rgba and converts string to
    // integer/float using unary + operator to save bytes
    else if (cache = /rgba\(([\d]+),([\d]+),([\d]+),([\d]+|[\d]*.[\d]+)\)/.exec(color))
        cache = [+cache[1], +cache[2], +cache[3], +cache[4]];
        
    // Checks for rgb and converts string to
    // integer/float using unary + operator to save bytes
    else if (cache = /rgb\(([\d]+),([\d]+),([\d]+)\)/.exec(color))
        cache = [+cache[1], +cache[2], +cache[3]];
        
    // Otherwise throw an exception to make debugging easier
    else throw color + ' is not supported by $.parseColor';
    
    // Performs RGBA conversion by default
    isNaN(cache[3]) && (cache[3] = 1);
    
    // Adds or removes 4th value based on rgba support
    // Support is flipped twice to prevent erros if
    // it's not defined
    return cache.slice(0,3 + !!$.support.rgba);
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
    allowSingletons: config.allowSingletons,
    sharedBetweenMarkers: config.sharedBetweenMarkers,
    isAllowed: function(obj) {
      if (this.storeFor == 'relation') {
        var relSpan = obj.querySelector('[data-m]'),
            relSpanDefined = isDefined(relSpan);

        if (relSpanDefined) {
          return relSpan.textContent != '+';
        } else {
          return this.sharedBetweenMarkers;
        }
      } else {
        return true;
      }
    },
    exec: function(label, menuItem) {
      var colorInput = document.createElement("input"),
          cpicker = new JSColor(colorInput, {format:'rgba'}),
          control = this,
          id = label.getAttribute('data-i'),
          storage = this.storage,
          scope = undefined,
          prefix = undefined,
          updateUI = function(c) {
            var rgb = parseColor(c);

            // https://www.w3.org/TR/AERT/#color-contrast
            // https://stackoverflow.com/questions/596216/formula-to-determine-perceived-brightness-of-rgb-color
            var brightness = 0.299*rgb[0] + 0.587*rgb[1] + 0.114*rgb[2];
            var textColor = brightness > 125 ? 'black' : 'white';

            if (control.storeFor == 'label') {
              label.setAttribute('style', "background-color: " + c + "; color: " + textColor + ";");
            } else if (control.storeFor == 'relation') {
              var relSpan = label.querySelector('[data-m="r"]');
              relSpan.classList.add('is-badge');
              relSpan.setAttribute('style', "background-color: " + c + "; color: " + textColor + ";");
            }
          };

      if (this.storeFor == "relation") {
        var rel = label.querySelector('[data-m="r"]'),
            prefix = "relation";
        if (rel) {
          scope = "r" + rel.textContent;
        } else if (this.allowSingletons) {
          scope = "sr" + id;
        }
      }

      // let's additionally set an option
      cpicker.option('previewSize', 50);

      // we can also set multiple options at once
      cpicker.option({
        'width': 100,
        'position': 'right',
        'backgroundColor': '#333',
        'zIndex': 10000,
        'onInput': function() {
          label._tippy.disable();
          menuItem._tippy.disable();
        },
        'onChange': function() {
          label._tippy.enable();
          menuItem._tippy.enable();
          label._tippy.show();
          menuItem._tippy.show();
        }
      });

      if (scope != undefined) {
        colorInput.setAttribute('data-s', scope);

        if (storage["sr" + id] && scope.startsWith('r')) {
          storage[scope] = storage["sr" + id];
          delete storage["sr" + id];
        }
        colorInput.setAttribute('value', storage[scope] || '');

        if (colorInput.value)
          updateUI(colorInput.value);
      }

      colorInput.addEventListener('change', function(e) {
        var target = e.target;
        updateUI(target.value);
        storage[target.getAttribute('data-s')] = target.value;
      });
      
      colorInput.addEventListener('blur', function(e) {
        var target = e.target;
        const event = new Event("labeler_" + prefix + "_blur", {bubbles: true});
        target.dispatchEvent(event);
      })

      tippy(isDefined(menuItem) ? menuItem : label, {
        content: colorInput,
        interactive: true,
        interactiveBorder: 100,
        placement: "right",
        trigger: 'click'
      });
    }
  }
};