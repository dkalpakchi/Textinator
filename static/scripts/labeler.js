$(document).ready(function() {
  var chunks = [],
      lastRelationY = 0,
      lastRelationId = 0,
      selectorArea = document.querySelector('.selector'),
      resetTextHTML = selectorArea.innerHTML,
      resetText = selectorArea.innerHTML.replace(/<br>/gi, '\n'),
      contextSize = $('#taskArea').data('context'),
      qStart = new Date();

  function previousTextLength(node) {
    var len = 0;
    var prev = node.previousSibling;
    while (prev != null) {
      if (prev.nodeType == 1) {
        if (prev.tagName == "BR") {
          // if newline
          len += 1
        } else if (prev.tagName == "SPAN" && prev.classList.contains("tag")) {
          // if there is a label
          len += prev.innerText.length
        }
      } else if (prev.nodeType == 3) {
        len += prev.length
      }
      prev = prev.previousSibling
    }
    return len;
  }

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

  $('.marker.tags').on('click', function() {
    if (chunks.length > 0) {
      var chunk = chunks[chunks.length - 1],
          idc = chunks.length - 1
          color = this.getAttribute('data-color'),
          leftTextNode = document.createTextNode(chunk['text'].slice(0, chunk['start'])),
          markedSpan = document.createElement('span'),
          deleteMarkedBtn = document.createElement('button'),
          rightTextNode = document.createTextNode(chunk['text'].slice(chunk['end'])),
          parent = chunk['node'].parentNode;
      markedSpan.className = "tag is-" + color + " is-medium";
      markedSpan.textContent = chunk['text'].slice(chunk['start'], chunk['end']);
      markedSpan.setAttribute('data-s', this.getAttribute('data-s'));
      $(markedSpan).prop('in_relation', false);
      deleteMarkedBtn.className = 'delete is-small';
      deleteMarkedBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        var el = e.target,
            parent = el.parentNode; // actual span

        chunks.splice(idc, 1);
        mergeWithNeighbors(parent);
        $(el).prop('in_relation', false);
      }, true);
      markedSpan.appendChild(deleteMarkedBtn)

      markedSpan.addEventListener('click', function(e) {
        if (!$(e.target).prop('in_relation'))
          e.target.classList.add('active');
      })

      parent.replaceChild(leftTextNode, chunk['node']);
      parent.insertBefore(markedSpan, leftTextNode.nextSibling);
      parent.insertBefore(rightTextNode, markedSpan.nextSibling);
      chunk['marked'] = true;
      chunk['label'] = this.querySelector('span.tag:first-child').textContent;
      delete chunk['node']
      window.chunks = chunks;
    }
  });

  $('.relation.tags').on('click', function() {
    var $parts = $('.selector span.tag.active'),
        between = this.getAttribute('data-b').split('-:-'),
        direction = this.getAttribute('data-d');
    if ($parts.length >= 2) {
      var nodes = {},
          links = [];
      var startId = lastRelationId;
      $parts.each(function(i) {
        $parts[i].id = 'rl_' + lastRelationId;
        lastRelationId++;

        $($parts[i]).prop('in_relation', true);

        var s = $parts[i].getAttribute('data-s');
        console.log(s)

        if (!nodes.hasOwnProperty(s)) {
          nodes[s] = [];
        }
        nodes[s].push({
          'id': $parts[i].id,
          'name': $parts[i].innerText,
          'dom': $parts[i].id
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

      drawNetwork({
        'id': "n" + startId + "__" + (lastRelationId - 1),
        'nodes': Array.prototype.concat.apply([], Object.values(nodes)),
        'links': links
      }, (from != null && to != null))
    }
    $parts.removeClass('active');
  })

  function updateChunk() {
    var selection = window.getSelection(),
        chunk = {};

    if (selection) {
      chunk['node'] = selection.anchorNode;
      chunk['text'] = selection.anchorNode.data;
      if (selection.anchorOffset > selection.focusOffset) {
        chunk['start'] = selection.focusOffset;
        chunk['end'] = selection.anchorOffset;
      } else {
        chunk['start'] = selection.anchorOffset;
        chunk['end'] = selection.focusOffset;
      }
      if (contextSize == 'p') {
        // paragraph
        chunk['context'] = chunk['text']
        chunk['lengthBefore'] = 0;
      } else if (contextSize == 't') {
        // text
        chunk['context'] = resetText;
        chunk['lengthBefore'] = previousTextLength(selection.anchorNode);
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

  $('.selector').on('mouseup', function(e) {
    var isRightMB;
    e = e || window.event;

    if ("which" in e)  // Gecko (Firefox), WebKit (Safari/Chrome) & Opera
        isRightMB = e.which == 3; 
    else if ("button" in e)  // IE, Opera 
        isRightMB = e.button == 2;

    if (!$(e.target).hasClass('delete') && !isRightMB) {
      updateChunk();
    }
  })

  $(document).on("keyup", function(e) {
    var selection = window.getSelection();
    if (selection && (selection.anchorNode != null)) {
      var isArticleParent = selection.anchorNode.parentNode == document.querySelector('.selector');
      if (e.shiftKey && e.which >= 37 && e.which <= 40 && isArticleParent) {
        updateChunk();
      } else {
        var $shortcut = $('[data-shortcut="' + String.fromCharCode(e.which) + '"]');
        if ($shortcut.length > 0) {
          $shortcut.click();
        }
      }
    }
  });

  $('#inputForm .submit.button').on('click', function(e) {
    e.preventDefault();

    var $inputForm = $('#inputForm'),
        $qInput = $inputForm.find('input.question'),
        $questionBlock = $('article.question');

    $qInput.prop("disabled", false);

    var inputFormData = $inputForm.serializeObject(),
        underReview = $questionBlock.prop('review') || false;
    inputFormData['chunks'] = JSON.stringify(chunks);
    inputFormData['is_review'] = underReview;
    inputFormData['time'] = Math.round(((new Date()).getTime() - qStart.getTime()) / 1000, 1);

    $.ajax({
      method: "POST",
      url: inputForm.action,
      dataType: "json",
      data: inputFormData,
      success: function(data) {
        if (data['error'] == false) {
          var articleNode = document.querySelector('.selector'),
              $title = $questionBlock.find('.message-header p');
          if (data['input'] == null) {
            // no review task
            resetArticle();
            $questionBlock.removeClass('is-warning');
            $questionBlock.addClass('is-primary');
            $questionBlock.prop('review', false);

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
          if ('aat' in data)
            $('#aat').html(data['aat'] + "s");
        }
        var $inpSmaller = (data['inp_points'] >= 1000) ? $('<span class="smaller">kp</span>') : $('<span class="smaller">p</span>'),
            $inpPts = $('#inputPoints'),
            $peerSmaller = (data['peer_points'] >= 1000) ? $('<span class="smaller">kp</span>') : $('<span class="smaller">p</span>'),
            $peerPts = $('#peerPoints');
        
        $inpPts.text(data['inp_points']);
        $inpPts.append($inpSmaller);
        
        $peerPts.text(data['peer_points']);
        $peerPts.append($peerSmaller);
        
        chunks = [];
        qStart = new Date();
        $('.countdown').trigger('cdAnimateStop').trigger('cdAnimate');
      },
      error: function() {
        console.log("ERROR!")
        if (underReview)
          $qInput.prop("disabled", true)
        else {
          $qInput.val('');
          $qInput.prop('disabled', false);
        }
        qStart = new Date();
        $('.countdown').trigger('cdAnimateReset').trigger('cdAnimate');
      }
    })

    resetArticle();
  })

  $('#getNewArticle').on('click', function(e) {
    e.preventDefault();

    var confirmation = chunks.length > 0 ? confirm("All your unsubmitted labels will be removed. Are you sure?") : true;

    if (confirmation) {
      var el = $('.selector.element');
      el.addClass('is-loading');

      $.ajax({
        type: "POST",
        url: $(this).attr('href'),
        dataType: "json",
        data: {
          "csrfmiddlewaretoken": $('input[name="csrfmiddlewaretoken"]').val()
        },
        success: function(d) {
          $('.selector').html(d.text);
          chunks = [];
          resetTextHTML = selectorArea.innerHTML;
          resetText = selectorArea.innerHTML.replace(/<br>/gi, '\n');
          el.removeClass('is-loading');hon
        },
        error: function() {
          console.log("ERROR!")
          el.removeClass('is-loading');
        }
      })
    }
  });

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

  var initialMarginX = 50,
      initialMarginY = 50,
      graphId = 0,
      radius = 10;

  function drawNetwork(data, arrows) {
    if (arrows === undefined) arrows = false;

    // Initialize the links
    var deltaY = initialMarginY;
        deltaX = initialMarginX;

    var svg = d3.select("#relations svg")

    svg = svg.append("g")
      .attr('id', data.id)
      .attr("transform", "translate(" + deltaX + ", " + deltaY + ")")

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
        .style("fill", "#69b3a2")
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
        .force("center", d3.forceCenter(radius, 10));                   // This force attracts nodes to the center of the svg area

    simulation.on("tick", ticked);

    // This function is run at each iteration of the force algorithm, updating the nodes position.
    function ticked() {
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

    function onCloseClick(d) {
      $(this.parentNode).find('circle[data-id]').each(function(i, d) { 
        var $el = $('#' + d.getAttribute('data-id'));
        if ($el.length > 0) {
          $el.prop('in_relation', false);
          $el.attr('id', '');
        }
      });
      d3.select(this.parentNode).remove();
    }

    simulation.on('end', function() {
      var group = d3.select('g#' + data.id);

      if (!group.empty()) {
        var bbox = group.node().getBBox();

        svg.append("circle")
          .attr('cx', bbox['x'] + bbox['width'] + 25)
          .attr('cy', bbox['y'] + 15)
          .attr("r", 10)
          .attr("stroke", "black")
          .attr('stroke-width', '2px')
          .attr('fill-opacity', 0)
          .on('click', onCloseClick)

        svg.append('line')
          .attr('x1', bbox['x'] + bbox['width'] + 20)
          .attr('y1', bbox['y'] + 10)
          .attr('x2', bbox['x'] + bbox['width'] + 30)
          .attr('y2', bbox['y'] + 20)
          .attr('stroke-width', '2px')
          .style("stroke", "black")
          .on('click', onCloseClick)

        svg.append('line')
          .attr('x1', bbox['x'] + bbox['width'] + 30)
          .attr('y1', bbox['y'] + 10)
          .attr('x2', bbox['x'] + bbox['width'] + 20)
          .attr('y2', bbox['y'] + 20)
          .attr('stroke-width', '2px')
          .style("stroke", "black")
          .on('click', onCloseClick)
      }

      lastRelationY = Math.max.apply(null, data.nodes.map(function(d) { return d.y })) + 30;
    });
  }
});