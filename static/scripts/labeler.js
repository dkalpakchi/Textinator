var labelerModule = (function() {
  var chunks = [], // the array of all chunk of text marked with a label, but not submitted yet
      relations = [], // the array of all relations for this article, not submitted yet
      labelId = 0,
      activeLabels = 0, // a number of labels currently present in the article
      lastRelationId = 1, // the ID of the last unsubmitted relation
      lastNodeInRelationId = 0, // TODO: maybe remove
      radius = 10,
      graphIds = [],
      currentRelationId = null, // the ID of the current relation
      contextSize = undefined, // the size of the context to be saved 'p', 't' or 'no'
      markersArea = null,
      selectorArea = null,   // the area where the article is
      resetTextHTML = null,  // the HTML of the loaded article
      resetText = null,    // the text of the loaded article
      markersInRelations = [],
      nonRelationMarkers = [],
      comments = {};

  function isDefined(x) {
    return x != null && x !== undefined;
  }

  function insertAfter(newNode, existingNode) {
    existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
  }

  function previousTextLength(node, inParagraph) {
    // calculate the length of the text preceding the node
    // inParagraph is a boolean variable indicating whether preceding text
    // is taken only from the current paragraph or from the whole article
    if (inParagraph === undefined) inParagraph = true;

    var len = 0;
    var prev = node.previousSibling;

    // paragraph scope
    while (prev != null) {
      if (prev.nodeType == 1) {
        if (prev.tagName == "BR") {
          // if newline
          len += 1
        } else if ((prev.tagName == "SPAN" && prev.classList.contains("tag")) || prev.tagName == "A") {
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
          len += parentSibling.textContent.length + 1; // +2 because P
        }
        parentSibling = parentSibling.previousElementSibling;
      }
    }
    return len;
  }

  function isDeleteButton(node) {
    return node.nodeName == "BUTTON" && node.classList.contains('delete');
  }

  function mergeWithNeighbors(node) {
    // merge the given node with two siblings - used when deleting a label
    var next = node.nextSibling,
        prev = node.previousSibling,
        parent = node.parentNode;

    var pieces = [],
        element = document.createTextNode("");
    for (var i = 0; i < node.childNodes.length; i++) {
      var child = node.childNodes[i];
      if (child.nodeType == 3) {
        element = document.createTextNode(element.data + child.data);
        if (i == node.childNodes.length - 1)
          pieces.push(element);
      } else {
        pieces.push(element);
        pieces.push(child);
        element = document.createTextNode("");
      }
    }

    if (pieces.length > 1) {
      if (pieces[0].nodeType == 3 && prev.nodeType == 3)
        parent.replaceChild(document.createTextNode(prev.data + pieces[0].data), prev);
      else
        parent.insertBefore(pieces[0], next);

      parent.removeChild(node);
      for (var i = 1; i < pieces.length - 1; i++) {
        parent.insertBefore(pieces[i], next)
      }

      if (pieces[pieces.length-1].nodeType == 3 && next.nodeType == 3) {
        parent.replaceChild(document.createTextNode(pieces[pieces.length-1].data + next.data), next);
      }
      else {
        parent.insertBefore(pieces[pieces.length-1], next);
      }
    } else {
      var next_data = next != null && isDefined(next.data) ? next.data : "";
      if (prev == null) {
        parent.replaceChild(document.createTextNode(pieces[0].data + next_data), node);
      } else {
        var prev_data = isDefined(prev.data) ? prev.data : "";
        parent.replaceChild(document.createTextNode(prev_data + pieces[0].data + next_data), prev);
        parent.removeChild(node);
      }
      if (next != null && !isDeleteButton(next))
        parent.removeChild(next);
    }
  }

  function isFullySelected(node, startOffset, endOffset) {
    if (node.nodeType == 3) {
      if (startOffset === undefined && endOffset === undefined) return false;
      var text = endOffset === undefined ? node.textContent.slice(startOffset) : node.textContent.slice(startOffset, endOffset);
      return node.textContent == text;
    } else {
      return node.parentNode.textContent == node.textContent;
    }
  }

  function getPiece(node, startOffset, endOffset) {
    var fullySelected = isFullySelected(node, startOffset, endOffset);   
    if (node.nodeType == 3 && !fullySelected) {
      if (startOffset === undefined && endOffset === undefined) return node;
      var piece = endOffset === undefined ? node.textContent.slice(startOffset) : node.textContent.slice(startOffset, endOffset);
      return document.createTextNode(piece);
    } else if (node.nodeType != 3 && fullySelected) {
      return node.parentNode;
    } else {
      return node;
    }
  }

  function getPieces(group, isLast) {
    // group is a Range object
    console.log(group)
    var startNode = group.startContainer,
        startOffset = group.startOffset,
        endNode = group.endContainer,
        endOffset = group.endOffset;

    if (startNode == endNode) {
      if (isFullySelected(startNode, startOffset, endOffset)) {
        return [startNode];
      } else {
        return [document.createTextNode(startNode.textContent.slice(startOffset, endOffset))];
      }      
    }

    var pieces = [getPiece(startNode, startOffset, undefined)];
    var sb = pieces[0];

    if (sb.previousSibling == null && sb.nextSibling == null) {
      // probably not part of DOM yet, so a slice
      sb = startNode;
    }

    while (sb != endNode && !sb.contains(endNode)) {
      sb = sb.nextSibling;
      if (sb == null) break;
      pieces.push(sb == endNode ? getPiece(endNode, 0, endOffset) : getPiece(sb, undefined, undefined));
    }
    console.log(pieces);
    return pieces;
  }

  var labeler = {
    allowSelectingLabels: false,
    allowCommentingLabels: false,
    init: function() {
      contextSize = $('#taskArea').data('context');
      markersArea = document.querySelector('.markers');
      selectorArea = document.querySelector('.selector');
      resetTextHTML = selectorArea == null ? "" : selectorArea.innerHTML;
      resetText = selectorArea == null ? "" : selectorArea.textContent.trim();
      this.allowSelectingLabels = markersArea == null ? false : markersArea.getAttribute('data-select') == 'true';
      this.allowCommentingLabels = markersArea == null ? false : markersArea.getAttribute('data-comment') == 'true';
      markersInRelations = markersArea == null ? [] :
        [].concat.apply([], Array.from(markersArea.querySelectorAll('div.relation.tags')).map(
        x => x.getAttribute('data-b').split('-:-')));
      nonRelationMarkers = markersArea == null ? [] :
        Array.from(markersArea.querySelectorAll('div.marker.tags')).map(
        x => x.getAttribute('data-s')).filter(x => !markersInRelations.includes(x));
      this.initSvg();
    },
    disableChunk: function(c) {
      $('span.tag[data-i="' + c['id'] + '"]').addClass('is-disabled');
      c['submittable'] = false;
    },
    enableChunk: function(c) {
      $('span.tag[data-i="' + c['id'] + '"]').removeClass('is-disabled');
      c['submittable'] = true;
    },
    disableChunks: function(chunks) {
      // disable given chunks visually
      for (var c in chunks) {
        disableChunk(chunks[c])
      }
      return chunks;
    },
    getActiveChunk: function() {
      return chunks[chunks.length-1];
    },
    // initialize pre-markers, i.e. mark the specified words with a pre-specified marker
    initPreMarkers: function() {
      this.labelId = 0;
      $('article.text span.tag').each(function(i, node) {
        node.setAttribute('data-i', this.labelId);
        this.updateChunkFromNode(node);

        node.querySelector('button.delete').addEventListener('click', function(e) {
          e.stopPropagation();
          var el = e.target,
              parent = el.parentNode; // actual span

          chunks.splice(this.labelId, 1);
          mergeWithNeighbors(parent);
          $(el).prop('in_relation', false);
          resetTextHTML = selectorArea.innerHTML
          this.activeLabels--;
        })
        this.labelId++;
      })
      this.activeLabels = this.labelId;
    },
    updateChunkFromNode: function(node) {
      // adding the information about the node, representing a label, to the chunks array
      var chunk = {},
          marker = document.querySelector('div.marker.tags[data-s="' + node.getAttribute('data-s') + '"]'),
          markerText = marker.querySelector('span.tag:first-child');
      chunk['node'] = null;
      chunk['text'] = node.parentNode != null ? node.parentNode.textContent : node.textContent; // if no parent, assume the whole paragraph was taken?
      chunk['lengthBefore'] = 0;
      chunk['marked'] = true;
      chunk['id'] = labelId;
      chunk['label'] = node.getAttribute('data-s');
      chunk['submittable'] = marker.getAttribute('data-submittable') === 'true';
      
      if (contextSize == 'p') {
        // paragraph
        chunk['context'] = chunk['text'];
        chunk['start'] = previousTextLength(node, true);
      } else if (contextSize == 't') {
        // text
        chunk['context'] = this.resetText;
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
    },
    updateChunkFromSelection: function() {
      function getDepthAcc(element,depth) {
        if(element.parentNode==null)
          return depth;
        else
          return getDepthAcc(element.parentNode,depth+1);
      }
        
      function getDepth(element) {
        return getDepthAcc(element,0);
      }

      // getting a chunk from the selection; the chunk then either is being added to the chunks array, if the last chunk was submitted
      // or replaces the last chunk if the last chunk was not submitted
      var selection = window.getSelection();

      if (selection && !selection.isCollapsed) {
        // group selections:
        //  - a label spanning other labels is selected, they should end up in the same group
        //  - two disjoint spans of text are selected, they should end up in separate groups
        var groups = [],
            group = [];
        group.push(selection.getRangeAt(0));
        for (var i = 1; i < selection.rangeCount; i++) {
          var last = group[group.length-1],
              cand = selection.getRangeAt(i);
          if (last.endContainer.nextSibling == cand.startContainer) {
            group.push(cand);
          } else {
            groups.push(group);
            group = [cand];
          }
        }
        if (group)
          groups.push(group)

        // FIXME:
        //  - when highlighting nested ltr can't highlight more than 2 nested correctly
        //  - rtl highlighting doesn't work at all

        for (var i = 0; i < groups.length; i++) {
          var chunk = {},
              group = groups[i],
              N = group.length;
              minDepth = Number.MAX_VALUE,
              pieces = [],
              // these two offsets are independent of whether we select ltr or rtl
              groupStart = {
                'whole': isFullySelected(group[0].startContainer, group[0].startOffset, true),
                'node': group[0].startContainer,
                'offset': group[0].startOffset, 
                'depth': getDepth(group[0].startContainer)
              },
              groupEnd = {
                'whole': isFullySelected(group[N-1].endContainer, group[N-1].endOffset, false),
                'node': group[N-1].endContainer,
                'offset': group[N-1].endOffset,
                'depth': getDepth(group[N-1].endContainer)
              };
          for (var j = 0; j < N; j++) {
            var node = group[j].commonAncestorContainer;
            var depth = getDepth(node);
            if (depth < minDepth) {
              chunk['node'] = node;
              minDepth = depth;
            }
            
            pieces.push.apply(pieces, getPieces(group[j], j == N-1));
            console.log("P", pieces);
          }

          // we know that chunk['node'] should give us an enclosing <p>, so force for it
          if (chunk['node'].tagName != "P") {
            var p = chunk['node'].parentNode;
            while (p.tagName != "P" && p.tagName != "BODY") 
              p = p.parentNode;
            if (chunk['node'].textContent != p.textContent)
              chunk['node'] = p;
          }

          chunk['pieces'] = pieces;

          if (groupStart['depth'] != groupEnd['depth']) {
            // if we have nested labels
            if (groupStart['depth'] < groupEnd['depth']) {
              while (groupStart['depth'] != groupEnd['depth']) {
                groupEnd['node'] = groupEnd['node'].parentNode;
                groupEnd['depth']--;
              }
            } else {
              while (groupStart['depth'] != groupEnd['depth']) {
                groupStart['node'] = groupStart['node'].parentNode;
                groupStart['depth']--;
              }
            }
          }

          chunk['left'] = groupStart;
          chunk['right'] = groupEnd;

          if (contextSize == 'p') {
            // paragraph
            chunk['context'] = chunk['node'].textContent; // the parent of anchor is <p> - just take it's length
            chunk['lengthBefore'] = previousTextLength(chunk['node'], true);
          } else if (contextSize == 't') {
            // text
            chunk['context'] = resetText;
            chunk['lengthBefore'] = previousTextLength(chunk['node'], false);
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

          var N = chunks.length;
          if (N == 0 || (N > 0 && chunks[N-1] !== undefined && chunks[N-1]['marked'])) {
            chunks.push(chunk);
          } else {
            chunks[N-1] = chunk;
          }
          console.log(chunk)
        } 
      }
    },
    mark: function(obj, max_markers) {
      if (chunks.length > 0 && activeLabels < max_markers) {
        var chunk = this.getActiveChunk(),
            idc = chunks.length - 1
            color = obj.getAttribute('data-color'),
            leftTextNode = chunk['left']['whole'] ? chunk['left']['node'] :
              document.createTextNode(chunk['left']['node'].textContent.slice(0, chunk['left']['offset'])),
            markedSpan = document.createElement('span'),
            deleteMarkedBtn = document.createElement('button'),
            rightTextNode = chunk['right']['whole'] ? chunk['right']['node'] :
              document.createTextNode(chunk['right']['node'].textContent.slice(chunk['right']['offset']));
        markedSpan.className = "tag is-" + color + " is-medium";
        for (var i = 0; i < chunk['pieces'].length; i++) {
          if (isDefined(chunk['pieces'][i]))
            markedSpan.appendChild(chunk['pieces'][i]);
        }
        markedSpan.setAttribute('data-s', obj.getAttribute('data-s'));
        markedSpan.setAttribute('data-i', labelId);
        markedSpan.setAttribute('data-j', idc);
        $(markedSpan).prop('in_relation', false);
        deleteMarkedBtn.className = 'delete is-small';
        markedSpan.appendChild(deleteMarkedBtn);

        if (this.allowCommentingLabels) {
          var $commentInput = $('<input data-i=' + labelId + ' value = ' + (comments[labelId] || '') + '>');
          $commentInput.on('change', function(e) {
            comments[parseInt(e.target.getAttribute('data-i'))] = $commentInput.val();
          });

          tippy(markedSpan, {
            content: $commentInput[0],
            trigger: 'click',
            interactive: true,
            distance: 0
          });
        }

        if (isDefined(chunk['node'])) {
          // TODO: figure out when it would happen
          var parent = chunk['node'].parentNode;

          if (chunk['node'].nodeType == 3) {
            if (leftTextNode != null) {
              parent.replaceChild(leftTextNode, chunk['node']);
              parent.insertBefore(markedSpan, leftTextNode.nextSibling);
            } else {
              parent.replaceChild(markedSpan, chunk['node']);
            }
            if (rightTextNode != null)
                parent.insertBefore(rightTextNode, markedSpan.nextSibling);
            
          } else {
            var leftParent;
            if (isDefined(leftTextNode)) {
              if (chunk['left']['whole']) {
                leftParent = leftTextNode.parentNode;
                leftParent.replaceChild(markedSpan, leftTextNode);
              } else {
                leftParent = chunk['left']['node'].parentNode;
                leftParent.replaceChild(leftTextNode, chunk['left']['node']);
                leftParent.insertBefore(markedSpan, leftTextNode.nextSibling);
              }
            }
              
            if (isDefined(rightTextNode)) {
              if (chunk['right']['whole']) {
                if (chunk['left']['node'] != chunk['right']['node'])
                  rightTextNode.parentNode.removeChild(rightTextNode);
              } else {
                var rightParent = markedSpan.parentNode;
                rightParent.insertBefore(rightTextNode, markedSpan.nextSibling);
                if (chunk['left']['node'] != chunk['right']['node'])
                  chunk['right']['node'].parentNode.removeChild(chunk['right']['node']);
              }
            }
          }

          var marked = parent.querySelectorAll('span.tag');
          for (var i = 0; i < marked.length; i++) {
            var checker = marked[i],
                elements = [];
            while (checker.classList.contains('tag')) {
              elements.push(checker);
              checker = checker.parentNode;
            }

            for (var j = 0, len = elements.length; j < len; j++) {
              elements[j].style.paddingTop = 10 + 10 * j + "px";
              elements[j].style.paddingBottom = 10 + 10 * j + "px";
            }
          }
          
          chunk['marked'] = true;
          chunk['submittable'] = obj.getAttribute('data-submittable') === 'true';
          chunk['id'] = labelId;
          labelId++;
          activeLabels++;
          chunk['label'] = obj.getAttribute('data-s');
          delete chunk['node']
        }
      }
    },
    checkRestrictions: function(inRelation) {
      if (inRelation === undefined) inRelation = false;

      var markers = document.querySelectorAll('.marker.tags[data-res]');
      var messages = [];

      var satisfied = Array.from(markers).map(function(x, i) {
        var res = x.getAttribute('data-res').split('&');

        for (var i = 0, len = res.length; i < len; i++) {
          if (res[i]) {
            var have = inRelation ? 
              document.querySelectorAll('.selector span.tag[data-s="' + x.getAttribute('data-s') + '"].active:not(.is-disabled)').length :
              document.querySelectorAll('.selector span.tag[data-s="' + x.getAttribute('data-s') + '"]:not(.is-disabled)').length
            var needed = parseInt(res[i].slice(2)),
                restriction = res[i].slice(0, 2),
                label = x.querySelector('span.tag').textContent;
            if (restriction == 'ge') {
              if (have >= needed) {
                return true;
              } else {
                var diff = (needed - have)
                messages.push('You need at least ' + diff + ' more "' + label + '" ' + 'label' + (diff > 1 ? 's' : ''));
                return false;
              }
            } else if (restriction == 'gs') {
              if (have > needed) {
                return true;
              } else {
                var diff = (needed - have + 1)
                messages.push('You need at least ' + diff + ' more "' + label + '" ' + 'label' + (diff > 1 ? 's' : ''));
                return false;
              }
            } else if (restriction == 'le') {
              if (have <= needed) {
                return true;
              } else {
                messages.push('You can have max ' + needed + ' "' + label + '" ' + 'label' + (needed > 1 ? 's' : ''));
                return false;
              }
            } else if (restriction == 'ls') {
              if (have < needed) {
                return true;
              } else {
                messages.push('You can have max ' + (needed - 1) + ' "' + label + '" ' + 'label' + ((needed - 1) > 1 ? 's' : ''));
                return false;
              }
            } else if (restriction == 'eq') {
              if (have == needed) {
                return true;
              } else {
                messages.push('You need to have exactly ' + needed + ' "' + label + '" ' + 'label' + (needed > 1 ? 's' : ''))
                return false;
              }
            } else {
              return true;
            }
          } else {
            return true;
          }
        }
      }, markers);

      var numSatisfied = satisfied.reduce(function(acc, val) { return acc + val; }, 0);

      if (numSatisfied != markers.length) {
        alert(messages.join('\n'));
      }
      return numSatisfied == markers.length
    },
    initSvg: function() {
      if (typeof d3 !== 'undefined') {
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
      }
    },
    drawNetwork: function(data, arrows) {
      if (typeof d3 !== 'undefined') {
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
            .text(function(d) { return d.name.length > 10 ? d.name.substr(0, 10) + '...' : d.name ; });

        // Let's list the force we wanna apply on the network
        var simulation = d3.forceSimulation(data.nodes)                 // Force algorithm is applied to data.nodes
            .force("link", d3.forceLink()                               // This force provides links between nodes
                  .id(function(d) { return d.id; })                     // This provide  the id of a node
                  .links(data.links)                                    // and this the list of links
            )
            .force("charge", d3.forceManyBody().strength(-500))         // This adds repulsion between nodes. Play with the -400 for the repulsion strength
            .force("center", d3.forceCenter(radius, 30))                // This force attracts nodes to the center of the svg area
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
    },
    previousRelation: function() {
      if (currentRelationId == null) return currentRelationId;

      currentRelationId--;
      if (currentRelationId < 0) {
        currentRelationId = 0;
      }
      return currentRelationId;
    },
    nextRelation: function() {
      if (currentRelationId == null) return currentRelationId;

      currentRelationId++;
      if (currentRelationId >= graphIds.length) {
        currentRelationId = graphIds.length - 1;
      }
      return currentRelationId;
    },
    removeCurrentRelation: function() {
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
      return currentRelationId;
    },
    showRelationGraph(id) {
      if (id == null || id === undefined)
        $('#relationId').text(0);
      else {
        var svg = d3.select("#relations svg")

        svg.selectAll('g')
          .attr('class', 'hidden');

        d3.select('g#' + graphIds[id])
          .attr('class', '');

        $('#relationId').text(id + 1);
      }
    },
    markRelation: function(obj) {
      if (!this.checkRestrictions(true)) return;

      var $parts = $('.selector span.tag.active'),
          between = obj.getAttribute('data-b').split('-:-'),
          direction = obj.getAttribute('data-d'),
          rule = obj.getAttribute('data-r');

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
        if (direction == '0' || direction == '2') {
          // first -> second or bidirectional
          from = between[0];
          to = between[1];
        } else if (direction == '1') {
          // second -> first
          from = between[1];
          to = between[0];
        }

        nodes[from].forEach(function(f) {
          nodes[to].forEach(function(t) {
            if (f.id != t.id) {
              // prevent loops
              links.push({
                'source': f.id,
                'target': t.id
              })
            }
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

        this.drawNetwork({
          'id': "n" + startId + "__" + (lastNodeInRelationId - 1),
          'nodes': Array.prototype.concat.apply([], Object.values(nodes)),
          'links': links
        }, (from != null && to != null && direction != '2'))

        $parts.removeClass('active');
        $parts.append($('<span class="rel">' + lastRelationId + '</span>'));
        lastRelationId++;
      }
    },
    labelDeleteHandler: function(e) {
      // when a delete button on any label is clicked
      e.stopPropagation();
      var target = e.target,
          parent = target.parentNode, // actual span
          sibling = target.nextSibling; // the span with a relation number (if any)

      target.remove();
      if (sibling != null)
        sibling.remove();
      chunks = chunks.filter(function(x) { return x.id != target.getAttribute('data-j') })
      mergeWithNeighbors(parent);
      // $(target).prop('in_relation', false);
      activeLabels--;
    }
  }

  return labeler;
})();


$(document).ready(function() {
  labelerModule.init();

  var qStart = new Date();  // the time the page was loaded or the last submission was made                          
      
  // Guidelines "Show more" button
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

  // do initialize pre-markers for the current article
  labelerModule.initPreMarkers();

  // disable the undo button, since we haven't submitted anything
  $('#undoLast').attr('disabled', true);  

  function removeAllChildren(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function resetArticle() {
    var node = document.querySelector('.selector');
    removeAllChildren(node);
    node.innerHTML = labelerModule.resetTextHTML;
  }

  // event delegation
  $('.selector.element').on('click', function(e) {
    var target = e.target;
    if (target.nodeName == "BUTTON" && target.classList.contains('delete')) {
      labelerModule.labelDeleteHandler(e);
    } else if (target.nodeName == "SPAN" && target.classList.contains('tag')) {
      if (labelerModule.allowSelectingLabels) {
        var $target = $(e.target);
        if (!$target.prop('in_relation') && !window.getSelection().toString()) {
          if (e.target.classList.contains('active') && $target.prop('selected')) {
            e.target.classList.remove('active');
            $target.prop('selected', false);
          } else {
            e.target.classList.add('active');
            $target.prop('selected', true);
          }
        }
      }
    }
  });

  $('.selector.element').on('mouseover', function(e) {
    var target = e.target;
    if (target.nodeName == "SPAN" && target.classList.contains('tag')) {
      if (labelerModule.allowSelectingLabels) {
        e.stopPropagation();
        if (e.target.classList.contains("tag"))
          if (!$(e.target).prop('selected'))
            e.target.classList.add('active');
        else
          if (!$(e.target.parentNode).prop('selected'))
            e.target.parentNode.classList.add('active');
      }
    }
  });

  $('.selector.element').on('mouseout', function(e) {
    var target = e.target;
    if (target.nodeName == "SPAN" && target.classList.contains('tag')) {
      if (labelerModule.allowSelectingLabels) {
        e.stopPropagation();
        if (e.target.classList.contains("tag"))
          if (!$(e.target).prop('selected'))
            e.target.classList.remove('active');
        else
          if (!$(e.target.parentNode).prop('selected'))
            e.target.parentNode.classList.remove('active');
      }
    }
  })

  // labeling piece of text with a given marker if the marker is clicked
  $('.marker.tags').on('click', function(e) {
    var mmpi = $('article.markers').attr('data-mmpi');
    labelerModule.mark(this, mmpi);
  });


  // check marker restrictions

  // putting the activated labels in a relationship
  $('.relation.tags').on('click', function(e) {
    labelerModule.markRelation(this);
  })

  // adding chunk if a piece of text was selected with a mouse
  $('.selector').on('mouseup', function(e) {
    var isRightMB;
    e = e || window.event;

    if ("which" in e)  // Gecko (Firefox), WebKit (Safari/Chrome) & Opera
        isRightMB = e.which == 3; 
    else if ("button" in e)  // IE, Opera 
        isRightMB = e.button == 2;

    if (!$(e.target).hasClass('delete') && !isRightMB) {
      labelerModule.updateChunkFromSelection();
    }
  })

  // adding chunk if a piece of text was selected with a keyboard
  $(document).on("keyup", function(e) {
    var selection = window.getSelection();
    if (selection && (selection.anchorNode != null)) {
      var isArticleParent = selection.anchorNode.parentNode == document.querySelector('.selector');
      if (e.shiftKey && e.which >= 37 && e.which <= 40 && isArticleParent) {
        labelerModule.updateChunkFromSelection();
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

  // submitting the marked labels and/or relations with(out) inputs
  $('#inputForm .submit.button').on('click', function(e) {
    e.preventDefault();

    // check if restrictions are violated
    if (!checkRestrictions()) return;

    var $inputForm = $('#inputForm'),
        $qInput = $inputForm.find('input.question'),
        $questionBlock = $('article.question');

    if ($qInput.length > 0 && $qInput.val().trim() == 0) {
      alert("Please write a question first.");
      return;
    }

    $qInput.prop("disabled", false);

    var inputFormData = $inputForm.serializeObject(),
        underReview = $questionBlock.prop('review') || false;

    // if there's an input form field, then create input_context
    if (inputFormData.hasOwnProperty('input'))
      inputFormData['input_context'] = selectorArea.textContent;

    inputFormData['relations'] = JSON.stringify(relations);

    var $selector = $('.selector.element');

    // if there are any relations, submit only those chunks that have to do with the relations
    // if there are no relations, submit only submittable chunks, i.e. independent chunks that should not be a part of any relation
    if (relations.length > 0) {
      inputFormData['chunks'] = chunks.filter(isInRelations)
      
      var nonRelationChunks = chunks.filter(x => !inputFormData['chunks'].includes(x));
      for (var i = 0, len = nonRelationChunks.length; i < len; i++) {
        if (nonRelationMarkers.includes(nonRelationChunks[i]['label'])) {
          inputFormData['chunks'].push(nonRelationChunks[i]);
        }
      }
    } else {
      inputFormData['chunks'] = chunks.filter(function(c) { return c.submittable })
    }

    for (var i=0, len=inputFormData['chunks'].length; i < len; i++) {
      inputFormData['chunks'][i]['comment'] = comments[inputFormData['chunks'][i]['id']] || '';
    }

    inputFormData['is_review'] = underReview;
    inputFormData['time'] = Math.round(((new Date()).getTime() - qStart.getTime()) / 1000, 1);
    inputFormData['datasource'] = parseInt($selector.attr('data-s'));
    inputFormData['datapoint'] = parseInt($selector.attr('data-dp'));

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
              
              disableChunks(JSON.parse(inputFormData['chunks']));

              $questionBlock.removeClass('is-warning');
              $questionBlock.addClass('is-primary');
              $questionBlock.prop('review', false);

              // TODO: get title for a review task from the server
              //       make it a configurable project setting
              $title.html("Your question");

              if ($qInput.length > 0) {
                $qInput.prop("disabled", false);
                $qInput.val('');
                $qInput.focus();  
              }
            } else {
              // review task
              removeAllChildren(articleNode);
              articleNode.innerHTML = data['input']['context'];

              $questionBlock.removeClass('is-primary');
              $questionBlock.addClass('is-warning');
              $questionBlock.prop('review', true);

              $title.html("Review question");

              if ($qInput.length > 0) {
                $qInput.val(data['input']['content']);
                $qInput.prop("disabled", true);
              }
            }
          }

          var $submitted = $('#submittedTotal'),
              $submittedToday = $('#submittedToday');
          
          $submitted.text(data['submitted']);
          $submitted.append($('<span class="smaller">q</span>'));
          
          $submittedToday.text(data['submitted_today']);
          $submittedToday.append($('<span class="smaller">q</span>'));
          
          qStart = new Date();

          // TODO; trigger iff .countdown is present
          $('.countdown').trigger('cdAnimateStop').trigger('cdAnimate');

          // fix relations
          relations = [];
          currentRelationId = null;
          lastRelationId = 1;
          graphIds = [];
          // clear svg
          d3.selectAll("svg > *").remove()
          showRelationGraph(currentRelationId);

          activeLabels = 0;

          $('#undoLast').attr('disabled', false);

          chunks.forEach(function(c) {
            c.submittable = false;
          })
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
          var $selector = $('.selector');
          // update text, source id and datapoint id
          el.attr('data-s', d.source_id);
          el.attr('data-dp', d.dp_id);

          if (d.source_id == -1) {
            var $text = $selector.closest('article.text');
            if ($text) {
              $text.removeClass('text');
            }

            // TODO: great_job image path should be dynamic
            $selector.html('\
              <div class="hero is-large">\
                <div class="hero-body">\
                  <div class="container">\
                    <div class="columns is-vcentered">\
                      <div class="column is-2">\
                        <figure class="image is-128x128">\
                          <img src="/textinator/static/images/great_job.png" alt="">\
                        </figure>\
                      </div>\
                      <div class="column">\
                        <h1 class="title">\
                          You have finished this challenge!\
                          <p class="subtitle">Thank you for the participation! Your contribution to the research is invaluable!</p>\
                        </h1>\
                      </div>\
                    </div>\
                  </div>\
                </div>\
              </div>')
            $text.siblings('article').remove()
          } else {
            $selector.html(d.text);

            chunks = [];
            labelId = $('article.text').find('span.tag').length; // count the number of pre-markers
            activeLabels = labelId;
            resetTextHTML = selectorArea.innerHTML;
            resetText = selectorArea.textContent;

            $('#undoLast').attr('disabled', true);

            if (labelerModule.allowCommentingLabels) {
              var $commentInput = $('<input data-i=' + labelId + ' value = ' + (comments[labelId] || '') + '>');
              $commentInput.on('change', function(e) {
                comments[parseInt(e.target.getAttribute('data-i'))] = $commentInput.val();
              });

              tippy('span.tag', {
                content: $commentInput[0],
                trigger: 'click',
                interactive: true,
                distance: 0
              });

              comments = {};
            }

            initPreMarkers();

            $button.attr('disabled', false);
          }
          el.removeClass('is-loading');
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

  $('#prevRelation').on('click', function(e) {
    e.preventDefault();
    labelerModule.showRelationGraph(labelerModule.previousRelation());
  })

  $('#nextRelation').on('click', function(e) {
    e.preventDefault();
    labelerModule.showRelationGraph(labelerModule.nextRelation());
  })


  $('#removeRelation').on('click', function(e) {
    e.preventDefault();
    labelerModule.showRelationGraph(labelerModule.removeCurrentRelation());
  })

  /**
   * Modals handling
   */

  $('#flagTextButton').on('click', function() {
    $('.flag.modal').addClass('is-active');
  })

  $('#flagTextForm').on('submit', function(e) {
    e.preventDefault();
    var $form = $("#flagTextForm");

    $.ajax({
      type: $form.attr('method'),
      url: $form.attr('action'),
      dataType: "json",
      data: {
        "csrfmiddlewaretoken": $('input[name="csrfmiddlewaretoken"]').val(),
        "feedback": $form.find('textarea[name="feedback"]').val(),
        "ds_id": selectorArea.getAttribute('data-s'),
        "dp_id": selectorArea.getAttribute('data-dp')
      },
      success: function(d) {
        alert("Thank you for your feedback!");
        $('.flag.modal').removeClass('is-active');
        getNewText(function() { return true; }, $('#getNewArticle'));
      },
      error: function() {
        alert("Your feedback was not recorded. Please try again later.");
      }
    })
  })

  $('#guidelinesButton').on('click', function() {
    $('.guidelines.modal').addClass('is-active');
  });

  $('.modal-close').on('click', function() {
    $('.modal').removeClass('is-active');
    $('.countdown svg circle:last-child').trigger('cdAnimate');
  });

  $('.modal-background').on('click', function() {
    $('.modal').removeClass('is-active');
    $('.countdown svg circle:last-child').trigger('cdAnimate');
  });

  $('#guidelinesButton').click();

  /**
   * - Modals handling
   */
});
