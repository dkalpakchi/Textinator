;(function() {
  var utils = {
    isDefined: function(x) {
      return x != null && x !== undefined;
    },
    unique: function(arr) {
      const seen = new Set();
      return arr.filter(function(elem) {
        const key = elem['start'] + " -- " + elem['end'];
        var isDuplicate = seen.has(key);
        if (!isDuplicate)
          seen.add(key);
        return !isDuplicate;
      });
    },
    hex2rgb: function(hex) {
      var m = hex.match(/^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i);
      return {
        r: parseInt(m[1], 16),
        g: parseInt(m[2], 16),
        b: parseInt(m[3], 16)
      };
    }
  };

  var explorer = {
    init: function() {
      this.textWidget = document.querySelector('#textSelector');
      this.textSelector = this.textWidget.querySelector('select#text');
      this.annotatorSelectors = {
        'an1': document.querySelector('select#an1'),
        'an2': document.querySelector('select#an2')
      };
      this.annotationsArea = {
        'an1': document.querySelector('[data-id="an1"]'),
        'an2': document.querySelector('[data-id="an2"]')
      };

      this.initEvents()
    },
    initEvents: function() {
      var ctx = this;
      for (var s in this.annotatorSelectors) {
        this.annotatorSelectors[s].addEventListener('change', function(e) {
          var target = e.target;

          if (target.selectedIndex != 0 && ctx.textSelector.selectedIndex != 0) {
            var userSelected = target.options[target.selectedIndex].value,
                textSelected = ctx.textSelector.options[ctx.textSelector.selectedIndex].value;

            ctx.loadAnnotations(textSelected, userSelected, target.id);
          }
        }, false);
      }
    },
    loadAnnotations: function(text_id, user_id, annotator_key) {
      var ctx = this;
      $.ajax({
        method: "GET",
        url: this.textWidget.getAttribute('data-url'),
        dataType: 'json',
        data: {
          c: text_id,
          u: user_id
        },
        success: function(data) {
          ctx.populateAnnotations(annotator_key, data.annotations);
        }
      })
    },
    createAnnotationElement: function(ann) {
      var dataTypes = ['inputs', 'labels'];
      var container = document.createElement('div'),
          header = document.createElement('header'),
          headerPart = document.createElement('div'),
          contentPart = document.createElement('div');
      container.className = "card";
      contentPart.className = "card-content";
      header.className = "card-header";
      headerPart.className = "card-header-title";
      headerPart.innerText = ann.created;

      header.appendChild(headerPart);
      container.appendChild(header);

      for (var k in dataTypes) {
        if (utils.isDefined(ann[dataTypes[k]])) {
          for (var i = 0, len = ann[dataTypes[k]].length; i < len; i++) {
            var marker = document.createElement('div'),
                content = document.createElement('div'),
                contentWrapper = document.createElement('div'),
                inp = ann[dataTypes[k]][i];
            contentWrapper.className = "content";

            marker.innerText = inp.marker.name;
            marker.className = "tag";
            mColor = inp.marker.color;
            marker.style.background = mColor;

            rgb = utils.hex2rgb(mColor);
            brightness = 0.299 * rgb.r + 0.587 * rgb.g + 0.114 * rgb.b;
            textColor = (brightness > 125) ? 'black' : 'white';
            marker.style.color = textColor;

            if (dataTypes[k] == 'inputs') 
              content.innerText = inp.content;
            else
              content.innerText = inp.text;

            contentWrapper.appendChild(marker);
            contentWrapper.appendChild(content);
            contentPart.appendChild(contentWrapper);
          }
        }
      }
      container.appendChild(contentPart);
      return container;
    },
    populateAnnotations: function(annotator_key, annotations) {
      var ctx = this,
          annArea = this.annotationsArea[annotator_key];
      for (var key in annotations) {
        var ann = annotations[key];
        annArea.appendChild(ctx.createAnnotationElement(ann));
      }
    }
  }
  

  $(document).ready(function() {
    explorer.init()

    $("[id^=item-context-]").accordion({
      collapsible: true,
      active: false
    });

    $("#flaggedCollapse").accordion({
      collapsible: true,
      active: false,
      icons: false,
    });

    $('a[download]').on('click', function() {
      var $btn = $(this),
          $form = $btn.closest('form');

      $btn.addClass('is-loading');
      $.ajax({
        method: "GET",
        url: $btn.attr('data-url'),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        data: $form.serializeObject(),
        success: function(data) {
          const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'export.json';
          
          a.addEventListener('click', function(e) {
            setTimeout(function() {
              URL.revokeObjectURL(url);
              // a.removeEventListener('click', clickHandler);
              a.remove();
              // URL.revokeObjectURL(url);
            }, 150);
          }, false);

          a.click();          
          $btn.removeClass('is-loading');
        },
        error: function() {
          alert("Error while exporting a file!");
          $btn.removeClass('is-loading');
        }
      });
    });
  })
})();
