;(function() {
  var contextBounded = [],
      contextFree = [],
      contextRelations = {},
      textArea = null,
      resetText = "",
      activeFilters = {};

  function markStatic(area, labels) {
    area.innerHTML = resetText;
    var acc = 0;
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
      } catch (e) {
        // some labels might be repeated in which case we'll have a DOMException caught here
        continue;
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
    }

    var legend = document.createElement('legend'),
        label = document.createElement('label');
    label.className = "label"
    label.textContent = "Legend";
    legend.appendChild(document.createElement('hr'));
    legend.appendChild(label);
    for (var k in markers) {
      var marker = document.createElement('span');
      marker.className = 'tag is-' + k + " is-normal";
      marker.textContent = markers[k]['name'];
      legend.appendChild(marker);
    }
    area.appendChild(legend);
  }

  function getAnnotations(target, selectedId) {
    $.ajax({
      method: "GET",
      url: target.getAttribute('data-url'),
      data: {
        'context': selectedId
      },
      success: function(d) {
        console.log(d)
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
          var annotations = $("#contextAnnotations");
          annotations.empty();
          for (var i = 0; i < contextBounded.length; i++) {
            var inp = contextBounded[i]['input'];
            annotations.append($('<option value="' + i + '">Input:' + inp + "</option>"))
          }

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

    $('#contextAnnotations').on('change', function(e) {
      var target = e.target,
          selected = target.value;
      if (selected != -1)
        markStatic(textArea, contextBounded[selected]['labels']);
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
  })
})();