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
      var table = document.createElement('table');
      table.className = "table";
      for (var k in dataTypes) {
        if (utils.isDefined(ann[dataTypes[k]])) {
          for (var i = 0, len = ann[dataTypes[k]].length; i < len; i++) {
            var markerCell = document.createElement('td'),
                contentCell = document.createElement('td'),
                inp = ann[dataTypes[k]][i],
                tr = document.createElement('tr');
            markerCell.innerText = inp.marker.name;

            if (dataTypes[k] == 'inputs') 
              contentCell.innerText = inp.content;
            else
              contentCell.innerText = inp.text;
            tr.appendChild(markerCell);
            tr.appendChild(contentCell);
            table.appendChild(tr);
          }
        }
      }
      return table;
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
