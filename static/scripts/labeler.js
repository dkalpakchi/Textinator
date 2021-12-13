;(function() {
  var utils = {
    isDefined: function(x) {
      return x != null && x !== undefined;
    }
  };


  var labelerModule = (function() {
    const RELATION_CHANGE_EVENT = 'labeler_relationschange';
    const LINE_ENDING_TAGS = ["P", "UL", "BLOCKQUOTE", "H1", "H2", "H3", "H4", "H5", "H6"];

    var chunks = [], // the array of all chunk of text marked with a label, but not submitted yet
        relations = {}, // a map from relationId to the list of relations constituting it
        labelId = 0,
        activeLabels = 0, // a number of labels currently present in the article
        currentRelationId = null, // the ID of the current relation (for a visual pane)
        lastRelationId = 1, // the ID of the last unsubmitted relation
        lastNodeInRelationId = 0, // TODO: maybe remove
        contextSize = undefined, // the size of the context to be saved 'p', 't' or 'no'
        resetTextHTML = null,  // the HTML of the loaded article
        resetText = null,    // the text of the loaded article
        pluginsToRegister = 0,
        markersInRelations = [],
        nonRelationMarkers = [],
        submittableChunks = []; // chunks to be submitted

    function containsIdentical(arr, obj) {
      for (var i in arr) {
        var found = true;
        for (var k in obj) {
          found = found && arr[i].hasOwnProperty(k) && (obj[k] == arr[i][k]);
          if (!found)
            break;
        }
        if (found)
          return true;
      }
      return false;
    }

    function clearSelection() {
      if (window.getSelection) {
        if (window.getSelection().empty) {  // Chrome
          window.getSelection().empty();
        } else if (window.getSelection().removeAllRanges) {  // Firefox
          window.getSelection().removeAllRanges();
        }
      } else if (document.selection) {  // IE?
        document.selection.empty();
      }
    }

    function getSelectionLength(range) {
      return range.toString().length;
    }

    function insertAfter(newNode, existingNode) {
      existingNode.parentNode.insertBefore(newNode, existingNode.nextSibling);
    }

    function previousTextLength(node, inParagraph) {
      function removeRelationIds(prev) {
        var markers = prev.querySelectorAll('span[data-m]');
        var textContent = [];
        for (var i = 0, len = markers.length; i < len; i++) {
          textContent.push(markers[i].textContent);
          markers[i].textContent = "";
        }
        return {
          'markers': markers,
          'textContent': textContent
        }
      }

      function addRelationIds(obj) {
        for (var i = 0, len = obj.markers.length; i < len; i++) {
          obj.markers[i].textContent = obj.textContent[i];
        }
      }

      function getPrevLength(prev, onlyElements) {
        if (onlyElements === undefined) onlyElements = false;
        var len = 0;
        while (prev != null) {
          if (prev.nodeType == 1) {
            if (prev.tagName == "BR") {
              // if newline
              len += 1
            } else if ((prev.tagName == "SPAN" && prev.classList.contains("tag")) || LINE_ENDING_TAGS.includes(prev.tagName)) {
              // if there is a label, need to remove the possible relation label before calculating textContent
              var res = removeRelationIds(prev);
              len += prev.textContent.length;
              if (LINE_ENDING_TAGS.includes(prev.tagName))
                len += 1; // +1 because P is replaced by '\n'
              addRelationIds(res);
            } else {
              len += prev.textContent.length;
            }
          } else if (prev.nodeType == 3) {
            len += prev.length
          }
          prev = onlyElements ? prev.previousElementSibling : prev.previousSibling
        }
        return len;
      }

      // calculate the length of the text preceding the node
      // inParagraph is a boolean variable indicating whether preceding text
      // is taken only from the current paragraph or from the whole article
      if (inParagraph === undefined) inParagraph = true;

      var textLength = getPrevLength(node.previousSibling);
      var enclosingLabel = getEnclosingLabel(node);
      if (enclosingLabel != null && enclosingLabel != node)
        textLength += getPrevLength(enclosingLabel.previousSibling);

      // account for nesting
      while (isLabel(node.parentNode) && node.parentNode != enclosingLabel) {
        node = node.parentNode;
        textLength += getPrevLength(node.previousSibling);
      }

      // Find previous <p> or <ul>
      var parent = getEnclosingParagraph(node);

      if (parent != null && parent.tagName == "UL")
        textLength += 1 // because <ul> adds a newline character to the beginning of the string

      if (inParagraph) return textLength;

      // all text scope
      if (parent != null) {
        textLength += getPrevLength(parent.previousElementSibling, true);

        if (parent.parentNode.tagName == "BLOCKQUOTE") {
          // +1 because <blockquote> adds a newline char to the beginning of the string
          textLength += getPrevLength(parent.parentNode.previousElementSibling, true) + 1;
        }
      }
      return textLength;
    }

    function isDeleteButton(node) {
      return utils.isDefined(node) && node.nodeName == "BUTTON" && node.classList.contains('delete');
    }

    function isLabel(node) {
      return utils.isDefined(node) && node.nodeName == "SPAN" && node.classList.contains("tag");
    }

    function isMarker(node) {
      return utils.isDefined(node) && node.nodeName == "DIV" && node.hasAttribute('data-s') && node.hasAttribute('data-color') &&
        node.hasAttribute('data-res') && node.hasAttribute('data-shortcut') && node.hasAttribute('data-submittable');
    }

    function isRelation(node) {
      return utils.isDefined(node) && node.nodeName == "DIV" && node.hasAttribute('data-b') && node.hasAttribute('data-d') &&
        node.hasAttribute('data-r') && node.hasAttribute('data-shortcut');
    }

    function isRelationIdentifier(node) {
      if (node.nodeType == 3) {
        node = node.parentNode;
      }
      return utils.isDefined(node) && node.nodeName == "SPAN" && node.hasAttribute('data-m') && node.getAttribute('data-m') == 'r';
    }

    function getEnclosingLabel(node) {
      while (isLabel(node.parentNode)) {
        if (!utils.isDefined(node)) break;
        node = node.parentNode;
      }
      return isLabel(node) ? node : null;
    }

    function getClosestMarker(node) {
      while (!isMarker(node)) {
        if (!utils.isDefined(node)) break;
        node = node.parentNode;
      }
      return isMarker(node) ? node : null;
    }

    function getClosestRelation(node) {
      while (!isRelation(node)) {
        if (!utils.isDefined(node)) break;
        node = node.parentNode;
      }
      return isRelation(node) ? node : null;
    }

    function getEnclosingParagraph(node) {
      while (!["UL", "BODY", "P"].includes(node.tagName))
        node = node.parentNode;
      return (["P", "UL"].includes(node.tagName)) ? node : null;
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
        var next_data = next != null && utils.isDefined(next.data) ? next.data : "";
        if (prev == null) {
          parent.replaceChild(document.createTextNode(pieces[0].data + next_data), node);
        } else {
          var prev_data = utils.isDefined(prev.data) ? prev.data : "";
          parent.replaceChild(document.createTextNode(prev_data + pieces[0].data + next_data), prev);
          parent.removeChild(node);
        }
        if (next != null && !isDeleteButton(next))
          parent.removeChild(next);
      }
    }

    /*
     * From MDN (https://developer.mozilla.org/en-US/docs/Web/API/Range/startOffset)
     * If the startContainer is a Node of type Text, Comment, or CDATASection,
     * then the offset is the number of characters from the start of the startContainer
     * to the boundary point of the Range. For other Node types, the startOffset is
     * the number of child nodes between the start of the startContainer and the boundary point of the Range
     * 
     * The same is true for endContainer and endOffset
     */
    function getSelectionFromRange(range, config) {
      if (range.startContainer == range.endContainer) {
        var node = range.startContainer
        if (node.nodeType == 3) { // Text
          return node.textContent.slice(range.startOffset, range.endOffset);
        } else {
          return node.textContent;
        }
      } else {
        var start = range.startContainer,
            end = range.endContainer,
            startText = "",
            endText = "";

        if (start.nodeType == 3) {
          startText += start.textContent.slice(range.startOffset);
        } else {
          for (var i = 0; i < range.startOffset; i++) {
            var n = start.childNodes[i];
            if (n != end) {
              startText += n.textContent;
            }
          }
        }
        if (config.startOnly) return startText;

        if (end.nodeType == 3) {
          endText += end.textContent.slice(0, range.endOffset);
        } else {
          for (var i = 0; i < range.endOffset; i++) {
            var n = end.childNodes[i];
            endText += n.textContent;
          }
        }
        if (config.endOnly) return endText;

        if (startText == endText && (start.contains(end) || end.contains(start))) {
          return startText;
        } else {
          return startText + endText;
        }
      }
    }

    // checks if a chunk is in any of the relations
    function isInRelations(c) {
      for (var key in relations) {
        var links = relations[key]['links'];
        for (var i = 0, len = links.length; i < len; i++) {
          if (links[i].s == c.id || links[i].t == c.id) return key;
        }
      }
      return false;
    }

    function removeAllChildren(node) {
      while (node.firstChild) {
        node.removeChild(node.firstChild);
      }
    }

    function initContextMenu(markedSpan, plugins) {
      if (Object.values(plugins).map(function(x) { return Object.keys(x).length; }).reduce(function(a, b) { return a + b; }, 0) > 0) {
        function createButton(plugin) {
          var btn = document.createElement('button');
          btn.className = "button is-primary is-small is-fullwidth is-rounded is-outlined mb-1";
          btn.textContent = plugin.verboseName;
          if (plugin.isAllowed(markedSpan)) {
            plugin.exec(markedSpan, btn);

            if (plugin.update) {
              // TODO: we dispatch event from the document whenever any relation change is occuring
              //       then we catching it here, but it gets overriden for every new markedSpan
              markedSpan.addEventListener(plugin.update, function (e) {
                (function(b) {
                  plugin.exec(e.target, b)
                })(btn);
              }, false);
            }
          }
          return btn;
        }

        var short = markedSpan.getAttribute('data-s');
        var div = document.createElement('div');
        var subset = Object.assign({}, plugins[short], plugins[undefined]);

        if (Object.keys(subset).length == 0) return;

        var keys = Object.keys(subset);
        keys.sort(function(x, y) {
          if (subset[x].verboseName < subset[y].verboseName) return -1;
          else if (subset[x].verboseName > subset[y].verboseName) return 1;
          else return 0;
        });
        for (var name in keys) {
          div.appendChild(createButton(subset[keys[name]]));
        }
        div.lastChild.classList.remove('mb-1');

        const instance = tippy(markedSpan, {
          content: div,
          interactive: true,
          trigger: 'manual',
          placement: "bottom"
        });

        markedSpan.addEventListener('contextmenu', function(event) {
          event.preventDefault();
          event.stopPropagation();
          var targetRect = event.target.getBoundingClientRect();

          instance.setProps({
            getReferenceClientRect: function() {
              var half = (targetRect.right - targetRect.left) / 2;
              return {
                width: 0,
                height: 0,
                top: targetRect.bottom,
                bottom: targetRect.bottom,
                left: targetRect.left + half,
                right: targetRect.left + half,
              }
            }
          });

          instance.show();
        });
      }
    }

    function getMarkerForChunk(c) {
      return document.querySelector('div.marker.tags[data-s="' + c['label'] + '"]');
    }

    function countChunksByType() {
      var cnt = {};
      for (var c in chunks) {
        var chunk = chunks[c];
        if (!chunk.hasOwnProperty('batch') && !chunk.submittable && !isInRelations(chunk)) {
          if (cnt.hasOwnProperty(chunk.label))
            cnt[chunk.label]++;
          else
            cnt[chunk.label] = 1;
        }
      }
      return cnt;
    }

    function resizeSVG() {
      var  svg = document.getElementById("relations").querySelector('svg');
      // Get the bounds of the SVG content
      var  bbox = svg.getBBox();
      // Update the width and height using the size of the contents
      svg.setAttribute("width", bbox.x + bbox.width + bbox.x);
      svg.setAttribute("height", bbox.y + bbox.height + bbox.y);
    }

    function getLabelText(obj) {
      var relLabels = {};
      var relIds = obj.querySelectorAll('span[data-m="r"]');
      for (var i = 0, len = relIds.length; i < len; i++) {
        var relSpan = relIds[i];
        relLabels[relSpan.parentNode.id] = relSpan.textContent;
        relSpan.textContent = "";
      }
      var text = obj.textContent;
      for (var i = 0, len = relIds.length; i < len; i++) {
        relSpan.textContent = relLabels[relIds[i].parentNode.id];
      }
      return text;
    }

    return {
      allowSelectingLabels: false,
      disableSubmittedLabels: false,
      drawingType: {},
      markersArea: null,
      selectorArea: null,   // the area where the article is
      contextMenuPlugins: {},
      isMarker: isMarker,
      isLabel: isLabel,
      init: function() {
        contextSize = $('#taskArea').data('context');
        this.markersArea = document.querySelector('.markers');
        this.relationsArea = document.querySelector('.relations:not(.marked)');
        this.selectorArea = document.querySelector('.selector');
        resetTextHTML = this.selectorArea == null ? "" : this.selectorArea.innerHTML;
        resetText = this.selectorArea == null ? "" : this.selectorArea.textContent.trim();
        this.allowSelectingLabels = this.markersArea == null ? false : this.markersArea.getAttribute('data-select') == 'true';
        this.disableSubmittedLabels = this.markersArea == null ? false : this.markersArea.getAttribute('data-disable') == 'true';
        markersInRelations = this.relationsArea == null ? [] :
          [].concat.apply([], Array.from(this.relationsArea.querySelectorAll('div.relation.tags')).map(
          x => [].concat.apply([], x.getAttribute('data-b').split('|').map(y => y.split('-:-'))) ));
        nonRelationMarkers = this.relationsArea == null ? [] :
          Array.from(this.markersArea.querySelectorAll('div.marker.tags')).map(
          x => x.getAttribute('data-s')).filter(x => !markersInRelations.includes(x));
        var repr = document.querySelector('#relationRepr');
        if (utils.isDefined(repr)) this.drawingType = JSON.parse(repr.textContent);
        this.initSvg();
        this.initEvents();
        this.updateMarkAllCheckboxes();
      },
      initEvents: function() {
        // event delegation
        if (this.selectorArea != null) {
          var control = this;
          this.selectorArea.addEventListener('click', function(e) {
            e.stopPropagation();
            var target = e.target;
            if (isDeleteButton(target)) {
              control.labelDeleteHandler(e);
              control.updateMarkAllCheckboxes();
            } else if (isLabel(target)) {
              if (control.allowSelectingLabels) {
                var $target = $(target);
                if ($target.prop('in_relation')) {
                  control.showRelationGraph(
                    parseInt(target.querySelector('[data-m="r"]').textContent)
                  );
                } else if (!window.getSelection().toString()) {
                  if (target.classList.contains('active') && $target.prop('selected')) {
                    target.classList.remove('active');
                    $target.prop('selected', false);
                  } else {
                    target.classList.add('active');
                    $target.prop('selected', true);
                  }
                }
              }
            }
          }, false);

          this.selectorArea.addEventListener('mouseover', function(e) {
            var target = e.target;
            if (isLabel(target)) {
              if (labelerModule.allowSelectingLabels) {
                e.stopPropagation();
                if (target.classList.contains("tag"))
                  if (!$(target).prop('selected'))
                    target.classList.add('active');
                else
                  if (!$(target.parentNode).prop('selected'))
                    target.parentNode.classList.add('active');
              }
            }
          }, false);

          this.selectorArea.addEventListener('mouseout', function(e) {
            var target = e.target;
            if (isLabel(target)) {
              if (labelerModule.allowSelectingLabels) {
                e.stopPropagation();
                if (target.classList.contains("tag"))
                  if (!$(target).prop('selected'))
                    target.classList.remove('active');
                else
                  if (!$(target.parentNode).prop('selected'))
                    target.parentNode.classList.remove('active');
              }
            }
          }, false)

          // adding chunk if a piece of text was selected with a mouse
          this.selectorArea.addEventListener('mouseup', function(e) {
            var isRightMB;
            e = e || window.event;

            if ("which" in e)  // Gecko (Firefox), WebKit (Safari/Chrome) & Opera
                isRightMB = e.which == 3; 
            else if ("button" in e)  // IE, Opera 
                isRightMB = e.button == 2;

            if (!isDeleteButton(e.target) && !isRightMB) {
              labelerModule.updateChunkFromSelection();
            }
          }, false);

          // TODO: might be potentially rewritten?
          // adding chunk if a piece of text was selected with a keyboard
          document.addEventListener("keydown", function(e) {
            var selection = window.getSelection();
            if (selection && (selection.anchorNode != null)) {
              var isArticleParent = selection.anchorNode.parentNode == document.querySelector('.selector');
              if (e.shiftKey && e.which >= 37 && e.which <= 40 && isArticleParent) {
                labelerModule.updateChunkFromSelection();
              }
            }
            var s = String.fromCharCode(e.which).toUpperCase();
            if (e.shiftKey) {
              var shortcut = document.querySelector('[data-shortcut="SHIFT + ' + s + '"]');
            } else {
              var shortcut = document.querySelector('[data-shortcut="' + s + '"]');
            }
            
            if (shortcut != null) {
              if (e.altKey && !e.shiftKey && !e.ctrlKey) {
                var input = shortcut.querySelector('input[type="checkbox"]');
                if (utils.isDefined(input)) {
                  input.checked = !input.checked;
                  const event = new Event('change', {bubbles: true});
                  input.dispatchEvent(event);
                }
              } else {
                shortcut.click();
              }
            }
          }, false);

          if (utils.isDefined(this.markersArea)) {
            this.markersArea.addEventListener('click', function(e) {
              var target = e.target;
              if (target.nodeName != 'INPUT') {
                var mmpi = control.markersArea.getAttribute('data-mmpi');
                control.mark(getClosestMarker(target), mmpi);
                control.updateMarkAllCheckboxes();
              }
            }, false);

            this.markersArea.addEventListener('change', function(e) {
              e.stopPropagation();
              var target = e.target;
              if (target.getAttribute('type') == 'checkbox') {
                var marker = getClosestMarker(target);
                control.selectorArea.querySelectorAll('[data-s="' + marker.getAttribute('data-s') + '"]').forEach(function(x) {
                  var $x = $(x);
                  if (!$x.prop('in_relation') && !$x.prop('disabled')) {
                    if (!target.checked && x.classList.contains('active') && $x.prop('selected')) {
                      x.classList.remove('active');
                      $x.prop('selected', false);
                    } else if (target.checked) {
                      x.classList.add('active');
                      $x.prop('selected', true);
                    }
                  }
                })
              }
            }, false);
          }

          if (utils.isDefined(this.relationsArea)) {
            this.relationsArea.addEventListener('click', function(e) {
              control.markRelation(getClosestRelation(e.target));
            }, false);
          }
        }
      },
      register: function(plugin, label) {
        var p = Object.assign({}, plugin);
        delete p.name;
        if (!(label in this.contextMenuPlugins)) this.contextMenuPlugins[label] = {};
        this.contextMenuPlugins[label][plugin.name] = p;

        if (p.update) {
          document.addEventListener(p.update, function(e) {
            const event = new Event(p.update);
            // select all labels and dispatch events
            document.querySelectorAll('span.tag').forEach(function(x) {
              x.dispatchEvent(event);
            });
          }, false);
        }
        pluginsToRegister--;

        if (pluginsToRegister <= 0) {
          this.initPreMarkers();
          this.updateMarkAllCheckboxes();
        }
      },
      expectToRegister: function() {
        pluginsToRegister++;
      },
      disableChunk: function(c) {
        var $el = $('span.tag[data-i="' + c['id'] + '"]');
        $el.addClass('is-disabled');
        $el.prop('disabled', true);
        $el.find('span[data-m="r"]').remove();
        c['submittable'] = false;
      },
      enableChunk: function(c) {
        var $el = $('span.tag[data-i="' + c['id'] + '"]');
        $el.removeClass('is-disabled');
        $el.prop('in_relation', false);
        $el.prop('disabled', false);
        c['submittable'] = true;
      },
      disableChunks: function(chunksList) {
        // disable given chunks visually
        for (var c in chunksList) {
          this.disableChunk(chunksList[c])
        }
        return chunksList;
      },
      getActiveChunk: function() {
        return chunks[chunks.length-1];
      },
      removeActiveChunk: function() {
        if (!chunks[chunks.length-1]['marked'])
          chunks.pop();
      },
      // initialize pre-markers, i.e. mark the specified words with a pre-specified marker
      initPreMarkers: function() {
        labelId = 0;
        var control = this;
        $('article.text span.tag').each(function(i, node) {
          node.setAttribute('data-i', labelId);
          control.updateChunkFromNode(node);
          initContextMenu(node, control.contextMenuPlugins);
          labelId++;
        })
        activeLabels = labelId;
      },
      updateChunkFromNode: function(node) {
        // adding the information about the node, representing a label, to the chunks array
        var chunk = {},
            marker = document.querySelector('div.marker.tags[data-s="' + node.getAttribute('data-s') + '"]'),
            markerText = marker.querySelector('span.tag:first-child');
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
      },
      updateChunkFromSelection: function() {
        // getting a chunk from the selection; the chunk then either is being added to the chunks array, if the last chunk was submitted
        // or replaces the last chunk if the last chunk was not submitted
        var selection = window.getSelection();

        if (selection && !selection.isCollapsed) {
          // group selections:
          //  - a label spanning other labels is selected, they should end up in the same group
          //  - two disjoint spans of text are selected, they should end up in separate groups (possible only in Firefox)
          var groups = [],
              group = [];
          group.push(selection.getRangeAt(0));
          for (var i = 1; i < selection.rangeCount; i++) {
            var last = group[group.length-1],
                cand = selection.getRangeAt(i);
            // NOTE:
            // - can't use `cand.compareBoundaryPoints(Range.END_TO_START, last)` because of delete buttons in the labels
            if ((last.endContainer.nextSibling == cand.startContainer) ||
               (last.endContainer.parentNode.nextSibling == cand.startContainer)) {
              group.push(cand);
            } else {
              groups.push(group);
              group = [cand];
            }
          }
          if (group)
            groups.push(group)


          for (var i = 0; i < groups.length; i++) {
            var chunk = {},
                group = groups[i],
                N = group.length;

            chunk['range'] = group[0].cloneRange();
            chunk['range'].setEnd(group[N-1].endContainer, group[N-1].endOffset);

            if (contextSize == 'p') {
              // paragraph
              var p = getEnclosingParagraph(chunk['range'].commonAncestorContainer);
              chunk['context'] = p == null ? null : p.textContent;
              chunk['lengthBefore'] = previousTextLength(chunk['range'].startContainer, true);
            } else if (contextSize == 't') {
              // text
              chunk['context'] = resetText;
              chunk['lengthBefore'] = previousTextLength(chunk['range'].startContainer, false);
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

            chunk['start'] = chunk['range'].startOffset;
            chunk['end'] = chunk['start'] + group.map(getSelectionLength).reduce((a, b) => a + b, 0);

            chunk['marked'] = false;
            chunk['label'] = null;

            var N = chunks.length;
            chunk['id'] = labelId;
            if (N == 0 || (N > 0 && chunks[N-1] !== undefined && chunks[N-1]['marked'])) {
              chunks.push(chunk);
            } else {
              chunks[N-1] = chunk;
            }
            console.log(chunk)
          } 
        } else {
          var chunk = this.getActiveChunk();
          if (utils.isDefined(chunk) && !chunk['marked'])
            this.removeActiveChunk();
        }
      },
      mark: function(obj, max_markers) {
        if (chunks.length > 0 && activeLabels < max_markers) {
          var chunk = this.getActiveChunk();

          if (!chunk.marked) {
            var color = obj.getAttribute('data-color'),
                textColor = obj.getAttribute('data-text-color'),
                markedSpan = document.createElement('span'),
                deleteMarkedBtn = document.createElement('button');
            markedSpan.className = "tag is-medium";
            markedSpan.setAttribute('data-s', obj.getAttribute('data-s'));
            markedSpan.setAttribute('data-i', chunk['id']);
            markedSpan.setAttribute('style', 'background-color:' + color + '; color:' + textColor + ";");
            $(markedSpan).prop('in_relation', false);
            deleteMarkedBtn.className = 'delete is-small';

            initContextMenu(markedSpan, this.contextMenuPlugins);

            // NOTE: avoid `chunk['range'].surroundContents(markedSpan)`, since
            // "An exception will be thrown, however, if the Range splits a non-Text node with only one of its boundary points."
            // https://developer.mozilla.org/en-US/docs/Web/API/Range/surroundContents
            try {
              chunk['range'].surroundContents(markedSpan);
              markedSpan.appendChild(deleteMarkedBtn);
            } catch (error) {
              var nodeAfterEnd = chunk['range'].endContainer.nextSibling;
              if (nodeAfterEnd != null && isDeleteButton(nodeAfterEnd)) {
                while (isLabel(nodeAfterEnd.parentNode)) {
                  nodeAfterEnd = nodeAfterEnd.parentNode;
                  if (nodeAfterEnd.nextSibling == null || !isDeleteButton(nodeAfterEnd.nextSibling))
                    break;
                  nodeAfterEnd = nodeAfterEnd.nextSibling;
                }
                chunk['range'].setEndAfter(nodeAfterEnd);
              }

              var nodeBeforeStart = chunk['range'].startContainer.previousSibling;
              if (nodeBeforeStart == null) {
                var start = chunk['range'].startContainer;
                while (isLabel(start.parentNode)) {
                  start = start.parentNode;
                }
                if (start != chunk['range'].startContainer)
                  chunk['range'].setStartBefore(start);
              }

              start = chunk['range'].startContainer;
              if (isRelationIdentifier(start)) {
                if (start.nodeType == 3)
                  start = start.parentNode;
                chunk['range'].setStartBefore(start.parentNode);
              }
              
              markedSpan.appendChild(chunk['range'].extractContents());
              markedSpan.appendChild(deleteMarkedBtn);
              chunk['range'].insertNode(markedSpan);
            }

            var marked = chunk['range'].commonAncestorContainer.querySelectorAll('span.tag');
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
            
            chunk['marked'] = true;
            chunk['submittable'] = obj.getAttribute('data-submittable') === 'true';
            chunk['id'] = labelId;
            labelId++;
            activeLabels++;
            chunk['label'] = obj.getAttribute('data-s');

            clearSelection(); // force clear selection
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
              // .attr('viewBox', '0,0,300,400')
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

          var svg = d3.select("#relations svg"),
              radius = 10;

          svg
            .attr("width", "85%")
            .attr("height", "85%");

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
                $(d.dom).addClass('active');
              })
              .on("mouseout", function(d, i) {
                $(d.dom).removeClass('active');
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

          $("#relationId").text(currentRelationId);
        }
      },
      drawList: function(data) {
        if (typeof d3 !== 'undefined') {
          var svg = d3.select("#relations svg"),
              radius = 10;

          svg.selectAll('g')
            .attr('class', 'hidden');

          svg = svg.append("g")
            .attr('id', data.id)

          data.nodes.forEach(function(n, i) {
            n['x'] = 10;
            n['y'] = 15 + i * (2 * radius + 7);
          })

          // Initialize the nodes
          var node = svg
            .selectAll("circle")
            .data(data.nodes)
            .enter()
            .append("circle")
              .attr("cx", function(d) { return d.x; })
              .attr("cy", function(d) { return d.y; })
              .attr("r", radius)
              .attr('data-id', function(d) { return d.id })
              .style("fill", function(d) { return d.color })
              .on("mouseover", function(d, i) {
                $(d.dom).addClass('active');
              })
              .on("mouseout", function(d, i) {
                $(d.dom).removeClass('active');
              });

          var text = svg.selectAll("text")
            .data(data.nodes)
            .enter().append("text")
              .text(function(d) { return d.name.length > 20 ? d.name.substr(0, 20) + '...' : d.name ; })
              .attr("x", function(d) { return d.x + radius * 1.3; })
              .attr("y", function(d) { return d.y + 0.5 * radius; });

          $("#relationId").text(currentRelationId);
        }
      },
      getAvailableRelationIds: function() {
        return Object.keys(relations);
      },
      countUnsubmittedChunks: function() {
        return chunks.filter(function(c) { return c.submittable }).length;
      },
      previousRelation: function() {
        if (currentRelationId == null) return currentRelationId;

        currentRelationId--;
        if (currentRelationId <= 0) {
          currentRelationId = 1;
        }
        return currentRelationId;
      },
      nextRelation: function() {
        if (currentRelationId == null) return currentRelationId;

        currentRelationId++;
        var graphIds = Object.keys(relations);
        if (currentRelationId > graphIds.length) {
          currentRelationId = graphIds.length;
        }
        return currentRelationId;
      },
      removeRelation: function(idx, exception) {
        $('g#' + relations[idx]['graphId']).find('circle[data-id]').each(function(i, d) { 
          var $el = $('#' + d.getAttribute('data-id'));
          if (utils.isDefined(exception) && $el.attr('id') == $(exception).attr('id')) return;
          if ($el.length > 0) {
            $el.prop('in_relation', false);
            $el.attr('id', '');
            $el.find('[data-m="r"]').remove();
          }
        });
        d3.select('g#' + relations[idx]['graphId']).remove();
        delete relations[idx];
        var map = {}
        var keys = Object.keys(relations);
        keys.sort();
        for (var k in keys) {
          var kk = parseInt(keys[k]);
          if (kk > idx) {
            $('g#' + relations[keys[k]]['graphId']).find('circle[data-id]').each(function(i, d) { 
              var $el = $('#' + d.getAttribute('data-id'));
              if ($el.length > 0) {
                $el.find('[data-m="r"]').text(kk-1);
              }
            });
            relations[kk-1] = relations[kk];
            map[kk] = kk - 1;
            delete relations[kk];
          } else {
            map[kk] = kk;
          }
        }

        if (utils.isDefined(keys[k])) {
          lastRelationId = kk > idx ? kk : kk + 1;
        } else {
          lastRelationId = 1;
        }

        const event = new Event(RELATION_CHANGE_EVENT);
        // Dispatch the event.
        document.dispatchEvent(event);

        return map;
      },
      removeCurrentRelation: function() {
        this.removeRelation(currentRelationId);
        var graphIds = Object.keys(relations);
        currentRelationId = graphIds.length > 0 ? graphIds.length : null;
        return currentRelationId;
      },
      showRelationGraph(id) {
        if (id == null || id === undefined)
          $('#relationId').text(0);
        else {
          var svg = d3.select("#relations svg")

          svg.selectAll('g')
            .attr('class', 'hidden');

          d3.select('g#' + relations[id]['graphId'])
            .attr('class', '');

          $('#relationId').text(id);
          resizeSVG();
        }
        currentRelationId = id;
      },
      markRelation: function(obj) {
        if (!this.checkRestrictions(true)) return;

        var $parts = $('.selector span.tag.active'),
            between = obj.getAttribute('data-b').split('|').map(x => x.split('-:-')),
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
              'name': getLabelText($parts[i]),
              'dom': $parts[i],
              'color': getComputedStyle($parts[i])["background-color"]
            });
          });

          var from = null,
              to = null;
          if (direction == '0' || direction == '2') {
            // first -> second or bidirectional
            from = 0;
            to = 1;
          } else if (direction == '1') {
            // second -> first
            from = 1;
            to = 0;
          }

          var sketches = [];
          for (var i = 0, len = between.length; i < len; i++) {
            var sketch = {
              'nodes': {},
              'links': [],
              'between': between[i]
            }
            if (utils.isDefined(nodes[between[i][from]]) && utils.isDefined(nodes[between[i][to]])) {
              if (!sketch.nodes.hasOwnProperty(between[i][from]))
                sketch.nodes[between[i][from]] = [];
              sketch.nodes[between[i][from]].push.apply(sketch.nodes[between[i][from]], nodes[between[i][from]]);
              if (nodes[between[i][from]] != nodes[between[i][to]]) {
                if (!sketch.nodes.hasOwnProperty(between[i][to]))
                  sketch.nodes[between[i][to]] = [];
                sketch.nodes[between[i][to]].push.apply(sketch.nodes[between[i][to]], nodes[between[i][to]]);
              }
              nodes[between[i][from]].forEach(function(f) {
                nodes[between[i][to]].forEach(function(t) {
                  if (f.id != t.id) {
                    // prevent loops
                    sketch.links.push({
                      'source': f.id,
                      'target': t.id
                    })
                  }
                })
              })
              sketches.push(sketch);
            }
          }

          if (sketches.length == 0) {
            alert("No relations could be formed among the selected labels");
            $parts.removeClass('active');
            $parts.prop('selected', false);
            $parts.prop('in_relation', false);
            return;
          }

          var j = startId;
          for (var i = 0, len = sketches.length; i < len; i++) {
            for (var key in sketches[i].nodes) {
              j += sketches[i].nodes[key].length;
            }
            relations[lastRelationId] = {
              'graphId': "n" + startId + "__" + (j - 1),
              'rule': rule,
              'between': sketches[i].between,
              'links': [],
              'd3': {
                'nodes': sketches[i].nodes,
                'links': sketches[i].links,
                'from': from,
                'to': to,
                'direction': direction
              }
            };

            sketches[i].links.forEach(function(l) {
              var source = document.querySelector('#' + l.source),
                  target = document.querySelector('#' + l.target);
              // if bidirectional, no need to store mirrored relations
              if (direction == 2 && containsIdentical(relations[lastRelationId]['links'], {
                's': target.getAttribute('data-i'),
                't': source.getAttribute('data-i')
              })) return;

              relations[lastRelationId]['links'].push({
                's': source.getAttribute('data-i'),
                't': target.getAttribute('data-i')
              })
            });

            if (currentRelationId == null)
              currentRelationId = 1;
            else
              currentRelationId++;

            if (!utils.isDefined(this.drawingType[rule]) || this.drawingType[rule] == 'g') {
              this.drawNetwork({
                'id': "n" + startId + "__" + (j - 1),
                'nodes': Array.prototype.concat.apply([], Object.values(sketches[i].nodes)),
                'links': [].concat(sketches[i].links) // necessary since d3 changes the structure of links
              }, (from != null && to != null && direction != '2'))
            } else if (this.drawingType[rule] == 'l') {
              this.drawList({
                'id': "n" + startId + "__" + (j - 1),
                'nodes': Array.prototype.concat.apply([], Object.values(sketches[i].nodes))
              })  
            }

            for (var s in sketches[i].nodes) {
              var snodes = sketches[i].nodes[s];
              snodes.forEach(function(x) {
                var relSpan = document.createElement('span');
                relSpan.setAttribute('data-m', 'r');
                relSpan.className = "rel";
                relSpan.textContent = lastRelationId;
                x.dom.appendChild(relSpan);
                x.dom.classList.remove('active')
                $(x.dom).prop('selected', false);
              });
            }

            lastRelationId++;
            startId = j;
          }

          const event = new Event(RELATION_CHANGE_EVENT);
          // Dispatch the event.
          document.dispatchEvent(event);
          this.updateMarkAllCheckboxes()
          resizeSVG();
        }
      },
      changeRelation: function(obj, fromId, toId) {
        var objId = obj.id,
            il = obj.getAttribute('data-i'),
            short = obj.getAttribute('data-s'),
            fromRel = relations[fromId],
            toRel = relations[toId],
            // a relation map, which is initially identity, but might become smth else if anything is deleted
            map = {[fromId]: fromId, [toId]: toId}; 

        if (utils.isDefined(fromRel) && utils.isDefined(toRel) && fromRel.between.sort().join(',') != toRel.between.sort().join(',')) {
          alert("Cannot move between different kind of relations")
          return;
        }

        if (utils.isDefined(fromRel)) {
          var newNodes = fromRel.d3.nodes[short].filter(function(x) { return x.id == objId });
          fromRel.links = fromRel.links.filter(function(x) { return x.s != il && x.t != il });
          fromRel.d3.nodes[short] = fromRel.d3.nodes[short].filter(function(x) { return x.id != objId });
          if (fromRel.links.length > 0) {
            fromRel.d3.links = fromRel.d3.links.filter(function(x) { return x.source.id != objId && x.target.id != objId});
            d3.select('g#' + fromRel.graphId).remove();
            if (!utils.isDefined(this.drawingType[fromRel.rule]) || this.drawingType[fromRel.rule] == 'g') {
              this.drawNetwork({
                'id': fromRel.graphId,
                'nodes': Array.prototype.concat.apply([], Object.values(fromRel.d3.nodes)),
                'links': [].concat(fromRel.d3.links)
              }, (fromRel.d3.from != null && fromRel.d3.to != null && fromRel.d3.direction != '2'))
            } else if (this.drawingType[fromRel.rule] == 'l') {
              this.drawList({
                'id': fromRel.graphId,
                'nodes': Array.prototype.concat.apply([], Object.values(fromRel.d3.nodes))
              })
            }
          } else {
            map = (utils.isDefined(toId) && toId != -1) ? this.removeRelation(fromId, obj) : this.removeRelation(fromId);
            this.showRelationGraph(null);
          }
        } else {
          // means obj was in no relation previously
          obj.id = 'rl_' + lastNodeInRelationId;
          lastNodeInRelationId++;
          var relSpan = obj.querySelector('span[data-m="r"]');
          if (relSpan == null) {
            relSpan = document.createElement('span');
            relSpan.setAttribute('data-m', 'r');
            relSpan.classList.add('rel');
            relSpan.textContent = "";
            obj.appendChild(relSpan);
          }
          
          $(obj).prop('in_relation', true);
          var newNodes = [
            {
              'id': obj.id,
              'name': getLabelText(obj),
              'dom': obj,
              'color': getComputedStyle(obj)["background-color"]
            }
          ];
        }

        if (utils.isDefined(toRel)) {
          var newLinks = [];
          if (toRel.between[toRel.d3.to] == short) {
            toRel.d3.nodes[toRel.between[toRel.d3.from]].forEach(function(f) {
              newNodes.forEach(function(t) {
                if (f.id != t.id) {
                  // prevent loops
                  newLinks.push({
                    'source': f.id,
                    'target': t.id
                  })
                }
              })
            });
          }
          
          if (toRel.between[toRel.d3.from] == short) {
            newNodes.forEach(function(f) {
              toRel.d3.nodes[toRel.between[toRel.d3.to]].forEach(function(t) {
                if (f.id != t.id) {
                  // prevent loops
                  newLinks.push({
                    'source': f.id,
                    'target': t.id
                  })
                }
              })
            });
          }
          toRel.d3.nodes[short] = toRel.d3.nodes[short].concat(newNodes);

          newLinks.forEach(function(l) {
            var source = document.querySelector('#' + l.source),
                target = document.querySelector('#' + l.target);
            if (toRel.d3.direction == 2 && containsIdentical(toRel.links, {
              's': target.getAttribute('data-i'),
              't': source.getAttribute('data-i')
            })) return;
            toRel.links.push({
              's': source.getAttribute('data-i'),
              't': target.getAttribute('data-i')
            })
          });

          toRel.d3.links = toRel.d3.links.concat(newLinks);

          d3.select('g#' + toRel.graphId).remove();
          if (!utils.isDefined(this.drawingType[toRel.rule]) || this.drawingType[toRel.rule] == 'g') {
            this.drawNetwork({
              'id': toRel.graphId,
              'nodes': Array.prototype.concat.apply([], Object.values(toRel.d3.nodes)),
              'links': [].concat(toRel.d3.links)
            }, (toRel.d3.from != null && toRel.d3.to != null && toRel.d3.direction != '2'))
          } else if (this.drawingType[toRel.rule] == 'l') {
            this.drawList({
              'id': toRel.graphId,
              'nodes': Array.prototype.concat.apply([], Object.values(toRel.d3.nodes))
            })
          }
          
          obj.querySelector('[data-m="r"]').textContent = map[toId];

          this.showRelationGraph(map[toId]);
        }

        // deselect if somone accidentally left clicked on the label
        obj.classList.remove('active')
        $(obj).prop('selected', false);

        const event = new Event(RELATION_CHANGE_EVENT);
        // Dispatch the event.
        document.dispatchEvent(event);
        resizeSVG();
      },
      labelDeleteHandler: function(e) {
        // when a delete button on any label is clicked
        e.stopPropagation();
        var target = e.target,
            parent = target.parentNode, // actual span
            sibling = target.nextSibling,
            chunkId = parent.getAttribute('data-i'),
            chunk2del = chunks.filter(function(x) { return x.id == chunkId}); // the span with a relation number (if any)

        var rel = isInRelations(chunk2del[0]);
        if (rel) {
          this.changeRelation(parent, rel, null);
        }

        target.remove();
        if (sibling != null)
          sibling.remove();
        chunks = chunks.filter(function(x) { return x.id != chunkId });
        mergeWithNeighbors(parent);
        // $(target).prop('in_relation', false);
        activeLabels--;
      },
      getSubmittableDict: function(stringify) {
        if (!utils.isDefined(stringify)) stringify = false;
        if (Object.values(relations).map(function(x) { return Object.keys(x).length; }).reduce(function(a, b) { return a + b; }, 0) > 0) {
          // if there are any relations, submit only those chunks that have to do with the relations
          submittableChunks = chunks.filter(isInRelations)
          
          var nonRelationChunks = chunks.filter(x => !submittableChunks.includes(x));
          for (var i = 0, len = nonRelationChunks.length; i < len; i++) {
            if (nonRelationMarkers.includes(nonRelationChunks[i]['label'])) {
              submittableChunks.push(nonRelationChunks[i]);
            }
          }
        } else {
          // if there are no relations, submit only submittable chunks, i.e. independent chunks that should not be a part of any relations
          submittableChunks = chunks.filter(function(c) { return c.submittable })
        }
        
        // add plugin info to chunks
        for (var i = 0, len = submittableChunks.length; i < len; i++) {
          submittableChunks[i]['extra'] = {};
          var plugins = this.contextMenuPlugins[submittableChunks[i].label];
          for (var name in plugins) {
            submittableChunks[i]['extra'][name] = plugins[name].storage[submittableChunks[i]['id']] || ''; 
          }
        }

        var submitRelations = [];
        submitRelations = submitRelations.concat.apply(submitRelations, Object.values(relations).map(function(x) {
          return {
            'links': x['links'],
            'rule': x['rule']
          }
        }));

        return {
          "relations": stringify ? JSON.stringify(submitRelations) : submitRelations,
          "chunks": stringify ? JSON.stringify(submittableChunks) : submittableChunks
        }
      },
      unmarkChunk: function(c) {
        var label = document.querySelector('span.tag[data-i="' + c['id'] + '"]');
        label.querySelector('span').remove();
        label.querySelector('button').remove();
        mergeWithNeighbors(label);
      },
      unmark: function(chunksList) {
        for (var c in chunksList) {
          this.unmarkChunk(chunksList[c])
        }
      },
      postSubmitHandler: function(batch) {
        relations = {};
        currentRelationId = null;
        lastRelationId = 1;
        // clear svg
        d3.selectAll("svg > *").remove()
        this.showRelationGraph(currentRelationId);
        activeLabels = 0;

        chunks.forEach(function(c) {
          if (submittableChunks.includes(c)) {
            // means already submitted, so mark as such
            c.submittable = false;
            c.batch = batch;
          }
        });
        submittableChunks = [];
      },
      resetArticle: function() {
        this.selectorArea.innerHTML = resetTextHTML;
      },
      restart: function() {
        chunks = [];
        resetTextHTML = this.selectorArea.innerHTML;
        resetText = this.selectorArea.textContent;

        this.initPreMarkers();
        this.updateMarkAllCheckboxes();
      },
      undo: function(batches) {
        var control = this;
        chunks.forEach(function(c) {
          if (batches.includes(c.batch)) {
            if (control.disableSubmittedLabels) {
              control.enableChunk(c);
            }
          }
        });
      },
      updateMarkAllCheckboxes() {
        var cnt = countChunksByType();
        $('[data-s] input[type="checkbox"]').prop("disabled", true);
        $('[data-s] input[type="checkbox"]').prop("checked", false);
        for (var i in cnt) {
          if (cnt[i] > 0) {
            $('[data-s="' + i + '"] input[type="checkbox"]').prop("disabled", false);
          }
        }
      }
    }
  })();

  $(document).ready(function() {
    labelerModule.init();
    
    // window.lm = labelerModule;

    /**
     * Labeler plugins
     */
    var labelerPluginsDOM = document.querySelector("#labelerPlugins"),
        labelerPlugins = JSON.parse(labelerPluginsDOM.textContent);
    for (var markerShort in labelerPlugins) {
      for (var i = 0, len = labelerPlugins[markerShort].length; i < len; i++) {
        var pluginCfg = labelerPlugins[markerShort][i];
        $.getScript(labelerPluginsDOM.getAttribute('data-url') + pluginCfg['file'], (function(cfg, ms) {
          return function() {
            labelerModule.register(plugin(cfg, labelerModule), ms);
          }
        })(pluginCfg, markerShort));
        labelerModule.expectToRegister();
      }
    }

    var sessionStart = new Date();  // the time the page was loaded or the last submission was made
        
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

    // disable the undo button, since we haven't submitted anything
    $('#undoLast').attr('disabled', true);  

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
          labelerModule.undo(data.batch);

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


    // TODO(dmytro):
    // - after the relationship is submitted, the ID starts over, whereas old ID is still there - confusing
    // - making labels in relationships transparent works very poorly for nested labels, so think of another way

    // submitting the marked labels and/or relations with(out) inputs
    $('#inputForm .submit.button').on('click', function(e) {
      e.preventDefault();

      // check if restrictions are violated
      if (!labelerModule.checkRestrictions()) return;

      var $inputForm = $('#inputForm'),
          $inputBlock = $inputForm.closest('article');

      var inputFormData = $inputForm.serializeObject(),
          underReview = $inputBlock.prop('review') || false,
          $markerGroups = $("#markerGroups");

      // if there's an input form field, then create input_context
      if ($markerGroups.length > 0) {
        if ($markerGroups.valid()) {
          inputFormData['input_context'] = labelerModule.selectorArea.textContent;
        } else {
          return;
        }
      }

      $.extend(inputFormData, labelerModule.getSubmittableDict());

      inputFormData['is_review'] = underReview;
      inputFormData['time'] = Math.round(((new Date()).getTime() - sessionStart.getTime()) / 1000, 1);
      inputFormData['datasource'] = parseInt(labelerModule.selectorArea.getAttribute('data-s'));
      inputFormData['datapoint'] = parseInt(labelerModule.selectorArea.getAttribute('data-dp'));

      if (inputFormData['chunks'].length > 0 || inputFormData['relations'].length > 0 || $markerGroups.length > 0) {
        inputFormData['chunks'] = JSON.stringify(inputFormData['chunks']);
        inputFormData['relations'] = JSON.stringify(inputFormData['relations']);
        inputFormData["marker_groups"] = JSON.stringify($markerGroups.length > 0 ? $markerGroups.serializeObject() : {});
        
        $.ajax({
          method: "POST",
          url: inputForm.action,
          dataType: "json",
          data: inputFormData,
          success: function(data) {
            if (data['error'] == false) {
              var $title = $inputBlock.find('.message-header p');

              // $("#markerGroups input").each(function(x) {
              //   $(x).val('');
              // });

              if (data['next_task'] == 'regular') {
                // no review task
                // resetArticle();
                
                if (labelerModule.disableSubmittedLabels)
                  labelerModule.disableChunks(JSON.parse(inputFormData['chunks']));
                else
                  labelerModule.unmark(JSON.parse(inputFormData['chunks']));

                $inputBlock.removeClass('is-warning');
                $inputBlock.addClass('is-primary');
                $inputBlock.prop('review', false);

                // TODO: get title for a review task from the server
                //       make it a configurable project setting
                $title.html("Your question");
              } else {
                // FIXME: review task
                labelerModule.resetArticle();

                $questionBlock.removeClass('is-primary');
                $questionBlock.addClass('is-warning');
                $questionBlock.prop('review', true);

                $title.html("Review question");
              }
            }

            var $submitted = $('#submittedTotal'),
                $submittedToday = $('#submittedToday');
            
            $submitted.text(data['submitted']);
            $submitted.append($('<span class="smaller">q</span>'));
            
            $submittedToday.text(data['submitted_today']);
            $submittedToday.append($('<span class="smaller">q</span>'));
            
            sessionStart = new Date();

            $("#markerGroups input").each(function(i, x) { $(x).val('') });

            // TODO; trigger iff .countdown is present
            $('.countdown').trigger('cdAnimateStop').trigger('cdAnimate');

            labelerModule.postSubmitHandler(data.batch);

            $('#undoLast').attr('disabled', false);
          },
          error: function() {
            console.log("ERROR!");
            $('#undoLast').attr('disabled', true);
            sessionStart = new Date();
            $('.countdown').trigger('cdAnimateReset').trigger('cdAnimate');
          }
        })
      }
    })

    function getNewText(confirmationCallback, $button) {
      var confirmation = confirmationCallback();
      $button.attr('disabled', true);

      if (confirmation) {
        var $el = $('.selector.element');
        $el.addClass('is-loading');

        $.ajax({
          type: "POST",
          url: $button.attr('href'),
          dataType: "json",
          data: {
            "csrfmiddlewaretoken": $('input[name="csrfmiddlewaretoken"]').val(),
            "sId": $el.attr('data-s'),
            "dpId": $el.attr('data-dp')
          },
          success: function(d) {
            // update text, source id and datapoint id
            $el.attr('data-s', d.source_id);
            $el.attr('data-dp', d.dp_id);
            var dpName = $('#dpName');
            if (dpName.text()) {
              dpName.text("(" + d.dp_source_name + ")")
            }

            var $selector = $(labelerModule.selectorArea);

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
              labelerModule.restart();
              $('#undoLast').attr('disabled', true);
              $button.attr('disabled', false);
            }
            $("#markerGroups input").each(function(i, x) { $(x).val('') });
            $el.removeClass('is-loading');
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

      // TODO: should I also count relations here?
      getNewText(function() {
        var confirmationText = "All your unsubmitted labels will be removed. Are you sure?";
        return labelerModule.countUnsubmittedChunks() > 0 ? confirm(confirmationText) : true;
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
          "ds_id": labelerModule.selectorArea.getAttribute('data-s'),
          "dp_id": labelerModule.selectorArea.getAttribute('data-dp')
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
})();