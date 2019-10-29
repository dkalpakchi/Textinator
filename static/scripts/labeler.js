$(document).ready(function() {
  var chunks = [],                                          // the array of all chunk of text marked with a label, but not submitted yet
      relations = [],                                       // the array of all relations for this article, not submitted yet
      lastNodeInRelationId = 0,                             // TODO: maybe remove
      selectorArea = document.querySelector('.selector'),   // the area where the article is
      resetTextHTML = selectorArea.innerHTML,               // the HTML of the loaded article
      resetText = selectorArea.textContent,                 // the text of the loaded article
      contextSize = $('#taskArea').data('context'),         // the size of the context to be saved 'p', 't' or 'no'
      qStart = new Date(),                                  // the time the page was loaded or the last submission was made
      labelId = 0,                                          // internal JS label id for the labels of the current article
      activeLabels = labelId,                               // a number of labels currently present in the article
      radius = 10,
      graphIds = [],
      currentRelationId = null;

  $('.button-scrolling').each(function(i, x) {
    var $button = $("<button class='scrolling is-link button'>Show more</button>");
    var $el = $(x);
    var top = $el.scrollTop();

    $el.scroll(function(e) {
      var pos = $button.css('top') ? parseInt($button.css('top')) : $button.position().top;
      $button.css('top', pos + $el.scrollTop() - top);
      top = $el.scrollTop();
      if ($el.scrollTop() + $el.innerHeight() >= $el[0].scrollHeight) {
        $button.hide();
      }
    });

    $button.on('click', function(e) {
      e.preventDefault();
      $button.prop('disabled', true);
      $el.animate({ scrollTop: $el.scrollTop() + 200 }, {
        duration: 500,
        complete: function() {
          $button.prop('disabled', false);
        }
      });
      if ($el.scrollTop() + $el.innerHeight() >= $el[0].scrollHeight) {
        $button.hide();
      }
    });

    $el.append($button);
  });

  // initialize pre-markers, i.e. mark the specified words with a pre-specified marker
  function initPreMarkers() {
    labelId = 0;
    $('article.text span.tag').each(function(i, node) {
      node.setAttribute('data-i', labelId);
      updateChunkFromNode(node);

      node.querySelector('button.delete').addEventListener('click', function(e) {
        e.stopPropagation();
        var el = e.target,
            parent = el.parentNode; // actual span

        chunks.splice(labelId, 1);
        mergeWithNeighbors(parent);
        $(el).prop('in_relation', false);
        resetTextHTML = selectorArea.innerHTML
        activeLabels--;
      })
      labelId++;
    })
    activeLabels = labelId;
  }

  // do initialize pre-markers for the current article
  initPreMarkers();

  // disable the undo button, since we haven't submitted anything
  $('#undoLast').attr('disabled', true);

  // calculate the length of the text preceding the node
  // inParagraph is a boolean variable indicating whether preceding text is taken only from the current paragraph or from the whole article
  function previousTextLength(node, inParagraph) {
    if (inParagraph === undefined) inParagraph = true;

    var len = 0;
    var prev = node.previousSibling;

    // paragraph scope
    while (prev != null) {
      if (prev.nodeType == 1) {
        if (prev.tagName == "BR") {
          // if newline
          len += 1
        } else if ((prev.tagName == "SPAN" && prev.classList.contains("tag"))) {
          // if there is a label
          len += prev.textContent.length
        }
      } else if (prev.nodeType == 3) {
        len += prev.length
      }
      prev = prev.previousSibling
    }

    if (inParagraph) return len;

    // all text scope
    // Find previous <p>
    var parent = node.parentNode;
    if (parent != null) {
      var parentSibling = parent.previousElementSibling;
      while (parentSibling != null) {
        if (parentSibling.tagName == "P") {
          len += parentSibling.textContent.length + 2; // +2 because P
        }
        parentSibling = parentSibling.previousElementSibling;
      }
    }
    return len;
  }

  // merge the given node with two siblings - used when deleting a label
  function mergeWithNeighbors(node) {
    // check if text node
    var next = node.nextSibling,
        prev = node.previousSibling,
        parent = node.parentNode;

    if (prev.nodeType == 3 && next.nodeType == 3) {
      parent.replaceChild(document.createTextNode(prev.data + node.textContent + next.data), prev);
      parent.removeChild(node);
      parent.removeChild(next);
    } else if (prev.nodeType == 3) {
      parent.replaceChild(document.createTextNode(prev.data + node.textContent), prev);
      parent.removeChild(node);
    } else if (next.nodeType == 3) {
      parent.replaceChild(document.createTextNode(node.textContent + next.data), node);
      parent.removeChild(next);
    }
  }

  function removeAllChildren(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function resetArticle() {
    var node = document.querySelector('.selector');
    removeAllChildren(node);
    node.innerHTML = resetTextHTML;
  }

  // activate labels on click
  $('article.text span.tag').on('click', function(e) {
    e.preventDefault();
    if (!$(e.target).prop('in_relation'))
      e.target.classList.add('active');
  })

  // labeling piece of text with a given marker if the marker is clicked
  $('.marker.tags').on('click', function() {
    if (chunks.length > 0 && activeLabels < $('article.markers').attr('data-mmpi')) {
      var chunk = chunks[chunks.length - 1],
          idc = chunks.length - 1
          color = this.getAttribute('data-color'),
          leftTextNode = document.createTextNode(chunk['text'].slice(0, chunk['start'])),
          markedSpan = document.createElement('span'),
          deleteMarkedBtn = document.createElement('button'),
          rightTextNode = document.createTextNode(chunk['text'].slice(chunk['end']));
      markedSpan.className = "tag is-" + color + " is-medium";
      markedSpan.textContent = chunk['text'].slice(chunk['start'], chunk['end']);
      markedSpan.setAttribute('data-s', this.getAttribute('data-s'));
      markedSpan.setAttribute('data-i', labelId);
      $(markedSpan).prop('in_relation', false);
      deleteMarkedBtn.className = 'delete is-small';
      deleteMarkedBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        var el = e.target,
            parent = el.parentNode; // actual span

        chunks = chunks.filter(function(x) { return x.id != chunk.id })
        mergeWithNeighbors(parent);
        $(el).prop('in_relation', false);
        activeLabels--;
        window.chunks = chunks
      }, true);
      markedSpan.appendChild(deleteMarkedBtn)

      markedSpan.addEventListener('click', function(e) {
        if (!$(e.target).prop('in_relation'))
          e.target.classList.add('active');
      })

      if (chunk['node'] !== undefined && chunk['node'] != null) {
        // TODO: figure out when it would happen
        var parent = chunk['node'].parentNode;
        parent.replaceChild(leftTextNode, chunk['node']);
        parent.insertBefore(markedSpan, leftTextNode.nextSibling);
        parent.insertBefore(rightTextNode, markedSpan.nextSibling);
        chunk['marked'] = true;
        chunk['submittable'] = this.getAttribute('data-submittable');
        chunk['id'] = labelId;
        labelId++;
        activeLabels++;
        chunk['label'] = this.querySelector('span.tag:first-child').textContent;
        delete chunk['node']
      }

      window.chunks = chunks;
    }
  });

  // putting the activated labels in a relationship
  $('.relation.tags').on('click', function() {
    var $parts = $('.selector span.tag.active'),
        between = this.getAttribute('data-b').split('-:-'),
        direction = this.getAttribute('data-d'),
        rule = this.getAttribute('data-r');
    if ($parts.length >= 2) {
      var nodes = {},
          links = [];
      var startId = lastNodeInRelationId;
      $parts.each(function(i) {
        $parts[i].id = 'rl_' + lastNodeInRelationId;
        lastNodeInRelationId++;

        $($parts[i]).prop('in_relation', true);

        var s = $parts[i].getAttribute('data-s');

        if (!nodes.hasOwnProperty(s)) {
          nodes[s] = [];
        }
        nodes[s].push({
          'id': $parts[i].id,
          'name': $parts[i].textContent,
          'dom': $parts[i].id,
          'color': getComputedStyle($parts[i])["background-color"]
        });
      });

      var from = null,
          to = null;
      if (direction == '0') {
        // first -> second
        from = between[0];
        to = between[1];
      } else if (direction == '1') {
        // second -> first
        from = between[1];
        to = between[0];
      }

      nodes[from].forEach(function(f) {
        nodes[to].forEach(function(t) {
          links.push({
            'source': f.id,
            'target': t.id
          })
        })
      })

      links.forEach(function(l) {
        var source = document.querySelector('#' + l.source),
            target = document.querySelector('#' + l.target);
        relations.push({
          "id": "n" + startId + "__" + (lastNodeInRelationId - 1),
          'rule': rule,
          's': source.getAttribute('data-i'),
          't': target.getAttribute('data-i')
        })
      });

      if (currentRelationId == null)
        currentRelationId = 0;
      else
        currentRelationId++;

      graphIds.push("n" + startId + "__" + (lastNodeInRelationId - 1));

      drawNetwork({
        'id': "n" + startId + "__" + (lastNodeInRelationId - 1),
        'nodes': Array.prototype.concat.apply([], Object.values(nodes)),
        'links': links
      }, (from != null && to != null))
    }
    $parts.removeClass('active');
  })

  // adding the information about the node, representing a label, to the chunks array
  function updateChunkFromNode(node) {
    var chunk = {},
        marker = document.querySelector('div.marker.tags[data-s="' + node.getAttribute('data-s') + '"]'),
        markerText = marker.querySelector('span.tag:first-child');
    chunk['node'] = null;
    chunk['text'] = node.parentNode != null ? node.parentNode.textContent : node.textContent; // if no parent, assume the whole paragraph was taken?
    chunk['lengthBefore'] = 0;
    chunk['marked'] = true;
    chunk['id'] = labelId;
    chunk['label'] = markerText.textContent;
    chunk['submittable'] = marker.getAttribute('data-submittable') === 'true';
    
    if (contextSize == 'p') {
      // paragraph
      chunk['context'] = chunk['text'];
      chunk['start'] = previousTextLength(node, true);
    } else if (contextSize == 't') {
      // text
      chunk['context'] = resetText;
      chunk['start'] = previousTextLength(node, false);
    } else if (contextSize == 's') {
      // TODO sentence

    } else if (contextSize == 'no') {
      chunk['context'] = null;
      chunk['lengthBefore'] = null;
    } else {
      // not implemented
      console.error("Context size " + contextSize + " is not implemented");
      return;
    }
    chunk['end'] = chunk['start'] + node.textContent.length;
    
    chunks.push(chunk);
  }

  // getting a chunk from the selection; the chunk then either is being added to the chunks array, if the last chunk was submitted
  //                                                    or replaces the last chunk if the last chunk was not submitted
  function updateChunkFromSelection() {
    var selection = window.getSelection(),
        chunk = {};

    if (selection && !selection.isCollapsed) {
      chunk['node'] = selection.anchorNode;
      chunk['text'] = selection.anchorNode.data; // the whole text of the anchor node
      if (selection.anchorOffset > selection.focusOffset) {
        chunk['start'] = selection.focusOffset;
        chunk['end'] = selection.anchorOffset;
      } else {
        chunk['start'] = selection.anchorOffset;
        chunk['end'] = selection.focusOffset;
      }
      if (contextSize == 'p') {
        // paragraph
        chunk['context'] = selection.anchorNode.parentNode.textContent; // the parent of anchor is <p> - just take it's length
        chunk['lengthBefore'] = previousTextLength(selection.anchorNode, true);
      } else if (contextSize == 't') {
        // text
        chunk['context'] = resetText;
        chunk['lengthBefore'] = previousTextLength(selection.anchorNode, false);
      } else if (contextSize == 's') {
        // TODO sentence

      } else if (contextSize == 'no') {
        chunk['context'] = null;
        chunk['lengthBefore'] = null;
      } else {
        // not implemented
        console.error("Context size " + contextSize + " is not implemented");
        return;
      }

      chunk['marked'] = false;
      chunk['label'] = null;

      if (chunks.length == 0 || (chunks.length > 0 && chunks[chunks.length - 1] !== undefined && chunks[chunks.length - 1]['marked'])) {
        chunks.push(chunk);
      } else {
        chunks[chunks.length - 1] = chunk;
      }
    }
  }

  function disableChunk(c) {
    $('span.tag[data-i="' + c['id'] + '"]').addClass('is-disabled');
    c['submittable'] = false;
  }

  function enableChunk(c) {
    $('span.tag[data-i="' + c['id'] + '"]').removeClass('is-disabled');
    c['submittable'] = true;
  }

  // disable given chunks visually
  function disableChunks(chunks) {
    for (var c in chunks) {
      disableChunk(chunks[c])
    }
    return chunks;
  }

  // adding chunk if a piece of text was selected with a mouse
  $('.selector').on('mouseup', function(e) {
    var isRightMB;
    e = e || window.event;

    if ("which" in e)  // Gecko (Firefox), WebKit (Safari/Chrome) & Opera
        isRightMB = e.which == 3; 
    else if ("button" in e)  // IE, Opera 
        isRightMB = e.button == 2;

    if (!$(e.target).hasClass('delete') && !isRightMB) {
      updateChunkFromSelection();
    }
  })

  // adding chunk if a piece of text was selected with a keyboard
  $(document).on("keyup", function(e) {
    var selection = window.getSelection();
    if (selection && (selection.anchorNode != null)) {
      var isArticleParent = selection.anchorNode.parentNode == document.querySelector('.selector');
      if (e.shiftKey && e.which >= 37 && e.which <= 40 && isArticleParent) {
        updateChunkFromSelection();
      } else {
        var $shortcut = $('[data-shortcut="' + String.fromCharCode(e.which) + '"]');
        if ($shortcut.length > 0) {
          $shortcut.click();
        }
      }
    }
  });

  // undo last relation/label if the button is clicked
  $('#undoLast').on('click', function(e) {
    e.preventDefault();
    var $target = $('#undoLast');

    $.ajax({
      method: "POST",
      url: $target.attr('data-url'),
      dataType: "json",
      data: {
        'csrfmiddlewaretoken': $target.closest('form').find('input[name="csrfmiddlewaretoken"]').val()
      },
      success: function(data) {
        chunks.forEach(function(c) {
          if (data['labels'].includes(c.context.slice(c.lengthBefore + c.start, c.lengthBefore + c.end))) {
            var $el = $('span.tag[data-i="' + c.id + '"]');
            $el.removeClass('is-disabled');
            $el.prop('in_relation', false);

            enableChunk(c);
          }
        });

        var $submitted = $('#submittedTotal'),
            $submittedToday = $('#submittedToday');
        
        $submitted.text(data['submitted']);
        $submitted.append($('<span class="smaller">q</span>'));
        
        $submittedToday.text(data['submitted_today']);
        $submittedToday.append($('<span class="smaller">q</span>'));

        $('#inputForm input[type="text"]').val(data['input']);
      },
      error: function() {
        console.log("ERROR!");
      }
    })
  })

  // function that checks if a chunk is in any of the relations
  function isInRelations(c) {
    for (var i = 0, len = relations.length; i < len; i++) {
      if (relations[i].s == c.id || relations[i].t == c.id) return true;
    }
    return false;
  }

  function checkRestrictions() {
    var markers = document.querySelectorAll('.marker.tags[data-res]');
    var messages = [];

    var satisfied = Array.from(markers).map(function(x, i) {
      var res = x.getAttribute('data-res');

      if (res) {
        var have = document.querySelectorAll('.selector span.tag[data-s="' + x.getAttribute('data-s') + '"]').length,
            needed = parseInt(res.slice(2)),
            label = x.querySelector('span.tag').textContent;
        if (res.slice(0, 2) == 'ge') {
          if (have >= needed) {
            return true;
          } else {
            var diff = (needed - have)
            messages.push('You need ' + diff + ' more "' + label + '" ' + 'label' + (diff > 1 ? 's' : ''));
            return false;
          }
        } else if (res.slice(0, 2) == 'gs') {
          if (have > needed) {
            return true;
          } else {
            var diff = (needed - have + 1)
            messages.push('You need ' + diff + ' more "' + label + '" ' + 'label' + (diff > 1 ? 's' : ''));
            return false;
          }
        } else if (res.slice(0, 2) == 'le') {
          if (have <= needed) {
            return true;
          } else {
            messages.push('You can have max ' + needed + ' "' + label + '" ' + 'label' + (needed > 1 ? 's' : ''));
            return false;
          }
        } else if (res.slice(0, 2) == 'ls') {
          if (have < needed) {
            return true;
          } else {
            messages.push('You can have max ' + (needed - 1) + ' "' + label + '" ' + 'label' + ((needed - 1) > 1 ? 's' : ''));
            return false;
          }
        } else
          return true;
      } else {
        return true;
      }
    }, markers);

    var numSatisfied = satisfied.reduce(function(acc, val) { return acc + val; }, 0);

    if (numSatisfied != markers.length) {
      alert(messages.join('\n'));
    }
    return numSatisfied == markers.length
  }

  // submitting the marked labels and/or relations with(out) inputs
  $('#inputForm .submit.button').on('click', function(e) {
    e.preventDefault();

    // check if restrictions are violated
    if (!checkRestrictions()) return;

    var $inputForm = $('#inputForm'),
        $qInput = $inputForm.find('input.question'),
        $questionBlock = $('article.question');

    $qInput.prop("disabled", false);

    var inputFormData = $inputForm.serializeObject(),
        underReview = $questionBlock.prop('review') || false;

    // if there's an input form field, then create input_context
    if (inputFormData.hasOwnProperty('input'))
      inputFormData['input_context'] = selectorArea.textContent;

    inputFormData['relations'] = JSON.stringify(relations);

    // if there are any relations, submit only those chunks that have to do with the relations
    // if there are no relations, submit only submittable chunks, i.e. independent chunks that should not be a part of any relation
    inputFormData['chunks'] = relations.length > 0 ? chunks.filter(isInRelations) : chunks.filter(function(c) { return c.submittable });
    inputFormData['is_review'] = underReview;
    inputFormData['time'] = Math.round(((new Date()).getTime() - qStart.getTime()) / 1000, 1);
    inputFormData['datasource'] = parseInt($('.selector.element').attr('data-s'));

    if (inputFormData['chunks'].length > 0 || relations.length > 0) {
      inputFormData['chunks'] = JSON.stringify(inputFormData['chunks']);
      $.ajax({
        method: "POST",
        url: inputForm.action,
        dataType: "json",
        data: inputFormData,
        success: function(data) {
          if (data['error'] == false) {
            var articleNode = document.querySelector('.selector'),
                $title = $questionBlock.find('.message-header p');

            if (data['next_task'] == 'regular') {
              // no review task
              // resetArticle();
              
              disableChunks(chunks.filter(function(x) { return x.submittable }))

              $questionBlock.removeClass('is-warning');
              $questionBlock.addClass('is-primary');
              $questionBlock.prop('review', false);

              // TODO: get title for a review task from the server
              //       make it a configurable project setting
              $title.html("Your question");

              $qInput.prop("disabled", false);
              $qInput.val('');
              $qInput.focus();
            } else {
              // review task
              removeAllChildren(articleNode);
              articleNode.innerHTML = data['input']['context'];

              $questionBlock.removeClass('is-primary');
              $questionBlock.addClass('is-warning');
              $questionBlock.prop('review', true);

              $title.html("Review question");

              $qInput.val(data['input']['content']);
              $qInput.prop("disabled", true);
            }
          }

          var $submitted = $('#submittedTotal'),
              $submittedToday = $('#submittedToday');
          
          $submitted.text(data['submitted']);
          $submitted.append($('<span class="smaller">q</span>'));
          
          $submittedToday.text(data['submitted_today']);
          $submittedToday.append($('<span class="smaller">q</span>'));
          
          relations = [];
          qStart = new Date();

          // TODO; trigger iff .countdown is present
          $('.countdown').trigger('cdAnimateStop').trigger('cdAnimate');

          // clear svg
          d3.selectAll("svg > *").remove()

          activeLabels = 0;

          $('#undoLast').attr('disabled', false);

          chunks.forEach(function(c) {
            c.submittable = false;
          })

          window.chunks = chunks;
        },
        error: function() {
          console.log("ERROR!");
          if (underReview)
            $qInput.prop("disabled", true)
          else {
            $qInput.val('');
            $qInput.prop('disabled', false);
          }
          $('#undoLast').attr('disabled', true);
          qStart = new Date();
          $('.countdown').trigger('cdAnimateReset').trigger('cdAnimate');
        }
      })
    }
  })

  function getNewText(confirmationCallback, $button) {
    var confirmation = confirmationCallback();
    $button.attr('disabled', true);

    if (confirmation) {
      var el = $('.selector.element');
      el.addClass('is-loading');

      $.ajax({
        type: "POST",
        url: $button.attr('href'),
        dataType: "json",
        data: {
          "csrfmiddlewaretoken": $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(d) {
          $('.selector').html(d.text);
          chunks = [];
          labelId = $('article.text').find('span.tag').length; // count the number of pre-markers
          activeLabels = labelId;
          resetTextHTML = selectorArea.innerHTML;
          resetText = selectorArea.textContent;

          $('#undoLast').attr('disabled', true);

          $('article.text span.tag').on('click', function(e) {
            if (!$(e.target).prop('in_relation'))
              e.target.classList.add('active');
          })

          initPreMarkers();

          el.removeClass('is-loading');
          el.attr('data-s', d.idsource);
          $button.attr('disabled', false);
        },
        error: function() {
          console.log("ERROR!")
          el.removeClass('is-loading');
          $button.attr('disabled', false);
        }
      })
    } else {
      $button.attr('disabled', false);
    }
  }

  // get a new article from the data source(s)
  $('#getNewArticle').on('click', function(e) {
    e.preventDefault();

    var $button = $(this);

    if ($button.attr('disabled')) return;

    getNewText(function() {
      var confirmationText = "All your unsubmitted labels will be removed. Are you sure?";
      return chunks.filter(function(c) { return c.submittable }).length > 0 ? confirm(confirmationText) : true;
    }, $button);
  });

  // get a new article from the data source(s)
  $('#finishRound').on('click', function(e) {
    e.preventDefault();

    var $button = $(this);

    if ($button.attr('disabled')) return;

    getNewText(function() {
      var confirmationText = "Are you sure that you have completed the task to the best of your ability?";
      return confirm(confirmationText);
    }, $button);
  });

  function showRelationGraph(id) {
    var svg = d3.select("#relations svg")

    svg.selectAll('g')
      .attr('class', 'hidden');

    d3.select('g#' + graphIds[id])
      .attr('class', '');

    $('#relationId').text(id + 1);
  }

  $('#prevRelation').on('click', function(e) {
    e.preventDefault();

    if (currentRelationId == null) return;

    currentRelationId--;
    if (currentRelationId < 0) {
      currentRelationId = 0;
      return;
    }

    showRelationGraph(currentRelationId);
  })

  $('#nextRelation').on('click', function(e) {
    e.preventDefault();

    if (currentRelationId == null) return;

    currentRelationId++;
    if (currentRelationId >= graphIds.length) {
      currentRelationId = graphIds.length - 1;
      return;
    }

    showRelationGraph(currentRelationId);
  })


  $('#removeRelation').on('click', function(e) {
    e.preventDefault();

    $('g#' + graphIds[currentRelationId]).find('circle[data-id]').each(function(i, d) { 
      var $el = $('#' + d.getAttribute('data-id'));
      if ($el.length > 0) {
        $el.prop('in_relation', false);
        $el.attr('id', '');
      }
    });
    d3.select('g#' + graphIds[currentRelationId]).remove();
    relations = relations.filter(function(x) {
      return x.id != graphIds[currentRelationId]
    })

    graphIds.splice(currentRelationId, 1);
    currentRelationId = graphIds.length - 1;
    showRelationGraph(currentRelationId);
  })

  /******************/
  /* + Handling SVG */
  /******************/
  
  /* Relations */
  var svg = d3.select("#relations")
    .append("svg")
      .attr("width", "100%")
      .attr("height", "100%");

  // TODO: this marker should be visible w.r.t. the target node
  svg.append("svg:defs").append("svg:marker")
    .attr("id", "triangle")
    .attr("refX", 6)
    .attr("refY", 6)
    .attr("markerWidth", 20)
    .attr("markerHeight", 20)
    .attr("markerUnits","userSpaceOnUse")
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M 0 0 12 6 0 12 3 6")
    .style("fill", "black");

  function drawNetwork(data, arrows) {
    if (arrows === undefined) arrows = false;

    var svg = d3.select("#relations svg")

    svg.selectAll('g')
      .attr('class', 'hidden');

    svg = svg.append("g")
      .attr('id', data.id)

    var link = svg
      .selectAll("line")
      .data(data.links)
      .enter()
      .append("line")
        .style("stroke", "#aaa");

    if (arrows)
      link = link.attr("marker-end", "url(#triangle)");

    // Initialize the nodes
    var node = svg
      .selectAll("circle")
      .data(data.nodes)
      .enter()
      .append("circle")
        .attr("r", radius)
        .attr('data-id', function(d) { return d.id })
        .style("fill", function(d) { return d.color })
        .on("mouseover", function(d, i) {
          $('#' + d.dom).addClass('active');
        })
        .on("mouseout", function(d, i) {
          $('#' + d.dom).removeClass('active');
        })

    var text = svg.selectAll("text")
      .data(data.nodes)
      .enter().append("text")
        .text(function(d) { return d.name; });

    // Let's list the force we wanna apply on the network
    var simulation = d3.forceSimulation(data.nodes)                 // Force algorithm is applied to data.nodes
        .force("link", d3.forceLink()                               // This force provides links between nodes
              .id(function(d) { return d.id; })                     // This provide  the id of a node
              .links(data.links)                                    // and this the list of links
        )
        .force("charge", d3.forceManyBody().strength(-400))         // This adds repulsion between nodes. Play with the -400 for the repulsion strength
        .force("center", d3.forceCenter(radius, 10))                // This force attracts nodes to the center of the svg area
        .stop()

    // This function is run at each iteration of the force algorithm, updating the nodes position.
    function ticked() {
      /* update the simulation */
      text
        .attr("x", function(d) { return d.x + radius * 1.2; })
        .attr("y", function(d) { return d.y; })

      link
        .attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { 
          var dx = 0.7 * Math.abs(d.target.x - d.source.x); 
          if (d.target.x > d.source.x) {
            return d.source.x + dx;
          } else {
            return d.source.x - dx;
          }
        })
        .attr("y2", function(d) {
          var dx = 0.7 * Math.abs(d.target.x - d.source.x);
          var x = null;
          if (d.target.x > d.source.x) {
            x = d.source.x + dx;
          } else {
            x = d.source.x - dx;
          }

          var dy = Math.abs(x - d.source.x) * Math.abs(d.target.y - d.source.y) / Math.abs(d.target.x - d.source.x)

          if (d.target.y > d.source.y) {
            // means arrow down
            return d.source.y + dy;
          } else {
            // means arrow up
            return d.source.y - dy;
          }
        });

      node
       .attr("cx", function(d) { return d.x; })
       .attr("cy", function(d) { return d.y; });
    }

    function finalizeSimulation() {
      var group = d3.select('g#' + data.id);

      if (!group.empty()) {
        var bbox = group.node().getBBox();

        var svgBbox = document.querySelector('svg').getBoundingClientRect();

        var mx = svgBbox.width / 2 - bbox.width / 4;
        var my = svgBbox.height / 2 - bbox.height / 2;

        group.attr("transform", "translate(" + mx + ", " + my + ")");
      }
    }

    for (var i = 0, n = Math.ceil(Math.log(simulation.alphaMin()) / Math.log(1 - simulation.alphaDecay())); i < n; ++i) {
      simulation.tick();
      ticked();
    }
    finalizeSimulation();

    $("#relationId").text(currentRelationId + 1);
  }

  /******************/
  /* - Handling SVG */
  /******************/
});