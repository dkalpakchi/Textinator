;(function() {
  var utils = {
    isDefined: function(x) {
      return x != null && x !== undefined;
    }
  };
  
  var contextBounded = [],
      contextFree = [],
      contextRelations = {},
      textArea = null,
      resetText = "",
      activeFilters = {};

  function markStatic(area, labels) {
    area.innerHTML = resetText;
    var acc = 0;
    var bounded = [];
    labels.sort(function(x, y) { return x['start'] - y['start']});
    var markers = {};
    for (var i = 0, len = labels.length; i < len; i++) {
      var cnodes = area.childNodes,
          text = cnodes[cnodes.length-1];

      const range = new Range();
      try {
        range.setStart(text, labels[i]['start'] - acc);
        range.setEnd(text, labels[i]['end'] - acc);
        acc = labels[i]['end'];
        bounded = [];
      } catch (e) {
        if (labels[i]['end'] <= acc) {
          // Nested labels
          if (bounded.length > 0 && labels[i]['end'] > bounded[bounded.length-1]['end']) {
            bounded.pop();
          }
          bounded.push({
            'span': markedSpan,
            'text': markedSpan.childNodes[0],
            'start': labels[i-1]['start'],
            'end': labels[i-1]['end'],
            'acc': 0
          });
          var l = bounded.length;
          var s = labels[i]['start'] - bounded[l-1]['start'] - bounded[l-1]['acc'];
          var e = labels[i]['end'] - bounded[l-1]['start'] - bounded[l-1]['acc'];
          range.setStart(bounded[l-1]['text'], s);
          range.setEnd(bounded[l-1]['text'], e);
          bounded[l-1]['acc'] = labels[i]['end'] - bounded[l-1]['start'];
        } else {
          // some labels might be repeated in which case we'll have a DOMException caught here
          bounded = [];
          continue;
        }
      }

      var markedSpan = document.createElement('span');
      markedSpan.className = "tag is-" + labels[i]['marker']['color'] + " is-medium";
      markers[labels[i]['marker']['color']] = labels[i]['marker'];

      var extra = "";
      for (var k in labels[i]['extra']) {
        if (labels[i]['extra'][k] != "")
          extra += k + ": " + labels[i]['extra'][k] + "<br>";
      }

      if (extra != "") {
        var extraSpan = document.createElement('span')
        extraSpan.innerHTML = extra;

        tippy(markedSpan, {
          content: extraSpan,
        });
      }
      range.surroundContents(markedSpan);
      if (bounded.length > 0) {
        var l = bounded.length;
        bounded[l-1]['text'] = bounded[l-1]['span'].childNodes[bounded[l-1]['span'].childNodes.length-1]
      }
    }

    var legend = document.createElement('legend'),
        label = document.createElement('label'),
        tagsDiv = document.createElement('div');
    label.className = "label"
    label.textContent = "Legend";
    legend.appendChild(document.createElement('hr'));
    legend.appendChild(label);
    tagsDiv.className = "tags";
    for (var k in markers) {
      var marker = document.createElement('span');
      marker.className = 'tag is-' + k + " is-normal";
      marker.textContent = markers[k]['name'];
      tagsDiv.appendChild(marker);
    }
    legend.appendChild(tagsDiv);
    area.appendChild(legend);

    var marked = area.querySelectorAll('span.tag');
    for (var i = 0; i < marked.length; i++) {
      var checker = marked[i],
          elements = [];
      while (checker.classList.contains('tag')) {
        elements.push(checker);
        checker = checker.parentNode;
      }

      for (var j = 0, len = elements.length; j < len; j++) {
        var pTopStr = elements[j].style.paddingTop,
            pBotStr = elements[j].style.paddingBottom,
            pTop = parseFloat(pTopStr.slice(0, -2)),
            pBot = parseFloat(pBotStr.slice(0, -2)),
            npTop = 10 + 10 * j,
            npBot = 10 + 10 * j;
        if (pTopStr == "" || (utils.isDefined(pTopStr) && !isNaN(pTop)))
          elements[j].style.paddingTop = npTop + "px";
        if (pBotStr == "" || (utils.isDefined(pBotStr) && !isNaN(pBot)))
          elements[j].style.paddingBottom = npBot + "px";
      }
    }
  }

  function getAnnotations(target, selectedId) {
    $.ajax({
      method: "GET",
      url: target.getAttribute('data-url'),
      data: {
        'context': selectedId
      },
      success: function(d) {
        $("#exploreText").text(d.data);
        resetText = d.data;
        contextBounded = d.bounded_labels;
        contextFree = d.free_labels;
        contextRelations = d.relations;
        if (d.is_static) {
          var annotations = $("#contextAnnotations");
          annotations.empty();
          for (var i = 0; i < contextBounded.length; i++) {
            var labels = contextBounded[i]['labels'],
                $li = $('<li>Input:' + contextBounded[i]['input'] + "</li>"),
                $div = $('<div class="alternative tags"></div>');
            for (var j = 0, len = labels.length; j < len; j++) {
              $div.append($(`
                <span class="tags has-addons">
                  <span class='tag is-${labels[j]['marker']['color']} is-medium'>${labels[j]['marker']['name']}</span>
                  <span class="tag is-medium">${labels[j]['text']}</span>
                  <span class="tag is-dark is-medium">${labels[j]['user']}, ${labels[j]['created']}</span>
                </span>`));
            }
            $li.append($div);
            annotations.append($li);
          }
        } else {
          var freeAnnotations = $("#contextFreeAnnotations");
          freeAnnotations.empty();
          var cf = {};
          for (var i = 0, len = contextFree.length; i < len; i++) {
            if (!(contextFree[i].batch in cf))
              cf[contextFree[i].batch] = [];
            cf[contextFree[i].batch].push(contextFree[i]);
          }
          contextFree = cf;

          freeAnnotations.append($('<option value="-1">Choose an annotation</option>'))
          for (var batch in contextFree) {
            freeAnnotations.append($('<option value="' + batch + '">' + batch + "</option>"))
          }
          var annotationsDiv = freeAnnotations.parent();
          annotationsDiv.parent().find('.loading').remove();
          if (contextFree.length <= 0) {
            annotationsDiv.removeClass('select');
            annotationsDiv.empty();
            annotationsDiv.text("No annotations found");
          }
          annotationsDiv.show();

          var annotations = $("#contextAnnotations");
          annotations.empty();
          annotations.append($('<option value="-1">Choose an annotation</option>'))
          for (var i = 0; i < contextBounded.length; i++) {
            var inp = contextBounded[i]['input'];
            annotations.append($('<option value="' + i + '">Input:' + inp + "</option>"))
          }
          var annotationsDiv = annotations.parent();
          annotationsDiv.parent().find('.loading').remove();
          if (contextBounded.length <= 0) {
            annotationsDiv.removeClass('select');
            annotationsDiv.empty();
            annotationsDiv.text("No annotations found");
          }
          annotationsDiv.show();

          var cr = {},
              relations = $("#contextRelations");
          relations.empty();
          relations.append($('<option value="-1">Choose a relation</option>'))
          for (var i = 0, len = contextRelations.length; i < len; i++) {
            if (!(contextRelations[i].batch in cr))
              cr[contextRelations[i].batch] = {
                'obj': contextRelations[i],
                'labels': []
              };
            cr[contextRelations[i].batch]['labels'].push(contextRelations[i]['first']);
            cr[contextRelations[i].batch]['labels'].push(contextRelations[i]['second']);
          }
          contextRelations = cr;
          
          var j = 1;
          for (var key in contextRelations) {
            var obj = contextRelations[key]['obj'];
            relations.append($('<option value="' + key + '">Relation ' + j + ": " + obj.rule.name +
                " (created by " + obj['user'] + " on " + obj['created'] + ")</option>"));
            j++;
          }
          var relationsDiv = relations.parent();
          relationsDiv.parent().find('.loading').remove();
          if (j <= 1) {
            relationsDiv.removeClass('select');
            relationsDiv.empty();
            relationsDiv.text("No relations found");
          }
          relationsDiv.show();
        }
        $("#exploreText").removeClass('element is-loading');
      },
      errors: function() {
        console.log("ERROR")
        $("#exploreText").removeClass('element is-loading');
      }
    })
  }

  function hideByFilters() {
    $('#contextRelations option').show();
    for (var batch in contextRelations) {
      var cr = contextRelations[batch]['labels'];
      for (var i = 0, len = cr.length; i < len; i++) {
        for (var l in activeFilters) {
          if (cr[i].marker.short == l) {
            for (var key in activeFilters[l]) {
              var extra = cr[i].extra,
                  filterValue = activeFilters[l][key];
              if ((key in extra && typeof filterValue !== "boolean" && extra.hasOwnProperty(key) && extra[key] != filterValue) || 
                (!(key in extra) && typeof filterValue === "boolean")) {
                $('#contextRelations option[value="' + batch + '"]').hide();
              }
            }
          }
        }
      }
    }
  }

  $(document).ready(function() {
    textArea = document.querySelector('#exploreText');
    resetText = textArea.textContent;

    $("[id^=item-context-]").accordion({
      collapsible: true,
      active: false
    });

    $("#flaggedCollapse").accordion({
      collapsible: true,
      active: false,
      icons: false,
    });

    $("#explorerFilters").accordion({
      collapsible: true,
      active: false,
      icons: false,
    });

    var select = document.querySelector('#exploreContexts');
    getAnnotations(select, select.value);

    $('#exploreContexts').on('change', function(e) {
      var target = e.target,
          selectedId = target.value;
      $("#exploreText").addClass('element is-loading');
      getAnnotations(target, selectedId);
    });

    $('#contextFreeAnnotations').on('change', function(e) {
      var target = e.target,
          selected = target.value;
      if (selected != -1)
        markStatic(textArea, contextFree[selected]);
      else
        textArea.innerHTML = resetText;
    });

    $('#contextAnnotations').on('change', function(e) {
      var target = e.target,
          selected = target.value;
      if (selected != -1)
        markStatic(textArea, contextBounded[selected]);
      else
        textArea.innerHTML = resetText;
    });

    $('#contextRelations').on('change', function(e) {
      var target = e.target,
          selected = target.value;
      if (selected != -1)
        markStatic(textArea, contextRelations[selected]['labels']);
      else 
        textArea.innerHTML = resetText;
    });

    $('#contextFreeAnnotations').parent().hide();
    $('#contextAnnotations').parent().hide();
    $('#contextRelations').parent().hide();

    $("#filterForm").on('submit', function(e) {
      e.preventDefault();
      var target = e.target;
      var res = $(target).serializeObject();
      for (var k in res) {
        var parts = k.split("__");
        if (!(parts[0] in activeFilters)) {
          activeFilters[parts[0]] = {}
        }
        activeFilters[parts[0]][parts[1]] = res[k] == 'on' ? true : res[k];
      }
      hideByFilters();
    });

    $('a[download]').on('click', function() {
      var $btn = $(this);
      $btn.addClass('is-loading');
      $.ajax({
        method: "GET",
        url: $btn.attr('data-url'),
        contentType: 'application/json; charset=utf-8',
        dataType: 'json',
        success: function(data) {
          const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'export.json';
          
          a.addEventListener('click', function(e) {
            setTimeout(function() {
              URL.revokeObjectURL(url);
              a.removeEventListener('click', clickHandler);
              a.remove();
              URL.revokeObjectURL(url);
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