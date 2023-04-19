(function ($, d3, tippy, django, bulmaCollapsible) {
  const utils = {
    isDefined: function (x) {
      return x != null && x !== undefined;
    },
    unique: function (arr) {
      const seen = new Set();
      return arr.filter(function (elem) {
        const key = elem["start"] + " -- " + elem["end"];
        let isDuplicate = seen.has(key);
        if (!isDuplicate) seen.add(key);
        return !isDuplicate;
      });
    },
    serializeHashedObject: function (obj) {
      let o = {};
      $(obj).each(function (i, x) {
        if (utils.isDefined(x.value) && x.value != "") {
          if (x.getAttribute("data-h")) {
            o[x.getAttribute("name")] = {
              value: x.value,
              hash: x.getAttribute("data-h"),
            };
          } else {
            o[x.getAttribute("name")] = x.value;
          }
        }
      });
      return o;
    },
    title: function (string) {
      return string.charAt(0).toUpperCase() + string.slice(1);
    },
    arrayEquals: function (a, b) {
      return (
        Array.isArray(a) &&
        Array.isArray(b) &&
        a.length === b.length &&
        a.every((val, index) => val === b[index])
      );
    },
    defaultobj: function (creator) {
      return new Proxy(Object(), {
        get(obj, prop) {
          if (!obj.hasOwnProperty(prop)) obj[prop] = creator();
          return obj[prop];
        },
      });
    },
    getRadioLabel: function (inp) {
      let label = document.querySelector(
        'p[data-label-for="' + inp.getAttribute("name") + '"]'
      );
      if (this.isDefined(label)) {
        return label.firstChild.textContent.trim();
      }
    },
    expandMode: function (m) {
      return m == "e" ? "editing" : "reviewing";
    },
  };

  const labelerModule = (function () {
    const RELATION_CHANGE_EVENT = "labeler_relationschange";
    const LINE_ENDING_TAGS = [
      "P",
      "UL",
      "BLOCKQUOTE",
      "H1",
      "H2",
      "H3",
      "H4",
      "H5",
      "H6",
      "ARTICLE",
    ];
    const LABEL_CSS_SELECTOR = "span.tag[data-s]";
    const RADIO_CHECK_SEPARATOR = "||";

    let chunks = [], // the array of all chunks of text marked with a label, but not submitted yet
      relations = {}, // a map from relationId to the list of relations constituting it
      labelId = 0,
      editingBatch = undefined,
      activeLabels = 0, // a number of labels currently present in the article
      currentRelationId = null, // the ID of the current relation (for a visual pane)
      lastRelationId = 1, // the ID of the last unsubmitted relation
      lastNodeInRelationId = 0, // TODO: maybe remove
      resetTextHTML = null, // the HTML of the loaded article
      resetText = null, // the text of the loaded article
      pluginsToRegister = 0,
      originalConfig = undefined;

    function containsIdentical(arr, obj) {
      for (let i in arr) {
        let found = true;
        for (let k in obj) {
          found = found && arr[i].hasOwnProperty(k) && obj[k] == arr[i][k];
          if (!found) break;
        }
        if (found) return true;
      }
      return false;
    }

    function clearSelection() {
      if (window.getSelection) {
        if (window.getSelection().empty) {
          // Chrome
          window.getSelection().empty();
        } else if (window.getSelection().removeAllRanges) {
          // Firefox
          window.getSelection().removeAllRanges();
        }
      } else if (document.selection) {
        // IE?
        document.selection.empty();
      }
    }

    // This function was used before getRangeLength
    // but it didn't work, because it turned out
    // range.toString() doesn't care about newlines!
    // See more:
    // - https://github.com/timdown/rangy/issues/306
    // - https://stackoverflow.com/questions/1146730/problem-detecting-newlines-in-javascript-range-object
    //
    // Solution: replaced with getRangeLength
    //
    // function getSelectionLength(range) {
    //   return range.toString().length;
    // }

    function getRangeLength(range) {
      let fragment = range.cloneContents();
      let lens = Array.from(fragment.childNodes).map(getNodeLength);
      return lens.reduce((a, b) => a + b, 0);
    }

    // hide those that will influence textContent
    // crucial for making textContent handle newlines correctly!
    function showExtraElements(selectorArea, makeVisible) {
      let $sel = $(selectorArea),
        $relNum = $sel.find('[data-m="r"]').addBack('[data-m="r"]'),
        $delBtn = $sel.find("button.delete").addBack("button.delete"),
        $meta = $sel.find("[data-meta]").addBack("[data-meta]"),
        $br = $sel.find("br").addBack("br"),
        $pinned = $sel.find(".pinned").addBack(".pinned");

      if (makeVisible) {
        $relNum.show();
        $delBtn.show();
        $meta.show();
        $br.each(function (i, x) {
          x.textContent = "";
        });
        $pinned.each(function (i, x) {
          x.previousSibling.remove();
        });
      } else {
        $relNum.hide();
        $delBtn.hide();
        $meta.hide();
        $br.each(function (i, x) {
          x.textContent = "\n";
        });
        $pinned.before(document.createTextNode("\n\n"));
      }
      ui.extraElementsVisible = makeVisible;
    }

    function getNodeLength(node) {
      /*
       * This function calculates the length of the nodes textContent
       * including possible newline characters.
       */

      let len = 0;
      let originalVisibility = ui.extraElementsVisible;
      if (originalVisibility) showExtraElements(node, false);

      if (node.nodeType === 1) {
        if (
          (node.tagName == "SPAN" && node.classList.contains("tag")) ||
          LINE_ENDING_TAGS.includes(node.tagName)
        ) {
          // if there is a label, need to remove the possible relation label
          // This is why normally we would use innerText here and not textContent
          // but now we hid extra elements already, we could just use textContent
          // since it's faster
          len += node.textContent.length;
          // +1 because P is replaced by '\n'
          if (LINE_ENDING_TAGS.includes(node.tagName)) len += 1;
        } else if (node.tagName != "SCRIPT" && node.tagName != "BUTTON") {
          // we don't need to account for invisible parts in any cases,
          // other than the ones from the previous else if statement
          // also sometimes a browser will correct typos like double spaces automatically
          // but because .surroundContents happens on the TEXT_NODE with all
          // typos included, we want the original TEXT_CONTENT to be here
          len += node.textContent.length;
        }
      } else if (node.nodeType === 3) {
        // TEXT_NODE
        len += node.length;
      }

      if (originalVisibility) showExtraElements(node, originalVisibility);
      return len;
    }

    function previousTextLength(node) {
      function getPrevLength(prev, onlyElements) {
        if (onlyElements === undefined) onlyElements = false;
        let len = 0;
        while (prev != null) {
          len += getNodeLength(prev);
          prev = onlyElements
            ? prev.previousElementSibling
            : prev.previousSibling;
        }
        return len;
      }

      let selectorArea = document.querySelector("#selector");

      showExtraElements(selectorArea, false);

      // account for the same paragraph
      let textLength = getPrevLength(node.previousSibling);

      // account for the previous text of the enclosing label
      let enclosingLabel = getEnclosingLabel(node);
      if (enclosingLabel != null && enclosingLabel != node)
        textLength += getPrevLength(enclosingLabel.previousSibling);

      // account for nesting
      while (isLabel(node.parentNode) && node.parentNode != enclosingLabel) {
        node = node.parentNode;
        textLength += getPrevLength(node.previousSibling);
      }

      // Find previous <p> or <ul>
      let parent = getEnclosingParagraph(node);

      if (parent != null && parent.tagName == "UL") textLength += 1; // because <ul> adds a newline character to the beginning of the string

      // all text scope
      if (parent != null) {
        textLength += getPrevLength(parent.previousElementSibling, true);

        if (parent.parentNode.tagName == "BLOCKQUOTE") {
          // +1 because <blockquote> adds a newline char to the beginning of the string
          textLength +=
            getPrevLength(parent.parentNode.previousElementSibling, true) + 1;
        }
      }

      showExtraElements(selectorArea, true);
      return textLength;
    }

    function isDeleteButton(node) {
      return (
        utils.isDefined(node) &&
        node.nodeName == "BUTTON" &&
        node.classList.contains("delete")
      );
    }

    function isLabel(node) {
      return (
        utils.isDefined(node) &&
        node.nodeName == "SPAN" &&
        node.classList.contains("tag") &&
        node.hasAttribute("data-s")
      );
    }

    function filterSiblings(node, checker) {
      let prev = node.previousSibling,
        next = node.nextSibling,
        res = [];

      while (utils.isDefined(prev)) {
        if (checker(prev)) res.push(prev);
        prev = prev.previousSibling;
      }

      while (utils.isDefined(next)) {
        if (checker(next)) res.push(next);
        next = next.nextSibling;
      }

      return res;
    }

    function isMarker(node) {
      return (
        utils.isDefined(node) &&
        node.nodeName == "DIV" &&
        node.hasAttribute("data-s") &&
        node.hasAttribute("data-color") &&
        node.hasAttribute("data-res") &&
        node.hasAttribute("data-shortcut") &&
        node.hasAttribute("data-indep")
      );
    }

    function isRelation(node) {
      return (
        utils.isDefined(node) &&
        node.nodeName == "DIV" &&
        node.hasAttribute("data-b") &&
        node.hasAttribute("data-d") &&
        node.hasAttribute("data-r") &&
        node.hasAttribute("data-shortcut")
      );
    }

    function isRelationIdentifier(node) {
      if (node.nodeType === 3) {
        node = node.parentNode;
      }
      return (
        utils.isDefined(node) &&
        node.nodeName == "SPAN" &&
        node.hasAttribute("data-m") &&
        node.getAttribute("data-m") == "r"
      );
    }

    function isBatch(node) {
      return (
        utils.isDefined(node) &&
        node.nodeName == "LI" &&
        node.hasAttribute("data-mode") &&
        node.getAttribute("data-mode") == "e"
      );
    }

    function isPostSubmitArea(node) {
      return (
        utils.isDefined(node) &&
        node.nodeName == "ARTICLE" &&
        node.hasAttribute("data-mode") &&
        node.hasAttribute("id") &&
        node.id === node.getAttribute("data-mode") + "Board"
      );
    }

    function isScrollablePart(node) {
      return (
        utils.isDefined(node) &&
        node.nodeName == "DIV" &&
        node.className == "scrollable"
      );
    }

    function isPurposeNode(node) {
      return utils.isDefined(node) && node.hasAttribute("data-purpose");
    }

    function isInsideTippyContent(node) {
      while (utils.isDefined(node.id) && !node.id.startsWith("tippy")) {
        if (!utils.isDefined(node)) break;
        node = node.parentNode;
      }
      return utils.isDefined(node.id) && node.id.startsWith("tippy");
    }

    function isAncestor(node, ancestorCand) {
      while (node != ancestorCand) {
        if (!utils.isDefined(node)) break;
        node = node.parentNode;
      }
      return node == ancestorCand;
    }

    function isFormField(node) {
      return utils.isDefined(node) && node.classList.contains("field");
    }

    function getEnclosing(node, isOfType) {
      node = node.parentNode;
      while (isOfType(node)) {
        if (!utils.isDefined(node)) break;
        node = node.parentNode;
      }
      return isOfType(node) ? node : null;
    }

    function getClosest(node, isOfType) {
      while (!isOfType(node)) {
        if (!utils.isDefined(node)) break;
        node = node.parentNode;
      }
      return isOfType(node) ? node : null;
    }

    function getEnclosingLabel(node) {
      return getEnclosing(node, isLabel);
    }

    function getClosestFormField(node) {
      return getClosest(node, isFormField);
    }

    function getClosestBatch(node) {
      return getClosest(node, isBatch);
    }

    function getClosestPurposeNode(node) {
      return getClosest(node, isPurposeNode);
    }

    function getClosestMarker(node) {
      return getClosest(node, isMarker);
    }

    function getClosestRelation(node) {
      return getClosest(node, isRelation);
    }

    function getClosestPostSubmitArea(node) {
      return getClosest(node, isPostSubmitArea);
    }

    function getEnclosingParagraph(node) {
      while (!["UL", "BODY", "P", "ARTICLE"].includes(node.tagName))
        node = node.parentNode;
      return ["P", "UL", "ARTICLE"].includes(node.tagName) ? node : null;
    }

    function mergeDisjoint(node1, node2) {
      node2.innerHTML = node1.innerHTML + node2.innerHTML;
    }

    function mergeWithNeighbors(node) {
      // merge the given node with two siblings - used when deleting a label
      let next = node.nextSibling,
        prev = node.previousSibling,
        parent = node.parentNode;

      let pieces = Array.from(node.childNodes);

      if (pieces.length > 1) {
        if (
          pieces[0].nodeType === 3 &&
          utils.isDefined(prev) &&
          prev.nodeType === 3
        )
          parent.replaceChild(
            document.createTextNode(prev.data + pieces[0].data),
            prev
          );
        else if (
          isLabel(pieces[0]) &&
          isLabel(prev) &&
          pieces[0].getAttribute("data-i") == prev.getAttribute("data-i")
        ) {
          mergeDisjoint(prev, pieces[0]);
          parent.replaceChild(pieces[0], prev);
        } else parent.insertBefore(pieces[0], next);

        parent.removeChild(node);
        for (let i = 1; i < pieces.length - 1; i++) {
          parent.insertBefore(pieces[i], next);
        }

        if (
          pieces[pieces.length - 1].nodeType === 3 &&
          utils.isDefined(next) &&
          next.nodeType === 3
        ) {
          parent.replaceChild(
            document.createTextNode(pieces[pieces.length - 1].data + next.data),
            next
          );
        } else if (
          isLabel(pieces[pieces.length - 1]) &&
          isLabel(next) &&
          pieces[pieces.length - 1].getAttribute("data-i") ==
            next.getAttribute("data-i")
        ) {
          mergeDisjoint(pieces[pieces.length - 1], next);
        } else {
          parent.insertBefore(pieces[pieces.length - 1], next);
        }
      } else if (pieces.length === 1) {
        // if it's only one piece, then it's guaranteed to be a text node
        if (next != null) {
          if (prev == null) {
            if (next.nodeType === 3) {
              parent.replaceChild(
                document.createTextNode(pieces[0].data + next.data),
                next
              );
            } else if (next.nodeType === 1) {
              parent.insertBefore(pieces[0], next);
            }
          } else {
            if (prev.nodeType === 1) {
              // previous is an Element node
              if (next.nodeType === 3) {
                parent.replaceChild(
                  document.createTextNode(pieces[0].data + next.data),
                  next
                );
              } else if (next.nodeType === 1) {
                parent.insertBefore(pieces[0], next);
              }
            } else if (prev.nodeType === 3) {
              // previous is a Text node
              if (next.nodeType === 3) {
                // next is also a Text node
                parent.replaceChild(
                  document.createTextNode(
                    prev.data + pieces[0].data + next.data
                  ),
                  prev
                );
                if (utils.isDefined(next) && !isDeleteButton(next))
                  parent.removeChild(next);
              } else if (next.nodeType === 1) {
                parent.insertBefore(pieces[0], next);
              }
            }
          }
        }

        parent.removeChild(node);
      }
    }

    // checks if a chunk is in any of the relations
    function isInRelations(c) {
      for (let key in relations) {
        let links = relations[key]["links"];
        for (let i = 0, len = links.length; i < len; i++) {
          if (links[i].s == c.id || links[i].t == c.id) return key;
        }
      }
      return false;
    }

    function initContextMenu(markedSpan, plugins) {
      function createButton(plugin) {
        if (plugin.isAllowed(markedSpan)) {
          let btn = document.createElement("button");
          btn.className =
            "button is-primary is-small is-fullwidth is-rounded is-outlined mb-1";
          btn.textContent = plugin.verboseName;
          plugin.exec(markedSpan, btn);

          if (plugin.subscribe) {
            // TODO: we dispatch event from the document whenever any relation change is occuring
            //       then we catching it here, but it gets overriden for every new markedSpan
            plugin.subscribe.forEach(function (event) {
              markedSpan.addEventListener(
                event,
                function (e) {
                  (function (b) {
                    if (plugin.isAllowed(e.target)) {
                      plugin.exec(e.target, b);
                      b.classList.remove("is-hidden");
                    } else {
                      b.classList.add("is-hidden");
                    }
                  })(btn);
                },
                false
              );
            });
          }
          return btn;
        } else {
          return null;
        }
      }

      if (
        Object.values(plugins)
          .map(function (x) {
            return Object.keys(x).length;
          })
          .reduce(function (a, b) {
            return a + b;
          }, 0) > 0
      ) {
        let code = markedSpan.getAttribute("data-s");
        let short = code.substring(0, code.lastIndexOf("_"));
        let div = document.createElement("div");
        let subset = Object.assign({}, plugins[short], plugins[undefined]);

        for (let k in plugins["sharedBetweenMarkers"]) {
          subset[k] = plugins["sharedBetweenMarkers"][k];
        }

        if (Object.keys(subset).length === 0) return;

        let keys = Object.keys(subset);
        keys.sort(function (x, y) {
          if (subset[x].verboseName < subset[y].verboseName) return -1;
          else if (subset[x].verboseName > subset[y].verboseName) return 1;
          else return 0;
        });

        for (let name in keys) {
          let btn = createButton(subset[keys[name]]);
          if (btn != null) div.appendChild(btn);
        }
        div.lastChild.classList.remove("mb-1");

        const instance = tippy(markedSpan, {
          content: div,
          interactive: true,
          trigger: "manual",
          placement: "bottom",
          theme: "translucent",
        });

        markedSpan.addEventListener("contextmenu", function (event) {
          event.preventDefault();
          event.stopPropagation();
          let targetRect = event.target.getBoundingClientRect();

          instance.setProps({
            getReferenceClientRect: function () {
              let half = (targetRect.right - targetRect.left) / 2;
              return {
                width: 0,
                height: 0,
                top: targetRect.bottom,
                bottom: targetRect.bottom,
                left: targetRect.left + half,
                right: targetRect.left + half,
              };
            },
          });

          instance.show();
        });
      }
    }

    function countChunksByType() {
      let cnt = {};
      for (let c in chunks) {
        let chunk = chunks[c];
        if (
          !chunk.hasOwnProperty("batch") &&
          !chunk.submittable &&
          !isInRelations(chunk)
        ) {
          if (cnt.hasOwnProperty(chunk.label)) cnt[chunk.label]++;
          else cnt[chunk.label] = 1;
        }
      }
      return cnt;
    }

    // Adapted rom https://benclinkinbeard.com/d3tips/make-any-chart-responsive-with-one-function/
    function responsifySVG(svg) {
      // container will be the DOM element
      // that the svg is appended to
      // we then measure the container
      // and find its aspect ratio
      const container = d3.select(svg.node().parentNode),
        width = parseInt(svg.style("width"), 10),
        height = parseInt(svg.style("height"), 10),
        aspect = width / height;

      // set viewBox attribute to the initial size
      // control scaling with preserveAspectRatio
      // resize svg on inital page load
      svg
        .attr("viewBox", `0 0 ${width} ${height}`)
        .attr("preserveAspectRatio", "xMinYMid")
        .call(resize);

      // add a listener so the chart will be resized
      // when the window resizes
      // multiple listeners for the same event type
      // requires a namespace, i.e., 'click.foo'
      // api docs: https://goo.gl/F3ZCFr
      d3.select(window).on("resize." + container.attr("id"), resize);

      // this is the code that resizes the chart
      // it will be called on load
      // and in response to window resizes
      // gets the width of the container
      // and resizes the svg to fill it
      // while maintaining a consistent aspect ratio
      function resize() {
        const w = parseInt(container.style("width"), 10);
        svg.attr("width", w);
        svg.attr("height", Math.round(w / aspect));
      }
    }

    function getLabelText(obj) {
      let relLabels = {};
      let relIds = obj.querySelectorAll('span[data-m="r"]');
      let relSpan;
      for (let i = 0, len = relIds.length; i < len; i++) {
        relSpan = relIds[i];
        relLabels[relSpan.parentNode.id] = relSpan.textContent;
        relSpan.textContent = "";
      }
      let text = obj.textContent;
      for (let i = 0, len = relIds.length; i < len; i++) {
        relSpan.textContent = relLabels[relIds[i].parentNode.id];
      }
      return text;
    }

    function createMarkedSpan(obj, displayType) {
      let color = obj.getAttribute("data-color"),
        textColor = obj.getAttribute("data-text-color"),
        markedSpan = document.createElement("span");
      markedSpan.className = "tag";
      markedSpan.setAttribute("data-s", obj.getAttribute("data-s"));
      markedSpan.setAttribute("data-scope", obj.getAttribute("data-scope"));
      markedSpan.setAttribute("data-dt", displayType);
      if (displayType == "hl") {
        markedSpan.setAttribute(
          "style",
          "background-color:" + color + "; color:" + textColor + ";"
        );
      } else if (displayType == "und") {
        markedSpan.setAttribute(
          "style",
          "text-decoration: underline 2px " +
            color +
            "; padding-left: 0px; border: 0px; background-color: transparent;"
        );
      }
      return markedSpan;
    }

    function checkForMultiplePossibleRelations(relationsArea, relCode) {
      let relBetween = relationsArea.querySelectorAll("[data-b]"),
        numRelations = Array.from(relBetween)
          .map((x) => x.getAttribute("data-b").indexOf(relCode) > -1)
          .reduce((x, y) => x + y);
      return numRelations > 1;
    }

    function createRelationSwitcher(relationIds) {
      let btns = document.createElement("div");
      btns.className = "buttons are-small";

      for (let i = 0, len = relationIds.length; i < len; i++) {
        let btn = document.createElement("button");
        btn.className = "button";
        btn.setAttribute("data-rel", relationIds[i]);
        btn.textContent = relationIds[i];
        btns.appendChild(btn);
      }
      return btns;
    }

    function getRadioButtonValue(rb) {
      let retval = rb.value;
      if (rb.name.endsWith("_ocat")) retval += RADIO_CHECK_SEPARATOR;
      return retval;
    }

    function findStartNode(node) {
      let startNode = node.nextSibling;
      if (!utils.isDefined(startNode)) return null;

      if (startNode.nodeType === 1) {
        startNode = startNode.childNodes[0];
        if (!utils.isDefined(startNode)) return null;

        while (startNode.nodeType !== 3 || startNode.textContent.length === 0) {
          if (!utils.isDefined(startNode.nextSibling))
            return findStartNode(startNode.parentNode.childNodes[0]);
          startNode = startNode.nextSibling;
        }
        return startNode;
      } else if (startNode.nodeType === 3) {
        return startNode;
      } else {
        return null;
      }
    }

    function findEndNode(node, nodeText) {
      if (!utils.isDefined(node)) return null;

      if (!utils.isDefined(nodeText)) nodeText = node.textContent;

      if (node.parentNode.textContent == nodeText)
        return findEndNode(node.parentNode, nodeText);
      else return node;
    }

    const ui = {
      collapsibles: null,
      extraElementsVisible: true,
      getClosestBatch: getClosestBatch,
      initCollapsibles: function () {
        if (!utils.isDefined(this.collapsibles)) {
          const collapsibles = bulmaCollapsible.attach();
          this.collapsibles = collapsibles;
        }

        this.collapsibles.forEach(function (instance) {
          instance.on("after:expand", function () {
            // bug fix
            instance._originalHeight = instance.element.scrollHeight + "px";
          });
          instance.on("after:collapse", function () {
            // TODO: this is a bit of a hack, figure out why this hack is needed
            let i = 0;
            let handle = setInterval(function () {
              labeler.fixUI();
              i++;
              if (i == 2) {
                clearInterval(handle);
              }
            }, 200);
          });
        });
      },
    };

    const labeler = {
      allowSelectingLabels: false,
      diisableSubmittedLabels: false,
      drawingType: {},
      ui: ui,
      initLineHeight: undefined,
      taskArea: null,
      textLabelsArea: null,
      markersArea: null,
      selectorArea: null, // the area where the article is
      interactiveDataArea: null,
      markerGroupsArea: null,
      submitForm: null,
      contextMenuPlugins: { sharedBetweenMarkers: {} },
      checkedOuterRadio: {}, // to keep tracked of nested radio button groups
      checkedInnerRadio: {},
      currentPage: {
        editing: null,
        reviewing: null,
      },
      radioCheckSeparator: RADIO_CHECK_SEPARATOR,
      isMarker: isMarker,
      isLabel: isLabel,
      init: function () {
        this.taskArea = document.querySelector("#taskArea");
        this.markersArea = this.taskArea.querySelector("#markersArea");
        this.markerGroupsArea =
          this.taskArea.querySelector("#markerGroupsArea");
        this.relationsArea = this.taskArea.querySelector("#relationsArea");
        this.textArea = this.taskArea.querySelector("#textArea");
        this.actionsArea = this.taskArea.querySelector("#actionsArea");
        this.selectorArea = this.textArea.querySelector("#selector");
        this.textLabelsArea = this.taskArea.querySelector("#textLabels");
        this.interactiveDataArea = document.querySelector(
          "textarea#interactiveDataArea"
        );
        resetTextHTML =
          this.selectorArea == null ? "" : this.selectorArea.innerHTML;
        resetText = this.getContextText(true);
        this.allowSelectingLabels =
          this.markersArea == null
            ? false
            : this.markersArea.getAttribute("data-select") == "true";
        this.disableSubmittedLabels =
          this.markersArea == null
            ? false
            : this.markersArea.getAttribute("data-disable") == "true";
        let repr = document.querySelector("#relationRepr");
        if (utils.isDefined(repr))
          this.drawingType = JSON.parse(repr.textContent);
        if (utils.isDefined(this.actionsArea))
          this.submitForm = this.actionsArea.querySelector("#inputForm");
        if (utils.isDefined(this.relationsArea)) this.initSvg();
        this.initEvents();
        this.updateMarkAllCheckboxes();
        this.fixUI();
      },
      fixUI: function () {
        [this.markersArea, this.markerGroupsArea].forEach(function (area) {
          if (utils.isDefined(area)) {
            $(area)
              .find(".control.has-tag-left")
              .each(function (i, x) {
                let $input = $(x).find("input"),
                  $tag = $(x).find("span.tag");

                if ($input.length) {
                  $input.css("padding-left", $tag.outerWidth() + 20);
                }
              });
          }
        });

        let viewPortHeight = window.innerHeight;

        if (
          utils.isDefined(this.markersArea) &&
          utils.isDefined(this.actionsArea) &&
          this.markersArea.nextElementSibling == this.actionsArea
        ) {
          this.markersArea.style.height =
            viewPortHeight - this.markersArea.offsetTop - 80 + "px";
          let markersAreaBody = this.markersArea.querySelector(".message-body");
          markersAreaBody.style.maxHeight =
            viewPortHeight - this.markersArea.offsetTop - 140 + "px";
        }

        if (this.interactiveDataArea == null) {
          this.textArea.style.height =
            viewPortHeight - this.textArea.offsetTop - 80 + "px";
        } else {
          this.textArea.style.height =
            viewPortHeight -
            this.textArea.offsetTop -
            this.interactiveDataArea.clientHeight -
            100 +
            "px";
        }
      },
      getContextText: function (forPresentation) {
        if (forPresentation === undefined) {
          forPresentation = true;
        }

        showExtraElements(this.selectorArea, false);
        let ct = "";
        if (utils.isDefined(this.selectorArea)) {
          let scrollable = this.selectorArea.querySelector(".scrollable");
          let hasScrollable = utils.isDefined(scrollable);
          if (forPresentation) {
            ct = (
              hasScrollable ? scrollable : this.selectorArea
            ).innerText.trim();
          } else {
            ct = (
              hasScrollable ? scrollable : this.selectorArea
            ).textContent.trim();
          }
        }
        showExtraElements(this.selectorArea, true);
        return ct;
      },
      initTextAreaEvents: function () {
        let control = this;
        this.textArea.addEventListener(
          "click",
          function (e) {
            e.stopPropagation();
            let target = e.target;
            if (isDeleteButton(target)) {
              control.labelDeleteHandler(e);
              control.updateMarkAllCheckboxes();
            } else if (isLabel(target)) {
              if (control.allowSelectingLabels) {
                let $target = $(target);
                if (
                  $target.prop("in_relation") &&
                  !$target.prop("multiple_possible_relations")
                ) {
                  control.showRelationGraph(
                    parseInt(
                      target.querySelector('[data-m="r"]').textContent,
                      10
                    )
                  );
                } else if (!window.getSelection().toString()) {
                  if (
                    target.classList.contains("active") &&
                    $target.prop("selected")
                  ) {
                    target.classList.remove("active");
                    $target.prop("selected", false);
                    $target.prop("ts", null);
                  } else {
                    target.classList.add("active");
                    $target.prop("ts", Date.now());
                    $target.prop("selected", true);
                  }
                }
              }
            } else if (target.hasAttribute("data-rel")) {
              control.showRelationGraph(
                parseInt(target.getAttribute("data-rel"), 10)
              );
            }
          },
          false
        );
      },
      initSelectorAreaEvents: function () {
        this.selectorArea.addEventListener(
          "mouseover",
          function (e) {
            let target = e.target;
            if (isLabel(target)) {
              if (labelerModule.allowSelectingLabels) {
                e.stopPropagation();
                if (target.classList.contains("tag"))
                  if (!$(target).prop("selected")) {
                    target.classList.add("active");
                    $(
                      '[data-i="' + target.getAttribute("data-i") + '"]'
                    ).addClass("active");
                  } else if (!$(target.parentNode).prop("selected")) {
                    target.parentNode.classList.add("active");
                    $(
                      '[data-i="' +
                        target.parentNode.getAttribute("data-i") +
                        '"]'
                    ).addClass("active");
                  }
              }
            }
          },
          false
        );

        this.selectorArea.addEventListener(
          "mouseout",
          function (e) {
            let target = e.target;
            if (isLabel(target)) {
              if (labelerModule.allowSelectingLabels) {
                e.stopPropagation();
                if (target.classList.contains("tag"))
                  if (!$(target).prop("selected")) {
                    target.classList.remove("active");
                    $(
                      '[data-i="' + target.getAttribute("data-i") + '"]'
                    ).removeClass("active");
                  } else if (!$(target.parentNode).prop("selected")) {
                    target.parentNode.classList.remove("active");
                    $(
                      '[data-i="' +
                        target.parentNode.getAttribute("data-i") +
                        '"]'
                    ).removeClass("active");
                  }
              }
            }
          },
          false
        );

        // adding chunk if a piece of text was selected with a mouse
        this.selectorArea.addEventListener(
          "mouseup",
          function (e) {
            let isRightMB;
            e = e || window.event;

            if ("which" in e)
              // Gecko (Firefox), WebKit (Safari/Chrome) & Opera
              isRightMB = e.which === 3;
            else if ("button" in e)
              // IE, Opera
              isRightMB = e.button === 2;

            if (!isRightMB) {
              labelerModule.updateChunkFromSelection();
            }
          },
          false
        );
      },
      initMarkerAreaOnClick: function () {
        let control = this;
        this.markersArea.addEventListener(
          "click",
          function (e) {
            let target = e.target;
            if (target.nodeName != "INPUT") {
              let marker = getClosestMarker(target);

              if (utils.isDefined(marker)) {
                if (marker.getAttribute("data-scope") == "span") {
                  let mmpi = control.markersArea.getAttribute("data-mmpi");
                  control.mark(marker, mmpi);
                  control.updateMarkAllCheckboxes();
                } else if (marker.getAttribute("data-scope") == "text") {
                  control.select(marker);
                }
              }
            } else if (target.getAttribute("type") == "radio") {
              if (!target.hasAttribute("required")) {
                let memoryInnerRb = control.checkedInnerRadio[target.name];
                if (utils.isDefined(memoryInnerRb) && memoryInnerRb.checked) {
                  memoryInnerRb.checked = false;

                  if (target.hasAttribute("data-group")) {
                    let outerRadio = control.markersArea.querySelector(
                      "#" + target.getAttribute("data-group")
                    );

                    // this will fire only when target.checked is true
                    outerRadio.checked = memoryInnerRb.checked;
                    delete control.checkedOuterRadio[outerRadio.name];
                  }
                  delete control.checkedInnerRadio[target.name];
                }

                let memoryOuterRb = control.checkedOuterRadio[target.name];
                if (utils.isDefined(memoryOuterRb) && memoryOuterRb.checked) {
                  memoryOuterRb.checked = false;

                  if (target.hasAttribute("data-for")) {
                    let radioFor = target.getAttribute("data-for");

                    if (utils.isDefined(control.checkedInnerRadio[radioFor])) {
                      control.checkedInnerRadio[radioFor].checked = false;
                      delete control.checkedInnerRadio[radioFor];
                    }
                  }
                  delete control.checkedOuterRadio[target.name];
                }
              }
            }
          },
          false
        );
      },
      initMarkerAreaOnChange: function () {
        let control = this;
        this.markersArea.addEventListener(
          "change",
          function (e) {
            e.stopPropagation();
            let target = e.target;
            if (target.getAttribute("type") == "checkbox") {
              let marker = getClosestMarker(target);
              if (utils.isDefined(marker)) {
                control.selectorArea
                  .querySelectorAll(
                    '[data-s="' + marker.getAttribute("data-s") + '"]'
                  )
                  .forEach(function (x) {
                    let $x = $(x);
                    if (!$x.prop("in_relation") && !$x.prop("disabled")) {
                      if (
                        !target.checked &&
                        x.classList.contains("active") &&
                        $x.prop("selected")
                      ) {
                        x.classList.remove("active");
                        $x.prop("selected", false);
                      } else if (target.checked) {
                        x.classList.add("active");
                        $x.prop("selected", true);
                      }
                    }
                  });
              }
            } else if (target.getAttribute("type") == "radio") {
              if (target.hasAttribute("data-for")) {
                let radioFor = target.getAttribute("data-for");
                let previousRadio = control.checkedOuterRadio[radioFor];
                if (utils.isDefined(previousRadio) && previousRadio != target) {
                  // grab old outer checkbox and uncheck it
                  previousRadio.checked = false;
                }
                // assign new outer checkbox
                control.checkedOuterRadio[radioFor] = target;

                if (utils.isDefined(control.checkedInnerRadio[radioFor])) {
                  control.checkedInnerRadio[radioFor].checked = false;
                }
                // this is to track unchecking
                control.checkedOuterRadio[target.name] = target;
              } else if (target.hasAttribute("data-group")) {
                let outerRadio = control.markersArea.querySelector(
                  "#" + target.getAttribute("data-group")
                );

                // this will fire only when target.checked is true
                outerRadio.checked = target.checked;
                control.checkedOuterRadio[target.name] = outerRadio;
                control.checkedInnerRadio[target.name] = target;

                // this is to track unchecking
                control.checkedOuterRadio[outerRadio.name] = outerRadio;
              } else {
                control.checkedInnerRadio[target.name] = target;
              }
            }
          },
          false
        );
      },
      initMarkerAreaKeyboardEvents: function () {
        // TODO: might be potentially rewritten?
        // adding chunk if a piece of text was selected with a keyboard
        let control = this;
        document.addEventListener(
          "keyup",
          function (e) {
            let target = e.target;

            if (target.id == "goToPage" && e.keyCode == 13) {
              document.querySelector('[data-page="#goToPage"]').click();
              return;
            }

            let selection = window.getSelection();

            if (selection && selection.anchorNode != null) {
              let isArticleAncestor = isAncestor(
                selection.anchorNode,
                control.selectorArea
              );

              if (
                e.shiftKey &&
                e.which >= 37 &&
                e.which <= 40 &&
                isArticleAncestor
              ) {
                labelerModule.updateChunkFromSelection();
              }
            }
            let s = String.fromCharCode(e.which).toUpperCase();
            let shortcut = null;
            if (s.trim()) {
              if (e.shiftKey) {
                shortcut = document.querySelector(
                  '[data-shortcut="SHIFT + ' + s + '"]'
                );
              } else {
                shortcut = document.querySelector(
                  '[data-shortcut="' + s + '"]'
                );
              }
            }

            if (shortcut != null) {
              if (e.altKey && !e.shiftKey && !e.ctrlKey) {
                let input = shortcut.querySelector('input[type="checkbox"]');
                if (utils.isDefined(input)) {
                  input.checked = !input.checked;
                  const event = new Event("change", { bubbles: true });
                  input.dispatchEvent(event);
                }
              } else {
                shortcut.click();
              }
            }
          },
          false
        );
      },
      initMarkerAreaEvents: function () {
        if (utils.isDefined(this.markersArea)) {
          this.initMarkerAreaOnClick();
          this.initMarkerAreaOnChange();
          this.initMarkerAreaKeyboardEvents();
        }
      },
      initRelationAreaEvents: function () {
        if (utils.isDefined(this.relationsArea)) {
          let control = this;
          this.relationsArea.addEventListener(
            "click",
            function (e) {
              let relMarker = getClosestRelation(e.target);

              if (utils.isDefined(relMarker)) control.markRelation(relMarker);
            },
            false
          );
        }
      },
      initEditingAndReviewingEvents: function () {
        let control = this;
        // editing & reviewing mode events
        document.addEventListener(
          "submit",
          function (e) {
            e.preventDefault();

            let $form = $(e.target);
            let data = $form.serializeObjectLists();
            if (data.hasOwnProperty("random"))
              data["random"] = data["random"][0];

            let $main = $form.closest("nav").siblings("main");
            $main.empty();
            $main.append(
              $(
                '<div class="lds-ring"><div></div><div></div><div></div><div></div></div>'
              )
            );
            $main.addClass("has-text-centered");

            if ($form.attr("id") == "editingSearchForm") {
              e.preventDefault();
              $.ajax({
                method: $form.method,
                url: $form.attr("action"),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                data: data,
                success: function (data) {
                  let $editingBoard = $("#editingBoard");
                  let $main = $editingBoard.find("main");
                  $main.prop("innerHTML", data.template);
                  $main.removeClass("has-text-centered");
                  $editingBoard.attr("data-href", $form.attr("action"));
                  labelerModule.fixUI();
                },
              });
            }
          },
          false
        );

        document.addEventListener("click", function (e) {
          let target = e.target,
            closestBatch = getClosestBatch(target),
            closestPsArea = getClosestPostSubmitArea(target);

          if (target.tagName == "I") {
            target = target.parentNode;
            if (target.classList.contains("icon")) {
              target = target.parentNode;
            }
          }

          if (target.tagName == "A") {
            e.preventDefault();
            e.stopPropagation();
            if (target.id == "addSearchClause") {
              let esClauseTemplate = document.querySelector(
                "#editingSearchClauseTemplate .field"
              );
              let clone = esClauseTemplate.cloneNode(true);
              let settings = document.querySelector("#searchSettings form");
              let submitSearchButton = settings.querySelector(
                'input[type="submit"]'
              );
              settings.insertBefore(clone, submitSearchButton.parentNode);

              if (utils.isDefined(control.ui.collapsibles)) {
                control.ui.collapsibles.forEach(function (instance) {
                  // bug fix
                  instance._originalHeight =
                    instance.element.scrollHeight + "px";
                  instance.collapse();
                  instance.expand();
                });
              }
            } else if (target.getAttribute("data-action") == "removeClause") {
              let fieldDiv = getClosestFormField(target);
              if (utils.isDefined(fieldDiv)) fieldDiv.remove();
            } else if (target.hasAttribute("data-page")) {
              // pagination events
              let mode = closestPsArea.getAttribute("data-mode");
              let searchForm = closestPsArea.querySelector(
                  "#" + mode + "SearchForm"
                ),
                searchData = {};
              let page = target.getAttribute("data-page");
              if (utils.isDefined(searchForm))
                searchData = $(searchForm).serializeObjectLists();

              if (page == "#goToPage")
                page = document.querySelector(page).value;

              $.ajax({
                type: "GET",
                url: closestPsArea.getAttribute("data-href") + "?p=" + page,
                dataType: "json",
                data: searchData,
                success: function (d) {
                  control.currentPage[mode] = page;
                  if (d.partial) {
                    let mainPart = closestPsArea.querySelector("main");
                    mainPart.innerHTML = d.template;
                  } else {
                    closestPsArea.outerHTML = d.template;
                  }

                  control.fixUI();
                  control.ui.collapsibles = null;
                  control.ui.initCollapsibles();
                },
                error: function () {
                  console.log("Error while invoking editing mode!");
                },
              });
            }
          } else if (utils.isDefined(closestBatch)) {
            // clicked on one of the batches
            let uuid = closestBatch.getAttribute("data-id"),
              $psArea = $(closestPsArea),
              $closestBatch = $(closestBatch);

            let purposeNode;

            if (isBatch(target)) {
              purposeNode = target.querySelector("[data-purpose]");
            } else {
              purposeNode = getClosestPurposeNode(target);
            }

            if (utils.isDefined(purposeNode)) {
              let purpose = purposeNode.getAttribute("data-purpose");
              if (purpose === "s") {
                // show batch
                let url = $psArea.attr("data-url"),
                  $list = $('[id*="Board"] li'),
                  clickedOnCurrent =
                    $closestBatch.data("restored") !== undefined &&
                    $closestBatch.data("restored");

                $list.find('[data-purpose="s"]').removeClass("is-hovered");
                if (clickedOnCurrent) {
                  $closestBatch.data("restored", false);
                  control.restoreOriginal();
                  control.clearBatch();
                } else {
                  purposeNode.classList.add("is-hovered");
                  $list.each(
                    (i, n) =>
                      void (
                        $(n).data("restored") !== undefined &&
                        $(n).data("restored", false)
                      )
                  );
                  // The code above is a shorthand for this code below. Note that `void` is necessary to force expression to be evaluated
                  // and return `undefined` at the end.
                  // $list.each(function(i, n) {
                  //   if ($(n).data('restored') !== undefined) {
                  //     $(n).data('restored', false);
                  //   }
                  // });
                  if (utils.isDefined(uuid) && utils.isDefined(url)) {
                    control.restoreBatch(uuid, url);
                  }
                  $closestBatch.data("restored", true);
                }
              } else if (purpose === "f") {
                // flag a batch as problematic
                let url = $psArea.attr("data-flag-url"),
                  csrf = purposeNode.querySelector(
                    'input[name="csrfmiddlewaretoken"]'
                  ),
                  batchButton =
                    closestBatch.querySelector('[data-purpose="s"]');

                if (closestBatch.hasAttribute("data-flagged")) {
                  if (closestBatch.getAttribute("data-flagged") == "true") {
                    // unflag
                    if (utils.isDefined(uuid) && utils.isDefined(url)) {
                      control.changeBatchFlag(
                        uuid,
                        url,
                        false,
                        csrf.value,
                        function () {
                          batchButton.classList.remove("is-danger");
                          if (
                            closestPsArea.getAttribute("data-mode") == "editing"
                          )
                            batchButton.classList.add("is-link");
                          else if (
                            closestPsArea.getAttribute("data-mode") ==
                            "reviewing"
                          )
                            batchButton.classList.add("is-dark");
                          closestBatch.setAttribute("data-flagged", false);
                          purposeNode.classList.remove("is-active");
                        }
                      );
                    }
                  } else {
                    // flag!!!
                    if (utils.isDefined(uuid) && utils.isDefined(url)) {
                      control.changeBatchFlag(
                        uuid,
                        url,
                        true,
                        csrf.value,
                        function () {
                          batchButton.classList.add("is-danger");
                          if (
                            closestPsArea.getAttribute("data-mode") == "editing"
                          )
                            batchButton.classList.remove("is-link");
                          else if (
                            closestPsArea.getAttribute("data-mode") ==
                            "reviewing"
                          )
                            batchButton.classList.remove("is-dark");
                          closestBatch.setAttribute("data-flagged", true);
                          purposeNode.classList.add("is-active");
                        }
                      );
                    }
                  }
                }
              }
            }
          }
        });

        document.addEventListener("change", function (e) {
          let target = e.target;
        });
      },
      initInteractiveDataAreaEvents: function () {
        if (this.interactiveDataArea != null) {
          let control = this;
          this.interactiveDataArea.addEventListener("input", function (e) {
            let target = e.target;
            control.selectorArea.innerHTML = target.value.replace(
              /\n/gi,
              "<br>"
            );

            if (target.value.length === 0) {
              control.selectorArea.innerHTML = "No input";
            }
            control.restart();
          });
        }
      },
      initEvents: function () {
        // event delegation
        if (this.selectorArea != null) {
          let control = this;

          this.initTextAreaEvents();

          let deselectActionBtn;
          if (utils.isDefined(this.actionsArea))
            deselectActionBtn = this.actionsArea.querySelector(
              "#deselectAllMarkers"
            );

          if (utils.isDefined(deselectActionBtn))
            deselectActionBtn.addEventListener("click", function () {
              control.textArea
                .querySelectorAll(LABEL_CSS_SELECTOR)
                .forEach((x) => x.classList.remove("active"));
            });

          this.initSelectorAreaEvents();

          this.initMarkerAreaEvents();
          this.initRelationAreaEvents();

          this.initEditingAndReviewingEvents();
          this.initInteractiveDataAreaEvents();
        }
      },
      register: function (plugin, label) {
        let p = Object.assign({}, plugin);
        delete p.name;
        if (!(label in this.contextMenuPlugins))
          this.contextMenuPlugins[label] = {};
        if (plugin.storeFor == "relation") {
          if (
            !this.contextMenuPlugins["sharedBetweenMarkers"].hasOwnProperty(
              plugin.name
            )
          )
            this.contextMenuPlugins["sharedBetweenMarkers"][plugin.name] = p;
        } else {
          this.contextMenuPlugins[label][plugin.name] = p;
        }

        if (Object.keys(p.dispatch).length > 0) {
          for (let catchEvent in p.dispatch) {
            document.addEventListener(
              catchEvent,
              function (e) {
                if (Array.isArray(p.dispatch[catchEvent])) {
                  p.dispatch[catchEvent].forEach(function (de) {
                    const event = new CustomEvent(de, { detail: e.detail });
                    // select all labels and dispatch events
                    document.querySelectorAll("span.tag").forEach(function (x) {
                      x.dispatchEvent(event);
                    });
                  });
                } else {
                  const event = new CustomEvent(p.dispatch[catchEvent]);
                  // select all labels and dispatch events
                  document.querySelectorAll("span.tag").forEach(function (x) {
                    x.dispatchEvent(event);
                  });
                }
              },
              false
            );
          }
        }
        pluginsToRegister--;

        if (pluginsToRegister <= 0) {
          this.initPreMarkers();
          this.updateMarkAllCheckboxes();
        }
      },
      expectToRegister: function () {
        pluginsToRegister++;
      },
      disableChunk: function (c) {
        let $el = $('span.tag[data-i="' + c["id"] + '"]');
        $el.removeAttr("data-i");
        $el.addClass("is-disabled");
        $el.prop("disabled", true);
        $el.find('span[data-m="r"]').remove();
      },
      disableTextLabels: function () {
        this.textLabelsArea
          .querySelectorAll("span.tag:not(.is-disabled)")
          .forEach(function (x) {
            x.querySelector("button.delete").remove();
            x.classList.add("is-disabled");
          });
      },
      enableChunk: function (c) {
        let $el = $('span.tag[data-i="' + c["id"] + '"]');
        $el.removeClass("is-disabled");
        $el.prop("in_relation", false);
        $el.prop("disabled", false);
      },
      disableChunks: function (chunksList) {
        // disable given chunks visually
        for (let c in chunksList) {
          this.disableChunk(chunksList[c]);
        }
        return chunksList;
      },
      getActiveChunk: function () {
        return chunks[chunks.length - 1];
      },
      removeActiveChunk: function () {
        if (!chunks[chunks.length - 1]["marked"]) chunks.pop();
      },
      // initialize pre-markers, i.e. mark the specified words with a pre-specified marker
      initPreMarkers: function () {
        labelId = 0;
        let control = this;
        $("article.text span.tag").each(function (i, node) {
          node.setAttribute("data-i", labelId);
          control.updateChunkFromNode(node);
          initContextMenu(node, control.contextMenuPlugins);
          labelId++;
        });
        activeLabels = labelId;
      },
      updateChunkFromNode: function (node) {
        // adding the information about the node, representing a label, to the chunks array
        let chunk = {},
          marker = document.querySelector(
            'div.marker.tags[data-s="' + node.getAttribute("data-s") + '"]'
          );
        //markerText = marker.querySelector("span.tag:first-child");
        chunk["lengthBefore"] = 0;
        chunk["marked"] = true;
        chunk["id"] = labelId;
        chunk["label"] = node.getAttribute("data-s");
        chunk["submittable"] = true; // whether it is possible to submit
        chunk["independent"] = marker.getAttribute("data-indep") === "true";
        chunk["start"] = previousTextLength(node, false);
        chunk["end"] = chunk["start"] + getNodeLength(node);
        chunks.push(chunk);
      },
      updateChunkFromSelection: function () {
        // getting a chunk from the selection; the chunk then either is being added to the chunks array, if the last chunk was submitted
        // or replaces the last chunk if the last chunk was not submitted
        let selection = window.getSelection();

        if (selection && !selection.isCollapsed) {
          // group selections:
          //  - a label spanning other labels is selected, they should end up in the same group
          //  - two disjoint spans of text are selected, they should end up in separate groups (possible only in Firefox)
          let groups = [],
            group = [];
          let firstRange = selection.getRangeAt(0);
          let skipFirst =
            firstRange.startContainer == firstRange.endContainer &&
            firstRange.startContainer.textContent.length == 0;
          if (!skipFirst) group.push(firstRange);
          for (let i = 1; i < selection.rangeCount; i++) {
            let last = group[group.length - 1],
              cand = selection.getRangeAt(i);

            if (cand.collapsed) continue;

            if (
              cand.endContainer.textContent.length == 0 &&
              cand.startContainer.textContent.length == 0
            )
              continue;

            // NOTE:
            // - can't use `cand.compareBoundaryPoints(Range.END_TO_START, last)` because of delete buttons in the labels
            if (
              last.endContainer.nextSibling == cand.startContainer ||
              last.endContainer.parentNode.nextSibling == cand.startContainer
            ) {
              group.push(cand);
            } else {
              groups.push(group);
              group = [cand];
            }
          }

          if (group) groups.push(group);

          for (let i = 0; i < groups.length; i++) {
            let chunk = {},
              group = groups[i];

            group = group.filter(function (x) {
              return !x.collapsed;
            });
            let N = group.length;

            if (N == 0) continue;

            /*
             * From MDN (https://developer.mozilla.org/en-US/docs/Web/API/Range/startOffset)
             * If the startContainer is a Node of type Text, Comment, or CDATASection,
             * then the offset is the number of characters from the start of the startContainer
             * to the boundary point of the Range. For other Node types, the startOffset is
             * the number of child nodes between the start of the startContainer and the
             * boundary point of the Range
             *
             * The same is true for endContainer and endOffset
             *
             * Also from MDN
             * (https://developer.mozilla.org/en-US/docs/Web/API/range/commonAncestorContainer)
             * The Range.commonAncestorContainer read-only property returns the deepest —
             * or furthest down the document tree — Node that contains both boundary points
             * of the Range. This means that if Range.startContainer and Range.endContainer
             * both refer to the same node, this node is the common ancestor container.
             */
            if (group[0].startContainer.nodeType === 1) {
              // means startContainer is an element node and then its startOffset is the number of child nodes
              let startOffset = group[0].startOffset;
              let startNode = group[0].startContainer.childNodes[startOffset];

              if (startNode.tagName == "BR") {
                // this is the end of the paragraph, so select the previous node as end container
                // and set offset to be its length
                if (
                  startOffset + 1 <
                  group[0].startContainer.childNodes.length
                ) {
                  startNode =
                    group[0].startContainer.childNodes[startOffset + 1];
                  group[0].setStart(startNode, 0);
                } else {
                  startNode = group[0].startContainer.nextSibling;
                  if (!utils.isDefined(startNode)) continue;
                }
              }
            } else if (group[0].startContainer.nodeType === 3) {
              // means it's a text node, so the offset is the number of chars
              let startOffset = group[0].startOffset;
              let startContLength = getNodeLength(group[0].startContainer);

              if (startOffset == startContLength) {
                let startNode = findStartNode(group[0].startContainer);
                if (utils.isDefined(startNode) && startNode.nodeType !== 3)
                  group[0].setStart(startNode, 0);
              }
            }

            if (group[0].endContainer.nodeType === 1) {
              let endOffset = group[0].endOffset;
              let endNode = group[0].endContainer.childNodes[endOffset];
              let startOffset = group[0].startOffset;
              let startContLength = getNodeLength(group[0].startContainer);

              if (isDeleteButton(endNode) && startOffset == startContLength) {
                // effectively collapsed selection, because it starts at the end of the
                // text node of the marker and ends at it delete button
                group.shift();
                N--;
              }
            }

            if (group[N - 1].endContainer.nodeType === 1) {
              // means startContainer is an element node and then its startOffset is the number of child nodes
              let endOffset = group[N - 1].endOffset;
              let endNode = group[N - 1].endContainer.childNodes[endOffset];

              if (utils.isDefined(endNode)) {
                if (endNode.tagName == "BR") {
                  // this is the end of the paragraph, so select the previous node as end container
                  // and set offset to be its length
                  if (endOffset - 1 >= 0) {
                    endNode =
                      group[N - 1].endContainer.childNodes[endOffset - 1];
                    group[N - 1].setEnd(endNode, getNodeLength(endNode));
                  } else {
                    endNode = group[N - 1].endContainer.previousSibling;
                    if (!utils.isDefined(endNode)) continue;
                  }
                }
              }
            } else if (group[N - 1].endContainer.nodeType === 3) {
              // means it's a text node, so the offset is the number of chars
              let endOffset = group[N - 1].endOffset;
              let endContLength = getNodeLength(group[N - 1].endContainer);

              if (
                endOffset == endContLength &&
                group[0].startContainer != group[N - 1].endContainer
              ) {
                let endNode = findEndNode(group[N - 1].endContainer);
                if (!utils.isDefined(endNode)) continue;
                group[N - 1].setEndAfter(endNode);
              } else if (endOffset === 0) {
                // means the annotator has most probably accidentally hovered
                // over the beginning of the next marker
                let startNode = group[N - 1].startContainer;
                if (utils.isDefined(startNode)) {
                  if (startNode.textContent.length > 0) {
                    // this means endOffset is 0, but there is a non-empty start container
                    // then just set the end after this start container or at the end of
                    // its text node
                    if (startNode.nodeType === 3)
                      group[N - 1].setEnd(startNode, getNodeLength(startNode));
                    else if (startNode.nodeType === 1)
                      group[N - 1].setEndAfter(startNode);
                  } else {
                    // this means that our start container is also empty
                    // this means the group became de-facto collapsed, so remove it
                    group.pop();
                    N = group.length;
                    // find the first group, which is not collapsed
                    // it can either still be with endOffset 0, but a non-empty start container
                    // or with an empty start container, but endOffset which is non-zero
                    // or when both conditions are false
                    while (
                      group[N - 1].endOffset === 0 &&
                      group[N - 1].startContainer.textContent.length === 0
                    ) {
                      group.pop();
                      N = group.length;
                    }

                    if (group[N - 1].endOffset === 0) {
                      // this means that at lest we have a start container that is non-empty
                      // (because otherwise while-loop above would not terminate)
                      let startNode = group[N - 1].startContainer;
                      if (startNode.nodeType === 3)
                        group[N - 1].setEnd(
                          startNode,
                          getNodeLength(startNode)
                        );
                      else if (startNode.nodeType === 1)
                        group[N - 1].setEndAfter(startNode);
                    } else {
                      // this means that there's an endOffset
                      // so there's a valid end container
                      let endNode = group[N - 1].endContainer;

                      if (!utils.isDefined(endNode)) continue;
                      let originalEndContent = endNode.textContent;

                      while (
                        isLabel(endNode.parentNode) &&
                        endNode.parentNode.textContent.endsWith(
                          originalEndContent
                        )
                      ) {
                        endNode = endNode.parentNode;
                      }
                      if (utils.isDefined(endNode))
                        group[N - 1].setEndAfter(endNode);
                    }
                  }
                }
              }
            }

            if (group[0].collapsed || group[N - 1].collapsed) continue;

            chunk["range"] = group[0].cloneRange();
            chunk["range"].setEnd(
              group[N - 1].endContainer,
              group[N - 1].endOffset
            );

            chunk["lengthBefore"] = previousTextLength(
              chunk["range"].startContainer
            );

            chunk["start"] = chunk["range"].startOffset;
            chunk["end"] =
              chunk["start"] +
              group.map(getRangeLength).reduce((a, b) => a + b, 0);
            //group.map(getSelectionLength).reduce((a, b) => a + b, 0);
            // range.toString() does not maintain newlines at all, so we

            chunk["marked"] = false;
            chunk["label"] = null;

            let Nc = chunks.length;
            chunk["id"] = labelId;
            if (
              Nc === 0 ||
              (Nc > 0 &&
                chunks[Nc - 1] !== undefined &&
                chunks[Nc - 1]["marked"])
            ) {
              chunks.push(chunk);
            } else {
              chunks[Nc - 1] = chunk;
            }
          }
        } else {
          let chunk = this.getActiveChunk();
          if (utils.isDefined(chunk) && !chunk["marked"])
            this.removeActiveChunk();
        }
      },
      mark: function (obj, max_markers) {
        // if there were problems with latest selection, we might want to try updating it!
        let control = this;
        if (chunks.length > 0 && activeLabels < max_markers) {
          let chunk = this.getActiveChunk();

          if (!chunk.marked) {
            let displayType = obj.getAttribute("data-dt");

            let markedSpan = createMarkedSpan(obj, displayType),
              deleteMarkedBtn = document.createElement("button");
            markedSpan.classList.add("is-medium");
            markedSpan.setAttribute("data-i", chunk["id"]);
            $(markedSpan).prop("in_relation", false);
            deleteMarkedBtn.className = "delete is-small";

            if (chunk["hash"]) markedSpan.setAttribute("data-h", chunk["hash"]);

            initContextMenu(markedSpan, this.contextMenuPlugins);

            /*
             * NOTE: avoid `chunk['range'].surroundContents(markedSpan)`, since
             * "An exception will be thrown, however, if the Range splits a non-Text node
             * with only one of its boundary points."
             * https://developer.mozilla.org/en-US/docs/Web/API/Range/surroundContents
             */

            try {
              chunk["range"].surroundContents(markedSpan);
              markedSpan.appendChild(deleteMarkedBtn);
            } catch (error) {
              let end = chunk["range"].endContainer,
                nodeAfterEnd = end.nextSibling;
              if (nodeAfterEnd != null) {
                // means we're at the delete button
                if (chunk["range"].endOffset == getNodeLength(end)) {
                  let start = chunk["range"].startContainer,
                    originalText = end.textContent,
                    startOffset = start == end ? chunk["range"].startOffset : 0,
                    endOffset = chunk["range"].endOffset;

                  while (
                    utils.isDefined(nodeAfterEnd) &&
                    isLabel(nodeAfterEnd.parentNode) &&
                    originalText.substr(startOffset, endOffset) ==
                      end.parentNode.textContent.substr(startOffset, endOffset)
                  ) {
                    end = end.parentNode;
                    nodeAfterEnd = nodeAfterEnd.nextSibling;
                    let isEmpty =
                      nodeAfterEnd == null ||
                      nodeAfterEnd.textContent.length == 0;
                    if (
                      (isEmpty && !isLabel(end.parentNode)) ||
                      (!isEmpty && !isDeleteButton(nodeAfterEnd))
                    )
                      break;
                  }

                  if (utils.isDefined(nodeAfterEnd))
                    chunk["range"].setEndAfter(nodeAfterEnd);
                }
              }

              /* This code works well for nodeBeforeStart, but not here
              else if (utils.isDefined(nodeAfterEnd) && nodeAfterEnd.textContent.length === 0) {
                // it's empty string, which sometimes happens for some reason
                chunk['range'].setEndAfter(nodeAfterEnd);
              }*/

              // TODO: this still causes problems when
              // a) we mark at the beginning of already marked span, here it's weird
              //    and depends on the cursor movement???, it seems, as in whether
              //    we come from already marked span or from a different container
              //    and that's how it decides on the startContainer and endContainer?
              // b) we mark part of the already marked span somewhere in the middle,
              //    take all the end with the delete button and then grab some text after
              //
              // In both cases this solution grabs the whole already marked label,
              // even though, the annotator most probably didn't want that.
              //
              // If we put an if statement as in L1262, we can remedy a), but the problem
              // is that the already marked span splits into two, one of which
              // is connected to the same delete button and the other one is orphane.
              //
              // So clearly there should be some tracking of these orphanes such that:
              // 1. If the parent container got deleted, so did the orphane, while all
              //    other marked spans on top of that did not.
              // 2. If the marked span on top of the orphane got deleted, the orphane
              //    should reunite with its parent (both visually and for deletion purposes).

              let nodeBeforeStart =
                chunk["range"].startContainer.previousSibling;
              let start;

              if (nodeBeforeStart == null) {
                // means we're within a label
                if (chunk["range"].startOffset == 0) {
                  start = chunk["range"].startContainer;
                  let originalText = start.textContent,
                    endOffset =
                      start == chunk["range"].endContainer
                        ? chunk["range"].endOffset
                        : originalText.length;

                  while (
                    isLabel(start.parentNode) &&
                    originalText.substr(0, endOffset) ==
                      start.parentNode.textContent.substr(0, endOffset)
                  ) {
                    start = start.parentNode;
                  }
                  if (start != chunk["range"].startContainer)
                    chunk["range"].setStartBefore(start);
                }
              } else if (
                utils.isDefined(nodeBeforeStart) &&
                nodeBeforeStart.textContent.length === 0
              ) {
                // it's empty string, which means that we're at a <br> tag
                // just ensure that <br> is not selected!
                if (
                  nodeBeforeStart.nodeName == "BR" &&
                  chunk["range"].startOffset == 0
                )
                  chunk["range"].setStartAfter(nodeBeforeStart);
              }

              start = chunk["range"].startContainer;
              if (isRelationIdentifier(start)) {
                if (start.nodeType === 3) start = start.parentNode;
                chunk["range"].setStartBefore(start.parentNode);
              }

              markedSpan.appendChild(chunk["range"].extractContents());
              markedSpan.appendChild(deleteMarkedBtn);
              chunk["range"].insertNode(markedSpan);
            }

            let marked =
              chunk["range"].commonAncestorContainer.querySelectorAll(
                "span.tag"
              );
            if (!utils.isDefined(this.initLineHeight)) {
              this.initLineHeight = parseFloat(
                window
                  .getComputedStyle(marked[0], null)
                  .getPropertyValue("line-height")
              );
            }

            let ctx = this;

            for (let i = 0; i < marked.length; i++) {
              let checker = marked[i],
                elements = [];
              while (isLabel(checker)) {
                elements.push(checker);
                checker = checker.parentNode;
              }

              let len = elements.length;
              let elDisplayType = elements[len - 1].getAttribute("data-dt");

              if (elDisplayType == "hl") {
                elements[len - 1].style.lineHeight =
                  ctx.initLineHeight + 3 * 5 + 10 * (len - 1) + "px";
              } else if (elDisplayType == "und") {
                elements[len - 1].style.lineHeight =
                  ctx.initLineHeight + 2 * 5 + 5 * (len - 1) + "px";
              }

              for (let j = 0; j < len; j++) {
                let pTopStr = elements[j].style.paddingTop,
                  pBotStr = elements[j].style.paddingBottom,
                  pTop = parseFloat(pTopStr.slice(0, -2)),
                  pBot = parseFloat(pBotStr.slice(0, -2)),
                  npTop = 4 + 4 * j,
                  npBot = 4 + 4 * j;

                if (displayType == "und") {
                  elements[j].style.textUnderlineOffset =
                    1.75 * (2 + 2 * j) + "px";
                }
                if (pTopStr == "" || (utils.isDefined(pTopStr) && !isNaN(pTop)))
                  elements[j].style.paddingTop = npTop + "px";
                if (pBotStr == "" || (utils.isDefined(pBotStr) && !isNaN(pBot)))
                  elements[j].style.paddingBottom = npBot + "px";
              }
            }

            chunk["marked"] = true;
            chunk["submittable"] = true;
            chunk["independent"] = obj.getAttribute("data-indep") === "true";
            chunk["id"] = labelId;
            labelId++;
            activeLabels++;
            chunk["label"] = obj.getAttribute("data-s");

            let $metaInfo = $(markedSpan).siblings("[data-meta]");
            if ($metaInfo.length > 0) {
              let $metaScript = $metaInfo.find("script");

              if ($metaScript.length > 0) {
                let jsonInfo = JSON.parse($metaScript.text());
                chunk["extra"] = jsonInfo;
              }
            }

            clearSelection(); // force clear selection
          }
        }
      },
      select: function (obj, hash) {
        if (
          !this.textLabelsArea.querySelector(
            '[data-s="' + obj.getAttribute("data-s") + '"]'
          )
        ) {
          let markedSpan = createMarkedSpan(obj),
            deleteMarkedBtn = document.createElement("button");
          markedSpan.textContent = obj.querySelector(
            "span.tag:first-child"
          ).textContent;
          markedSpan.classList.add("is-small");
          deleteMarkedBtn.className = "delete is-small";
          markedSpan.appendChild(deleteMarkedBtn);

          if (utils.isDefined(hash)) {
            markedSpan.setAttribute("data-h", hash);
          }

          this.textLabelsArea.appendChild(markedSpan);
        }
      },
      checkRestrictions: function (inRelation) {
        if (inRelation === undefined) inRelation = false;
        let ctx = this;

        let markers = document.querySelectorAll(".marker.tags[data-res]");
        let messages = {
          s: [],
          i: [],
        };

        let satisfied = Array.from(markers).map(function (x) {
          let res = x.getAttribute("data-res").split("&");

          for (let i = 0, len = res.length; i < len; i++) {
            if (res[i]) {
              let have = inRelation
                ? ctx.selectorArea.querySelectorAll(
                    'span.tag[data-s="' +
                      x.getAttribute("data-s") +
                      '"].active:not(.is-disabled)'
                  ).length
                : ctx.selectorArea.querySelectorAll(
                    'span.tag[data-s="' +
                      x.getAttribute("data-s") +
                      '"]:not(.is-disabled)'
                  ).length;
              let rlen = res[i].length,
                mode = res[i].slice(rlen - 1),
                needed = parseInt(res[i].slice(2, rlen - 1), 10),
                restriction = res[i].slice(0, 2),
                label = x.querySelector("span.tag").textContent.trim();
              if (restriction == "ge") {
                if (have >= needed) {
                  return true;
                } else {
                  let diff = needed - have;
                  messages[mode].push(
                    "You need at least " +
                      diff +
                      ' more "' +
                      label +
                      '" ' +
                      "label" +
                      (diff > 1 ? "s" : "")
                  );
                  return false;
                }
              } else if (restriction == "gs") {
                if (have > needed) {
                  return true;
                } else {
                  let diff = needed - have + 1;
                  messages[mode].push(
                    "You need at least " +
                      diff +
                      ' more "' +
                      label +
                      '" ' +
                      "label" +
                      (diff > 1 ? "s" : "")
                  );
                  return false;
                }
              } else if (restriction == "le") {
                if (have <= needed) {
                  return true;
                } else {
                  messages[mode].push(
                    "You can have max " +
                      needed +
                      ' "' +
                      label +
                      '" ' +
                      "label" +
                      (needed > 1 ? "s" : "")
                  );
                  return false;
                }
              } else if (restriction == "ls") {
                if (have < needed) {
                  return true;
                } else {
                  messages[mode].push(
                    "You can have max " +
                      (needed - 1) +
                      ' "' +
                      label +
                      '" ' +
                      "label" +
                      (needed - 1 > 1 ? "s" : "")
                  );
                  return false;
                }
              } else if (restriction == "eq") {
                if (have == needed) {
                  return true;
                } else {
                  messages[mode].push(
                    "You need to have exactly " +
                      needed +
                      ' "' +
                      label +
                      '" ' +
                      "label" +
                      (needed > 1 ? "s" : "")
                  );
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

        let numSatisfied = satisfied.reduce(function (acc, val) {
          return acc + val;
        }, 0);

        let requiredAlertMsg = [];

        // check required inputs
        let requiredRadioGroups = utils.defaultobj(() => Array());
        let radios = this.markersArea.querySelectorAll(
          'input[type="radio"][required]'
        );
        radios.forEach((x) =>
          requiredRadioGroups[utils.getRadioLabel(x)].push(x.checked)
        );

        for (let name in requiredRadioGroups) {
          let group = requiredRadioGroups[name];
          let filledIn = group.reduce((a, b) => a && b);
          if (!filledIn) {
            requiredAlertMsg.push("The field " + '"' + name + '" is required!');
          }
        }

        let textInputs = this.markersArea.querySelectorAll(
          'input[type="text"][required],textarea[required]'
        );
        textInputs.forEach(function (x) {
          if (!x.value) {
            let name;
            if (x.tagName == "INPUT") {
              let tag = x.nextElementSibling;
              name = tag.firstChild.textContent.trim();
            } else {
              let tag = x.previousElementSibling;
              name = tag.firstChild.textContent.trim();
            }
            requiredAlertMsg.push("The field " + '"' + name + '" is required!');
          }
        });

        if (requiredAlertMsg.length > 0) {
          alert(requiredAlertMsg.join("\n"));
          return false;
        }

        if (numSatisfied != markers.length) {
          if (messages["s"].length > 0) {
            alert(messages["s"].join("\n"));
          } else if (messages["i"].length > 0) {
            let res = confirm(
              "Some optional restrictions are not satisfied:\n" +
                messages["i"].join("\n") +
                "\nDo you want to ignore these?"
            );

            if (res) return true; // ignore and declare the restrictions to be passed
          }
        }

        return numSatisfied == markers.length && requiredAlertMsg.length == 0;
      },
      initSvg: function () {
        if (typeof d3 !== "undefined") {
          /* Relations */
          let svg = d3
            .select("#relations")
            .append("svg")
            .attr("width", "100%")
            .attr("height", "100%")
            .call(responsifySVG);

          // TODO: this marker should be visible w.r.t. the target node
          svg
            .append("svg:defs")
            .append("svg:marker")
            .attr("id", "triangle")
            .attr("refX", 6)
            .attr("refY", 6)
            .attr("markerWidth", 20)
            .attr("markerHeight", 20)
            .attr("markerUnits", "userSpaceOnUse")
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M 0 0 12 6 0 12 3 6")
            .style("fill", "black");
        }
      },
      drawNetwork: function (data, arrows) {
        function ticked(text, link, node, radius) {
          /* update the simulation */
          text
            .attr("x", function (d) {
              return d.x + radius * 1.2;
            })
            .attr("y", function (d) {
              return d.y;
            });

          link
            .attr("x1", function (d) {
              return d.source.x;
            })
            .attr("y1", function (d) {
              return d.source.y;
            })
            .attr("x2", function (d) {
              let dx = 0.7 * Math.abs(d.target.x - d.source.x);
              if (d.target.x > d.source.x) {
                return d.source.x + dx;
              } else {
                return d.source.x - dx;
              }
            })
            .attr("y2", function (d) {
              let dx = 0.7 * Math.abs(d.target.x - d.source.x);
              let x = null;
              if (d.target.x > d.source.x) {
                x = d.source.x + dx;
              } else {
                x = d.source.x - dx;
              }

              let dy =
                (Math.abs(x - d.source.x) * Math.abs(d.target.y - d.source.y)) /
                Math.abs(d.target.x - d.source.x);

              if (d.target.y > d.source.y) {
                // means arrow down
                return d.source.y + dy;
              } else {
                // means arrow up
                return d.source.y - dy;
              }
            });

          node
            .attr("cx", function (d) {
              return d.x;
            })
            .attr("cy", function (d) {
              return d.y;
            });
        }

        function finalizeSimulation() {
          let group = d3.select("g#" + data.id);

          if (!group.empty()) {
            // let bbox = group.node().getBBox();

            let svgBbox = document.querySelector("svg").getBoundingClientRect();

            let mx = svgBbox.width / 2;
            let my = svgBbox.height / 2;

            group.attr("transform", "translate(" + mx + ", " + my + ")");
          }
        }

        if (typeof d3 !== "undefined") {
          if (arrows === undefined) arrows = false;

          let svg = d3.select("#relations svg"),
            radius = 10;

          svg.selectAll("g").attr("class", "hidden");

          svg.select("g#" + data.id).remove();

          svg = svg.append("g").attr("id", data.id);

          let link = svg
            .selectAll("line")
            .data(data.links)
            .enter()
            .append("line")
            .style("stroke", "#aaa");

          if (arrows) link = link.attr("marker-end", "url(#triangle)");

          // Initialize the nodes
          let node = svg
            .selectAll("circle")
            .data(data.nodes)
            .enter()
            .append("circle")
            .attr("r", radius)
            .attr("data-id", function (d) {
              return d.id;
            })
            .style("fill", function (d) {
              return d.color;
            })
            .on("mouseover", function (d) {
              $(d.dom).addClass("active");
            })
            .on("mouseout", function (d) {
              $(d.dom).removeClass("active");
            });

          let text = svg
            .selectAll("text")
            .data(data.nodes)
            .enter()
            .append("text")
            .text(function (d) {
              return d.name.length > 10 ? d.name.substr(0, 10) + "..." : d.name;
            });

          // Let's list the force we wanna apply on the network
          let simulation = d3
            .forceSimulation(data.nodes) // Force algorithm is applied to data.nodes
            .force(
              "link",
              d3
                .forceLink() // This force provides links between nodes
                .id(function (d) {
                  return d.id;
                }) // This provide  the id of a node
                .links(data.links) // and this the list of links
            )
            .force("charge", d3.forceManyBody().strength(-400)) // This adds repulsion between nodes. Play with the -400 for the repulsion strength
            .force("center", d3.forceCenter(radius, 10)) // This force attracts nodes to the center of the svg area
            .stop();

          // This function is run at each iteration of the force algorithm, updating the nodes position.

          for (
            let i = 0,
              n = Math.ceil(
                Math.log(simulation.alphaMin()) /
                  Math.log(1 - simulation.alphaDecay())
              );
            i < n;
            ++i
          ) {
            simulation.tick();
            ticked(text, link, node, radius);
          }
          finalizeSimulation();

          this.showRelationGraph(currentRelationId);
        }
      },
      drawList: function (data) {
        if (typeof d3 !== "undefined") {
          let svg = d3.select("#relations svg"),
            radius = 10;

          svg.selectAll("g").attr("class", "hidden");

          svg.select("g#" + data.id).remove();

          svg = svg.append("g").attr("id", data.id);

          data.nodes.forEach(function (n, i) {
            n["x"] = 10;
            n["y"] = 15 + i * (2 * radius + 7);
          });

          // Initialize the nodes
          svg
            .selectAll("circle")
            .data(data.nodes)
            .enter()
            .append("circle")
            .attr("cx", function (d) {
              return d.x;
            })
            .attr("cy", function (d) {
              return d.y;
            })
            .attr("r", radius)
            .attr("data-id", function (d) {
              return d.id;
            })
            .style("fill", function (d) {
              return d.color;
            })
            .on("mouseover", function (d) {
              $(d.dom).addClass("active");
            })
            .on("mouseout", function (d) {
              $(d.dom).removeClass("active");
            });

          svg
            .selectAll("text")
            .data(data.nodes)
            .enter()
            .append("text")
            .text(function (d) {
              return d.name.length > 20 ? d.name.substr(0, 20) + "..." : d.name;
            })
            .attr("x", function (d) {
              return d.x + radius * 1.3;
            })
            .attr("y", function (d) {
              return d.y + 0.5 * radius;
            });

          this.showRelationGraph(currentRelationId);
        }
      },
      getAvailableRelationIds: function () {
        return Object.keys(relations);
      },
      countUnsubmittedChunks: function () {
        return chunks.filter(function (c) {
          return c.submittable;
        }).length;
      },
      previousRelation: function () {
        if (currentRelationId == null) return currentRelationId;

        currentRelationId--;
        if (currentRelationId <= 0) {
          currentRelationId = 1;
        }
        return currentRelationId;
      },
      nextRelation: function () {
        if (currentRelationId == null) return currentRelationId;

        currentRelationId++;
        let graphIds = Object.keys(relations);
        if (currentRelationId > graphIds.length) {
          currentRelationId = graphIds.length;
        }
        return currentRelationId;
      },
      removeRelation: function (idx, exception) {
        let control = this;

        $("g#" + relations[idx]["graphId"])
          .find("circle[data-id]")
          .each(function (i, d) {
            let $el = $("#" + d.getAttribute("data-id"));
            if (
              utils.isDefined(exception) &&
              $el.attr("id") == $(exception).attr("id")
            )
              return;
            if ($el.length > 0) {
              control.updateRelationSwitcher($el[0], undefined, idx);
            }
          });
        d3.select("g#" + relations[idx]["graphId"]).remove();
        delete relations[idx];
        let map = {};
        let keys = Object.keys(relations);
        keys.sort();
        let k, kk;
        for (k in keys) {
          kk = parseInt(keys[k], 10);
          if (kk > idx) {
            $("g#" + relations[keys[k]]["graphId"])
              .find("circle[data-id]")
              .each(function (i, d) {
                let $el = $("#" + d.getAttribute("data-id"));
                if ($el.length > 0) {
                  $el.find('[data-m="r"]').text(kk - 1);
                }
              });
            relations[kk - 1] = relations[kk];
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
      removeCurrentRelation: function () {
        this.removeRelation(currentRelationId);
        let graphIds = Object.keys(relations);
        currentRelationId = graphIds.length > 0 ? graphIds.length : null;
        return currentRelationId;
      },
      showRelationGraph(id) {
        if (id == null || id === undefined) $("#relationId").text(0);
        else {
          let svg = d3.select("#relations svg");

          svg.selectAll("g").attr("class", "hidden");

          d3.select("g#" + relations[id]["graphId"]).attr("class", "");

          $("#relationId").text(id + " - " + relations[id]["name"]);
        }
        currentRelationId = id;
      },
      updateRelationSwitcher: function (x, relationId, removeId) {
        let relSpan = undefined;
        if (x.hasOwnProperty("dom")) relSpan = x.dom.querySelector("[data-m]");
        else relSpan = x.querySelector("[data-m]");

        if (removeId < 0) removeId = undefined;

        if (utils.isDefined(relSpan)) {
          if (utils.isDefined($(relSpan).prop("rels"))) {
            let rr = $(relSpan).prop("rels");

            if (utils.isDefined(removeId)) {
              let idx = rr.indexOf(parseInt(removeId, 10));
              if (idx != -1) rr.splice(idx, 1);
            }

            if (utils.isDefined(relationId)) {
              if (parseInt(relationId, 10) < 0) {
                rr = [];
              } else if (rr.indexOf(parseInt(relationId, 10)) == -1) {
                rr.push(relationId);
              }
            }
            $(relSpan).prop("rels", rr);

            if (rr.length > 0)
              relSpan.textContent = rr.length > 1 ? "+" : rr[0];
            else {
              relSpan.textContent = "";
              let $x = $(x.hasOwnProperty("dom") ? x.dom : x);
              $x.prop("in_relation", false);
              $x.attr("id", "");
              $(relSpan).remove();
              relSpan = undefined;
            }
          } else if (utils.isDefined(relationId)) {
            relSpan.textContent = relationId;
            $(relSpan).prop("rels", [relationId]);
          }
        } else if (utils.isDefined(relationId)) {
          relSpan = document.createElement("span");
          relSpan.setAttribute("data-m", "r");
          relSpan.className = "rel";
          relSpan.textContent = relationId;
          x.dom.appendChild(relSpan);
          $(relSpan).prop("rels", [relationId]);
        }

        if (utils.isDefined(relSpan)) {
          let content = createRelationSwitcher($(relSpan).prop("rels"));

          if (relSpan._tippy) {
            relSpan._tippy.destroy();
          }

          const instance = tippy(relSpan, {
            content: content,
            interactive: true,
            placement: "bottom",
            theme: "translucent",
          });
        }
      },
      markRelation: function (obj) {
        if (!this.checkRestrictions(true)) return;

        let $parts = $(this.selectorArea).find("span.tag.active"),
          between = obj
            .getAttribute("data-b")
            .split("|")
            .map((x) => x.split("-:-")),
          direction = obj.getAttribute("data-d"),
          rule = obj.getAttribute("data-r"),
          relName = obj.querySelector('[data-role="name"]').textContent,
          control = this,
          newRelationId = lastRelationId;

        if ($parts.length >= 2) {
          let allInRelation = true,
            rels = [],
            sameRels = [];
          for (let i = 0, len = $parts.length; i < len; i++) {
            let $p = $($parts[i]);
            allInRelation = allInRelation && $p.prop("in_relation");
            rels.push($p.find("[data-m]").prop("rels"));
          }

          // linear scan to check that the same relation is not attempted to be created
          if (allInRelation) {
            let relsLength = rels.length,
              ptr = new Array(relsLength),
              isLast = false;
            ptr.fill(0);

            while (!isLast) {
              let cur = rels.map((x, i) => x[ptr[i]]);
              let candLast = true;

              if (new Set(cur).size === 1) {
                // all same, advance all pointers
                sameRels.push(rels[ptr[0]]);
                for (let j = 0; j < relsLength; j++) {
                  if (ptr[j] + 1 < rels[j].length) {
                    ptr[j]++;
                  }
                  candLast = candLast && ptr[j] + 1 == rels[j].length;
                }
              } else {
                // Advance the minimal pointers
                let arrMin = Math.min(...cur);
                for (let j = 0; j < relsLength; j++) {
                  if (cur[ptr[j]] == arrMin && ptr[j] + 1 < rels[j].length) {
                    ptr[j]++;
                  }
                  candLast = candLast && ptr[j] + 1 == rels[j].length;
                }
              }

              if (isLast) break;
              isLast = candLast;
            }
          }

          for (let j = 0, len = sameRels.length; j < len; j++) {
            let ind = sameRels[j];

            if (
              relations[ind]["rule"] == rule &&
              relations[ind]["name"] == relName
            ) {
              return;
            }
          }

          let nodes = {},
            startId = lastNodeInRelationId,
            rels2remove = [],
            candRels = [];
          $parts.each(function (i) {
            let $part = $($parts[i]);

            if ($part.prop("in_relation")) {
              let rr = $($parts[i].querySelector("[data-m]")).prop("rels");
              if (
                utils.isDefined(rr) &&
                rr.length === 1 &&
                rule == relations[rr[0]].rule
              ) {
                newRelationId = rr[0];
                candRels.push(rr[0]);
              }
            } else {
              $parts[i].id = "rl_" + lastNodeInRelationId;
              lastNodeInRelationId++;
            }

            $part.prop("in_relation", true);

            // strip marker variant part
            let s = $parts[i].getAttribute("data-s");
            s = s.substring(0, s.lastIndexOf("_"));

            $part.prop(
              "multiple_possible_relations",
              checkForMultiplePossibleRelations(control.relationsArea, s)
            );

            if (!nodes.hasOwnProperty(s)) {
              nodes[s] = [];
            }
            nodes[s].push({
              id: $parts[i].id,
              name: getLabelText($parts[i]),
              dom: $parts[i],
              ts: $part.prop("ts"),
              color: getComputedStyle($parts[i])["background-color"],
            });

            // if relationship is bidirectional and we add the node to an already existing relation,
            // then also pull all other nodes from the relation
            if (direction == "2" && newRelationId != lastRelationId) {
              let storedIds = nodes[s].map((x) => x.id),
                otherNodes = relations[newRelationId].d3.nodes;

              for (let ons in otherNodes) {
                if (!nodes.hasOwnProperty(ons)) nodes[ons] = [];

                if (ons == s) {
                  for (let i in otherNodes[ons]) {
                    if (!storedIds.includes(otherNodes[ons][i].id))
                      nodes[ons].push(otherNodes[ons][i]);
                  }
                } else {
                  for (let i in otherNodes[ons]) {
                    nodes[ons].push(otherNodes[ons][i]);
                  }
                }
              }
            }
          });

          if (candRels.length > 1) {
            newRelationId = Math.min(...candRels);
            for (let i in candRels) {
              if (candRels[i] != newRelationId) rels2remove.push(candRels[i]);
            }
          }

          let from = null,
            to = null;
          if (direction == "0" || direction == "2") {
            // first -> second or bidirectional
            from = 0;
            to = 1;
          } else if (direction == "1") {
            // second -> first
            from = 1;
            to = 0;
          }

          let sketches = [];
          for (let i = 0, len = between.length; i < len; i++) {
            let sketch = {
              nodes: {},
              links: [],
              between: between[i],
            };
            if (
              utils.isDefined(nodes[between[i][from]]) &&
              utils.isDefined(nodes[between[i][to]])
            ) {
              if (
                between[i][from] == between[i][to] &&
                nodes[between[i][from]].length < 2
              ) {
                // can't make a relationship with itself
                continue;
              }

              if (!sketch.nodes.hasOwnProperty(between[i][from]))
                sketch.nodes[between[i][from]] = [];
              sketch.nodes[between[i][from]].push.apply(
                sketch.nodes[between[i][from]],
                nodes[between[i][from]]
              );
              if (nodes[between[i][from]] != nodes[between[i][to]]) {
                if (!sketch.nodes.hasOwnProperty(between[i][to]))
                  sketch.nodes[between[i][to]] = [];
                sketch.nodes[between[i][to]].push.apply(
                  sketch.nodes[between[i][to]],
                  nodes[between[i][to]]
                );
              }
              nodes[between[i][from]].forEach(function (f) {
                nodes[between[i][to]].forEach(function (t) {
                  if (
                    direction == "2" ||
                    (direction == "0" && f.ts < t.ts) ||
                    (direction == "1" && t.ts < f.ts)
                  ) {
                    if (f.id != t.id) {
                      // prevent loops
                      sketch.links.push({
                        source: f.id,
                        target: t.id,
                      });
                    }
                  }
                });
              });
              sketches.push(sketch);
            }
          }

          if (sketches.length === 0) {
            alert("No relations could be formed among the selected labels");
            $parts.removeClass("active");
            $parts.prop("selected", false);
            $parts.prop("in_relation", false);
            return;
          }

          let j = startId;

          for (let i = 0, len = sketches.length; i < len; i++) {
            for (let key in sketches[i].nodes) {
              j += sketches[i].nodes[key].length;
            }

            if (relations.hasOwnProperty(newRelationId)) {
              for (let k in sketches[i].nodes) {
                let nn = sketches[i].nodes[k];
                for (let a = 0, len_a = nn.length; a < len_a; a++) {
                  if (
                    !containsIdentical(
                      relations[newRelationId].d3.nodes[k],
                      nn[a]
                    )
                  ) {
                    if (!relations[newRelationId].d3.nodes.hasOwnProperty(k))
                      relations[newRelationId].d3.nodes[k] = [];
                    relations[newRelationId].d3.nodes[k].push(nn[a]);
                  }
                }
              }

              for (
                let a = 0, len_a = sketches[i].links.length;
                a < len_a;
                a++
              ) {
                let nn = sketches[i].links[a],
                  inv = { target: nn["source"], source: nn["target"] };
                if (
                  !containsIdentical(relations[newRelationId].d3.links, nn) &&
                  !containsIdentical(relations[newRelationId].d3.links, inv)
                ) {
                  relations[newRelationId].d3.links.push(nn);
                }
              }
            } else {
              relations[newRelationId] = {
                graphId: "n" + startId + "__" + (j - 1),
                rule: rule,
                between: sketches[i].between,
                links: [],
                name: relName,
                d3: {
                  nodes: sketches[i].nodes,
                  links: sketches[i].links,
                  from: from,
                  to: to,
                  direction: direction,
                },
              };
            }

            sketches[i].links.forEach(function (l) {
              let source = document.querySelector("#" + l.source),
                target = document.querySelector("#" + l.target);
              // if bidirectional, no need to store mirrored relations
              if (
                direction === 2 &&
                containsIdentical(relations[newRelationId]["links"], {
                  s: target.getAttribute("data-i"),
                  t: source.getAttribute("data-i"),
                })
              )
                return;

              let obj = {
                s: source.getAttribute("data-i"),
                t: target.getAttribute("data-i"),
              };

              if (!containsIdentical(relations[newRelationId]["links"], obj))
                relations[newRelationId]["links"].push(obj);
            });

            currentRelationId = newRelationId;

            if (
              !utils.isDefined(this.drawingType[rule]) ||
              this.drawingType[rule] == "g"
            ) {
              this.drawNetwork(
                {
                  id: relations[newRelationId]["graphId"],
                  nodes: Array.prototype.concat.apply(
                    [],
                    Object.values(relations[newRelationId].d3.nodes)
                  ),
                  links: [].concat(relations[newRelationId].d3.links), // necessary since d3 changes the structure of links
                },
                from != null && to != null && direction != "2"
              );
            } else if (this.drawingType[rule] == "l") {
              this.drawList({
                id: relations[newRelationId]["graphId"],
                nodes: Array.prototype.concat.apply(
                  [],
                  Object.values(relations[newRelationId].d3.nodes)
                ),
              });
            }

            for (let s in sketches[i].nodes) {
              let snodes = sketches[i].nodes[s];
              snodes.forEach(function (x) {
                control.updateRelationSwitcher(x, newRelationId);
                x.dom.classList.remove("active");
                $(x.dom).prop("selected", false);
              });
            }

            if (newRelationId == lastRelationId) lastRelationId++;
            startId = j;
          }

          for (let i in rels2remove) {
            this.removeRelation(rels2remove[i]);
          }

          const event = new Event(RELATION_CHANGE_EVENT);
          // Dispatch the event.
          document.dispatchEvent(event);
          this.updateMarkAllCheckboxes();
        }
      },
      changeRelation: function (obj, fromId, toId) {
        let objId = obj.id,
          il = obj.getAttribute("data-i"),
          code = obj.getAttribute("data-s"),
          short = code.substring(0, code.lastIndexOf("_")),
          fromRel = relations[fromId],
          toRel = relations[toId],
          // a relation map, which is initially identity, but might become smth else if anything is deleted
          map = { [fromId]: fromId, [toId]: toId },
          control = this;

        if (
          utils.isDefined(fromRel) &&
          utils.isDefined(toRel) &&
          fromRel.between.sort().join(",") != toRel.between.sort().join(",")
        ) {
          alert("Cannot move between different kind of relations");
          return;
        }

        let newNodes;
        if (utils.isDefined(fromRel)) {
          newNodes = fromRel.d3.nodes[short].filter(function (x) {
            return x.id == objId;
          });
          fromRel.links = fromRel.links.filter(function (x) {
            return x.s != il && x.t != il;
          });
          fromRel.d3.nodes[short] = fromRel.d3.nodes[short].filter(
            function (x) {
              return x.id != objId;
            }
          );
          if (fromRel.links.length > 0) {
            fromRel.d3.links = fromRel.d3.links.filter(function (x) {
              return x.source.id != objId && x.target.id != objId;
            });
            d3.select("g#" + fromRel.graphId).remove();
            if (
              !utils.isDefined(this.drawingType[fromRel.rule]) ||
              this.drawingType[fromRel.rule] == "g"
            ) {
              this.drawNetwork(
                {
                  id: fromRel.graphId,
                  nodes: Array.prototype.concat.apply(
                    [],
                    Object.values(fromRel.d3.nodes)
                  ),
                  links: [].concat(fromRel.d3.links),
                },
                fromRel.d3.from != null &&
                  fromRel.d3.to != null &&
                  fromRel.d3.direction != "2"
              );
            } else if (this.drawingType[fromRel.rule] == "l") {
              this.drawList({
                id: fromRel.graphId,
                nodes: Array.prototype.concat.apply(
                  [],
                  Object.values(fromRel.d3.nodes)
                ),
              });
            }
            relations[fromId] = fromRel;
          } else {
            map =
              utils.isDefined(toId) && toId != -1
                ? this.removeRelation(fromId, obj)
                : this.removeRelation(fromId);
            this.showRelationGraph(null);
          }
        } else {
          // means obj was in no relation previously
          obj.id = "rl_" + lastNodeInRelationId;
          lastNodeInRelationId++;
          let relSpan = obj.querySelector('span[data-m="r"]');
          if (relSpan == null) {
            relSpan = document.createElement("span");
            relSpan.setAttribute("data-m", "r");
            relSpan.classList.add("rel");
            relSpan.textContent = "";
            obj.appendChild(relSpan);
          }

          $(obj).prop("in_relation", true);
          newNodes = [
            {
              id: obj.id,
              name: getLabelText(obj),
              dom: obj,
              color: getComputedStyle(obj)["background-color"],
            },
          ];
        }

        if (utils.isDefined(toRel)) {
          let newLinks = [];
          if (toRel.between[toRel.d3.to] == short) {
            toRel.d3.nodes[toRel.between[toRel.d3.from]].forEach(function (f) {
              newNodes.forEach(function (t) {
                if (f.id != t.id) {
                  // prevent loops
                  newLinks.push({
                    source: f.id,
                    target: t.id,
                  });
                }
              });
            });
          }

          if (toRel.between[toRel.d3.from] == short) {
            newNodes.forEach(function (f) {
              toRel.d3.nodes[toRel.between[toRel.d3.to]].forEach(function (t) {
                if (f.id != t.id) {
                  // prevent loops
                  newLinks.push({
                    source: f.id,
                    target: t.id,
                  });
                }
              });
            });
          }
          toRel.d3.nodes[short] = toRel.d3.nodes[short].concat(newNodes);

          newLinks.forEach(function (l) {
            let source = document.querySelector("#" + l.source),
              target = document.querySelector("#" + l.target);
            if (
              toRel.d3.direction === 2 &&
              containsIdentical(toRel.links, {
                s: target.getAttribute("data-i"),
                t: source.getAttribute("data-i"),
              })
            )
              return;
            toRel.links.push({
              s: source.getAttribute("data-i"),
              t: target.getAttribute("data-i"),
            });
          });

          toRel.d3.links = toRel.d3.links.concat(newLinks);

          d3.select("g#" + toRel.graphId).remove();
          if (
            !utils.isDefined(this.drawingType[toRel.rule]) ||
            this.drawingType[toRel.rule] == "g"
          ) {
            this.drawNetwork(
              {
                id: toRel.graphId,
                nodes: Array.prototype.concat.apply(
                  [],
                  Object.values(toRel.d3.nodes)
                ),
                links: [].concat(toRel.d3.links),
              },
              toRel.d3.from != null &&
                toRel.d3.to != null &&
                toRel.d3.direction != "2"
            );
          } else if (this.drawingType[toRel.rule] == "l") {
            this.drawList({
              id: toRel.graphId,
              nodes: Array.prototype.concat.apply(
                [],
                Object.values(toRel.d3.nodes)
              ),
            });
          }

          obj.querySelector('[data-m="r"]').textContent = map[toId];

          this.showRelationGraph(map[toId]);

          relations[toId] = toRel;

          newNodes.forEach((x) =>
            control.updateRelationSwitcher(x, toId, fromId)
          );
        } else {
          newNodes.forEach((x) =>
            control.updateRelationSwitcher(x, toId, fromId)
          );
        }

        // deselect if somone accidentally left clicked on the label
        obj.classList.remove("active");
        $(obj).prop("selected", false);

        const event = new Event(RELATION_CHANGE_EVENT);
        // Dispatch the event.
        document.dispatchEvent(event);
      },
      collectSiblings: function (markedSpan, level, hr) {
        let siblings = filterSiblings(markedSpan, isLabel);
        if (siblings) {
          for (let i in siblings) hr[level].push(siblings[i]);
        }
      },
      getMarkerHierarchy: function (markedSpan, level, hr) {
        let control = this;
        if (!utils.isDefined(hr)) hr = utils.defaultobj(() => Array());
        if (!utils.isDefined(level)) level = 1; // default for the initial marker

        this.collectSiblings(markedSpan, level, hr);

        if (level === 1) {
          // let's account for the parent nodes as well
          if (isLabel(markedSpan.parentNode))
            hr[level - 1].push(markedSpan.parentNode);

          this.collectSiblings(markedSpan.parentNode, level - 1, hr);
        }

        for (let i = 0, len = markedSpan.childNodes.length; i < len; i++) {
          if (isLabel(markedSpan.childNodes[i])) {
            hr[level + 1].push(markedSpan.childNodes[i]);
          }
          control.getMarkerHierarchy(markedSpan.childNodes[i], level + 1, hr);
        }
        return hr;
      },
      deleteSpan: function (markedSpan) {
        let displayType = markedSpan.getAttribute("data-dt");

        let hr = this.getMarkerHierarchy(markedSpan);
        let ctx = this;

        let levels = Array.from(Object.keys(hr)).sort().reverse();
        let len = levels.length;
        if (len > 0) {
          let lastLevelObj = hr[levels[len - 1]];
          for (let i in lastLevelObj) {
            let elDisplayType = lastLevelObj[i].getAttribute("data-dt");
            if (elDisplayType == "hl") {
              lastLevelObj[i].style.lineHeight =
                ctx.initLineHeight + 3 * 5 + 10 * (len - 1) + "px";
            } else if (elDisplayType == "und") {
              lastLevelObj[i].style.lineHeight =
                ctx.initLineHeight + 2 * 5 + 5 * (len - 1) + "px";
            }
          }
        }

        for (let j = 0; j < len; j++) {
          let npTop = 4 + 4 * j,
            npBot = 4 + 4 * j,
            undOffset = 1.75 * (2 + 2 * j);
          let levelObj = hr[levels[j]];
          for (let i in levelObj) {
            let pTopStr = levelObj[i].style.paddingTop,
              pBotStr = levelObj[i].style.paddingBottom,
              pTop = parseFloat(pTopStr.slice(0, -2)),
              pBot = parseFloat(pBotStr.slice(0, -2));

            if (displayType == "und") {
              levelObj[i].style.textUnderlineOffset = undOffset + "px";
            }

            if (pTopStr == "" || (utils.isDefined(pTopStr) && !isNaN(pTop)))
              levelObj[i].style.paddingTop = npTop + "px";
            if (pBotStr == "" || (utils.isDefined(pBotStr) && !isNaN(pBot)))
              levelObj[i].style.paddingBottom = npBot + "px";
          }
        }

        mergeWithNeighbors(markedSpan);
      },
      labelDeleteHandler: function (e) {
        // when a delete button on any label is clicked
        e.stopPropagation();
        let target = e.target, // delete button
          parent = target.parentNode, // actual span
          scope = parent.getAttribute("data-scope");

        if (scope == "text") {
          parent.remove();
        } else if (scope == "span") {
          let sibling = target.nextSibling,
            chunkId = parent.getAttribute("data-i"),
            chunk2del = chunks.filter(function (x) {
              return x.id == chunkId;
            }); // the span with a relation number (if any)

          let rel = isInRelations(chunk2del[0]);
          if (rel) {
            this.changeRelation(parent, rel, null);
          }

          target.remove(); // remove delete button
          if (sibling != null) sibling.remove(); // remove the relation identifier (if any)

          let iid = parent.getAttribute("data-i");
          this.deleteSpan(parent);

          let disjointParts = this.selectorArea.querySelectorAll(
            '[data-i="' + iid + '"]'
          );
          for (let i = 0, len = disjointParts.length; i < len; i++) {
            this.deleteSpan(disjointParts[i]);
          }

          if (utils.isDefined(editingBatch)) {
            for (let i = 0, len = chunks.length; i < len; i++) {
              if (chunks[i].id == chunkId) {
                chunks[i]["deleted"] = true;
                break;
              }
            }
          } else {
            chunks = chunks.filter(function (x) {
              return x.id != chunkId;
            });
          }

          // $(target).prop('in_relation', false);
          activeLabels--;
        }
      },
      getSubmittableDict: function (stringify) {
        if (!utils.isDefined(stringify)) stringify = false;

        let markerGroups = utils.isDefined(this.markerGroupsArea)
            ? $(this.markerGroupsArea)
                .find("form#markerGroups")
                .serializeObject()
            : {},
          shortTextMarkers = utils.isDefined(this.markersArea)
            ? utils.serializeHashedObject(
                $(this.markersArea).find('input[type="text"]')
              )
            : {},
          submitRelations = [],
          textMarkers = Array.from(
            this.textLabelsArea.querySelectorAll(
              "span.tag[data-s]:not(.is-disabled)"
            )
          ).map((x) => x.getAttribute("data-s")),
          numbers = utils.isDefined(this.markersArea)
            ? utils.serializeHashedObject(
                $(this.markersArea).find('input[type="number"]')
              )
            : {},
          ranges = utils.isDefined(this.markersArea)
            ? utils.serializeHashedObject(
                $(this.markersArea)
                  .find('input[type="range"]')
                  .filter(
                    (i, x) => $('output[for="' + x.id + '"]').text() != "???"
                  )
              )
            : {},
          radioButtons = {},
          checkBoxes = {},
          longTextMarkers = utils.isDefined(this.markersArea)
            ? utils.serializeHashedObject($(this.markersArea).find("textarea"))
            : {},
          submittableChunks = chunks.filter((c) => c.submittable);

        if (utils.isDefined(this.markersArea)) {
          $(this.markersArea)
            .find('input[type="radio"]')
            .filter((i, x) => x.checked)
            .each(function (i, x) {
              // simulate serializeHashedObject here
              let name = x.name.endsWith("_ocat")
                ? x.name.replace("_ocat", "")
                : x.name;
              if (x.hasAttribute("data-h")) {
                if (radioButtons.hasOwnProperty(name)) {
                  radioButtons[name].value += getRadioButtonValue(x);
                } else {
                  radioButtons[name] = {
                    hash: x.getAttribute("data-h"),
                    value: getRadioButtonValue(x),
                  };
                }
              } else {
                if (radioButtons.hasOwnProperty(name)) {
                  radioButtons[name] += getRadioButtonValue(x);
                } else {
                  radioButtons[name] = getRadioButtonValue(x);
                }
              }
            });

          $(this.markersArea)
            .find('input[type="checkbox"]')
            .filter((i, x) => x.checked)
            .each(function (i, x) {
              // simulate serializeHashedObject here
              if (!checkBoxes.hasOwnProperty(x.name)) {
                if (x.hasAttribute("data-h"))
                  checkBoxes[x.name] = {
                    hash: x.getAttribute("data-h"),
                    value: [],
                  };
                else checkBoxes[x.name] = [];
              }
              if (x.hasAttribute("data-h"))
                checkBoxes[x.name].value.push(x.value);
              else checkBoxes[x.name].push(x.value);
            });

          var ctx = this;
          for (let key in checkBoxes) {
            if (Array.isArray(checkBoxes[key]))
              checkBoxes[key] = checkBoxes[key].join(ctx.radioCheckSeparator);
            else
              checkBoxes[key].value = checkBoxes[key].value.join(
                ctx.radioCheckSeparator
              );
          }
        }

        // add plugin info to chunks
        let sharedLabelPlugins = {},
          sharedRelPlugins = {};
        for (let p in this.contextMenuPlugins["sharedBetweenMarkers"]) {
          let cp = this.contextMenuPlugins["sharedBetweenMarkers"][p];
          if (cp.hasOwnProperty("storeFor")) {
            if (cp.storeFor == "label") {
              sharedLabelPlugins[p] = cp;
            } else if (cp.storeFor == "relation") {
              sharedRelPlugins[p] = cp;
            }
          }
        }

        for (let i = 0, len = submittableChunks.length; i < len; i++) {
          if (!submittableChunks[i].hasOwnProperty("extra"))
            submittableChunks[i]["extra"] = {};
          let plugins = this.contextMenuPlugins[submittableChunks[i].label];

          for (let name in plugins) {
            submittableChunks[i]["extra"][name] =
              plugins[name].storage["l" + submittableChunks[i]["id"]] || "";
          }

          for (let name in sharedLabelPlugins) {
            submittableChunks[i]["extra"][name] =
              sharedLabelPlugins[name].storage[
                "l" + submittableChunks[i]["id"]
              ] || "";
          }
        }

        for (let rId in relations) {
          let relObj = {
            links: relations[rId]["links"],
            rule: relations[rId]["rule"],
            extra: {},
          };

          for (let name in sharedRelPlugins) {
            relObj["extra"][name] =
              sharedRelPlugins[name].storage["r" + rId] || "";
          }

          submitRelations.push(relObj);
        }

        return {
          relations: stringify
            ? JSON.stringify(submitRelations)
            : submitRelations,
          chunks: stringify
            ? JSON.stringify(submittableChunks)
            : submittableChunks,
          marker_groups: stringify
            ? JSON.stringify(markerGroups)
            : markerGroups,
          short_text_markers: stringify
            ? JSON.stringify(shortTextMarkers)
            : shortTextMarkers,
          long_text_markers: stringify
            ? JSON.stringify(longTextMarkers)
            : longTextMarkers,
          text_markers: stringify ? JSON.stringify(textMarkers) : textMarkers,
          numbers: stringify ? JSON.stringify(numbers) : numbers,
          ranges: stringify ? JSON.stringify(ranges) : ranges,
          radio: stringify ? JSON.stringify(radioButtons) : radioButtons,
          checkboxes: stringify ? JSON.stringify(checkBoxes) : checkBoxes,
        };
      },
      unmarkChunk: function (c) {
        let label = document.querySelector(
          'span.tag[data-i="' + c["id"] + '"]'
        );
        if (utils.isDefined(label)) {
          let relSpan = label.querySelector("span");
          let delButton = label.querySelector("button");

          if (utils.isDefined(relSpan)) relSpan.remove();
          if (utils.isDefined(delButton)) delButton.remove();

          mergeWithNeighbors(label);
        }
      },
      unmark: function (chunksList) {
        for (let c in chunksList) {
          this.unmarkChunk(chunksList[c]);
        }
      },
      postSubmitHandler: function (batch) {
        this.disableTextLabels();
        relations = {};
        currentRelationId = null;
        lastRelationId = 1;
        labelId = 0;
        // clear svg
        d3.selectAll("svg > *").remove();
        this.showRelationGraph(currentRelationId);
        activeLabels = 0;

        this.checkedOuterRadio = {};
        this.checkedInnerRadio = {};

        chunks.forEach(function (c) {
          if (c.submittable) {
            // means already submitted, so mark as such
            c.submittable = false;
            c.batch = batch;
            c.id = null;
          }
        });
      },
      resetArticle: function () {
        this.selectorArea.innerHTML = resetTextHTML;
      },
      restart: function () {
        chunks = [];
        resetTextHTML = this.selectorArea.innerHTML;
        resetText = this.selectorArea.textContent;

        $(this.textLabelsArea).empty();

        this.initPreMarkers();
        this.updateMarkAllCheckboxes();
      },
      undo: function (batches) {
        let control = this;
        chunks.forEach(function (c) {
          if (batches.includes(c.batch)) {
            if (control.disableSubmittedLabels) {
              control.enableChunk(c);
            }
          }
        });
      },
      updateMarkAllCheckboxes: function () {
        let cnt = countChunksByType();
        $('[data-s] input[type="checkbox"]').prop("disabled", true);
        $('[data-s] input[type="checkbox"]').prop("checked", false);
        for (let i in cnt) {
          if (cnt[i] > 0) {
            $('[data-s="' + i + '"] input[type="checkbox"]').prop(
              "disabled",
              false
            );
          }
        }
      },
      hasNewInputs: function (inputData) {
        return (
          Object.keys(inputData["short_text_markers"]).length ||
          Object.keys(inputData["long_text_markers"]).length ||
          Object.keys(inputData["numbers"]).length ||
          Object.keys(inputData["ranges"]).length ||
          Object.keys(inputData["radio"]).length ||
          Object.keys(inputData["checkboxes"]).length
        );
      },
      hasNewLabels: function (inputData) {
        return (
          inputData["chunks"].length ||
          inputData["relations"].length ||
          inputData["text_markers"].length
        );
      },
      hasNewInfo: function (inputData) {
        return (
          Object.values(inputData["marker_groups"]).filter((x) => x).length ||
          this.hasNewInputs(inputData) ||
          this.hasNewLabels(inputData)
        );
      },
      getMarkerTypes: function () {
        return [
          "chunks",
          "relations",
          "marker_groups",
          "short_text_markers",
          "text_markers",
          "long_text_markers",
          "numbers",
          "ranges",
          "radio",
          "checkboxes",
        ];
      },
      restoreMarkedSpan: function (
        nodeStart,
        nodeEnd,
        spanLabel,
        subValueStart,
        subValueEnd
      ) {
        const range = new Range();

        if (nodeStart == nodeEnd && nodeStart.nodeType === 1) {
          // this means that we mark a nested label, we take -2 to ignore the delete button
          let childLen = nodeStart.childNodes.length;

          for (let idx = 0; idx < childLen - 2; idx++) {
            let diffLen = getNodeLength(nodeStart.childNodes[idx]);
            subValueStart += diffLen;
            subValueEnd += diffLen;
          }

          nodeStart = nodeStart.childNodes[childLen - 2];
          nodeEnd = nodeEnd.childNodes[childLen - 2];
        }

        let rStart = spanLabel["start"] - subValueStart;
        let rEnd = spanLabel["end"] - subValueEnd;

        if (rEnd > getNodeLength(nodeEnd)) {
          console.error(
            "Restoration Error: attempting to mark a span that is larger than the available size"
          );
          return false;
        }

        if (rStart < 0) {
          console.error(
            "Restoration Error: attempting to mark a span that starts before the given text node"
          );
          return false;
        }

        if (nodeStart == nodeEnd && rEnd - rStart < 0) {
          console.error(
            "Restoration Error: attempting to mark a span of size " +
              (rEnd - rStart)
          );
          return false;
        }

        if (nodeStart.tagName == "BR") nodeStart = nodeStart.nextSibling;

        range.setStart(nodeStart, rStart);
        if (
          isScrollablePart(nodeStart.parentNode) &&
          nodeStart.parentNode != nodeEnd.parentNode
        ) {
          // means the label is at the end of the scrollable part
          let scrollableChildren = nodeStart.parentNode.childNodes;
          nodeEnd = scrollableChildren[scrollableChildren.length - 1];
          range.setEndAfter(nodeEnd);
        } else {
          range.setEnd(nodeEnd, rEnd);
        }

        window.getSelection().addRange(range);
        this.updateChunkFromSelection();

        let activeChunk = this.getActiveChunk();
        activeChunk["hash"] = spanLabel["hash"];
        activeChunk["updated"] = false;

        let code = spanLabel["marker"]["code"],
          mmpi = this.markersArea.getAttribute("data-mmpi");
        this.mark(
          this.markersArea.querySelector('.marker[data-s="' + code + '"]'),
          mmpi
        );

        if (spanLabel.undone) {
          this.disableChunk(this.getActiveChunk());
        }
        return true;
      },
      getOverlappingSpans: function (state, spanLabels) {
        return state.processed.map(function (x) {
          let s1 = spanLabels[state.curLabelId],
            s2 = spanLabels[x["id"]];
          return (
            (s1["start"] >= s2["start"] && s1["end"] <= s2["end"]) ||
            (s2["start"] >= s1["start"] && s2["end"] <= s1["end"])
          );
        });
      },
      updateProcessed: function (state, spanLabels, isMultiParagraph) {
        let areOverlapping = this.getOverlappingSpans(state, spanLabels),
          numOverlapping = areOverlapping.reduce((a, b) => a + b, 0);

        if (!utils.isDefined(isMultiParagraph)) isMultiParagraph = false;

        state.processed.push({
          id: state.curLabelId,
          ov: numOverlapping,
          closed: false,
          multip: isMultiParagraph,
        });
        return {
          mask: areOverlapping,
          level: numOverlapping,
        };
      },
      getClosestTextNode: function (
        curNode,
        spanLabel,
        checkStart,
        prevLength
      ) {
        // this operates within paragraph only!
        let cLength = getNodeLength(curNode);
        let errors = 0;

        if (!utils.isDefined(checkStart)) checkStart = true;

        let cAcc = prevLength;
        while (
          curNode !== null &&
          ((checkStart && cAcc + cLength <= spanLabel["start"]) ||
            (!checkStart && cAcc + cLength < spanLabel["end"]))
        ) {
          cAcc += cLength;
          curNode = curNode.nextSibling;
          cLength = utils.isDefined(curNode) ? getNodeLength(curNode) : null;
        }

        if (curNode === null) {
          console.error(
            "Restoration Error: reached the end of the markable, while trying to find the closest text node"
          );
        }

        if (curNode.nodeType == 1) {
          // we are inside the label, find the closest text node inside
          // so the label might end up being an overlapping one,
          // hence find the text node inside the label that fits the best
          return this.getClosestTextNode(
            curNode.childNodes[0],
            spanLabel,
            checkStart,
            cAcc
          );
        }

        return {
          node: curNode,
          acc: cAcc,
          errors: errors,
        };
      },
      restoreNonUnitMarkers: function (non_unit_markers) {
        // restore markers, instantiated with inputs, which do not belong to any unit
        let control = this;
        for (let k in non_unit_markers) {
          for (let i = 0, len = non_unit_markers[k].length; i < len; i++) {
            let el = non_unit_markers[k][i],
              inps,
              vals;
            if (k == "lfree_text")
              inps = control.markersArea.querySelectorAll(
                'textarea[name="' + el.marker.code + '"]'
              );
            else if (k == "radio") {
              if (el.content.includes("||")) {
                inps = control.markersArea.querySelectorAll(
                  'input[type="radio"][name="' +
                    el.marker.code +
                    '_ocat"],' +
                    'input[type="radio"][name="' +
                    el.marker.code +
                    '"]'
                );
                vals = el.content.split(control.radioCheckSeparator);
              } else {
                inps = control.markersArea.querySelectorAll(
                  'input[type="radio"][name="' + el.marker.code + '"]'
                );
              }
            } else if (k == "check") {
              inps = control.markersArea.querySelectorAll(
                'input[type="checkbox"][name="' + el.marker.code + '"]'
              );
              vals = el.content.split(control.radioCheckSeparator);
            } else
              inps = control.markersArea.querySelectorAll(
                'input[name="' + el.marker.code + '"]'
              );
            if (inps) {
              for (let i = 0, linps = inps.length; i < linps; i++) {
                let inp = inps[i];
                inp.setAttribute("data-h", el.hash);
                if (k == "radio") {
                  if (utils.isDefined(vals)) {
                    for (let j = 0, lv = vals.length; j < lv; j++) {
                      if (inp.value == vals[j]) {
                        inp.checked = true;
                      }
                    }
                  }
                  if (inp.value == el.content) {
                    inp.checked = true;
                    if (inp.hasAttribute("data-group")) {
                      let outerRadio = control.markersArea.querySelector(
                        "#" + inp.getAttribute("data-group")
                      );

                      if (utils.isDefined(outerRadio))
                        outerRadio.checked = true;
                    }
                  }
                } else if (k == "check") {
                  if (vals.includes(inp.value)) inp.checked = true;
                } else {
                  inp.value = el.content;
                }

                if (inp.getAttribute("type") == "range") {
                  let event = new Event("input");
                  inp.dispatchEvent(event);
                }
              }
            }
          }
        }
      },
      restoreTextMarkers: function (text_labels) {
        let control = this;
        for (let i = 0, len = text_labels.length; i < len; i++) {
          let lab = control.markersArea.querySelector(
            'input[name="' + text_labels[i].marker.code + '"]'
          );
          if (lab) {
            control.select(lab, text_labels[i].hash);
          }
        }
      },
      restoreSpanMarkers: function (span_labels) {
        let state = {
          acc: 0, // the accumulator variable, pointing at where the current text node starts
          curLabelId: 0, // id of the current label
          processed: [], // labels that are not nested into one another
          c2i: {}, // mapping between internal labels and those on the webpage
          multip: {}, // multi-paragraph nodes are stored here
          numInner: {},
          likelyErrors: 0,
        };
        let numLabels = span_labels.length,
          cnodes = this.selectorArea.childNodes,
          control = this;

        // Step 1: define the order of re-labeling
        // - from top to bottom
        // - starting from the outer ones to the inner ones
        span_labels.sort(function (x, y) {
          if (x["start"] == y["start"]) {
            // otherwise, by length, with longest coming first
            return y["end"] - y["start"] - (x["end"] - x["start"]);
          } else {
            // by default sort by a starting coordinate
            // with earliest coming first
            return x["start"] - y["start"];
          }
        });

        // Step 2: unfold scrollable and skip pinned parts
        let flatCnodes = [],
          acceptClassNames = ["scrollable"],
          skipClassNames = ["pinned"];
        for (let i = 0, len = cnodes.length; i < len; i++) {
          if (skipClassNames.includes(cnodes[i].className)) continue;
          if (
            cnodes[i].tagName === "DIV" &&
            acceptClassNames.includes(cnodes[i].className)
          ) {
            for (let j = 0, len2 = cnodes[i].childNodes.length; j < len2; j++) {
              flatCnodes.push(cnodes[i].childNodes[j]);
            }
          }
        }
        if (flatCnodes.length > 0) cnodes = flatCnodes;

        // Step 3: actually labeling
        // - labels within one paragraph are rendered directly as they are
        // - multi-paragraph labels (and those dependent on them) are rendered asap
        // - rendering should happen from the outer to the inner ones, from top to bottom
        for (let cId = 0, len = cnodes.length; cId < len; cId++) {
          state.numInner[cId] = 0;
          if (
            state.curLabelId < numLabels ||
            Object.keys(state.multip).length > 0
          ) {
            let cnodeLength = getNodeLength(cnodes[cId]);
            if (cnodes[cId].tagName === "BR") {
              for (let candLabelId in state.multip) {
                if (!state.processed[candLabelId].closed) {
                  state.multip[candLabelId].parBreaks.push(state.acc);
                }
              }
            }

            // Attempt to close a multi-paragraph marking
            let keys2del = [];
            for (let candLabelId in state.multip) {
              if (state.acc + cnodeLength >= span_labels[candLabelId]["end"]) {
                // if the candLabelId label ends within this paragraph,
                // we found the suitable paragraph to render it!
                let multiData = state.multip[candLabelId],
                  startInfo = multiData["start"];

                // TODO: return here
                let startSearchRes = control.getClosestTextNode(
                  cnodes[startInfo["nodeId"]],
                  span_labels[candLabelId],
                  true,
                  startInfo["innerAcc"]
                );
                let endSearchRes = control.getClosestTextNode(
                  cnodes[cId],
                  span_labels[candLabelId],
                  false,
                  state.acc
                );
                state.errors += startSearchRes.errors + endSearchRes.errors;

                let hasRestored = control.restoreMarkedSpan(
                  startSearchRes.node,
                  endSearchRes.node,
                  span_labels[candLabelId],
                  startSearchRes.acc,
                  endSearchRes.acc
                );

                if (hasRestored) {
                  state.c2i[candLabelId] = control.getActiveChunk().id;
                  state.processed[candLabelId].closed = true;
                  state.numInner[cId]++;
                  keys2del.push(candLabelId);

                  for (let dId in multiData.delayed) {
                    // need to re-select tagItem on account of
                    // having added new spans in the previous iteration
                    let tagItem = document.querySelector(
                      'span.tag[data-i="' + state.c2i[candLabelId] + '"]'
                    );
                    let tagNodes = tagItem.childNodes;

                    let dInfo = multiData.delayed[dId];
                    let dStart =
                      span_labels[dInfo.id]["start"] - startInfo["innerAcc"];
                    let dEnd =
                      span_labels[dInfo.id]["end"] - startInfo["innerAcc"];
                    let dAcc = 0,
                      dStartNode = undefined,
                      dEndNode = undefined,
                      dStartNodeDefined = false,
                      dEndNodeDefined = false,
                      dStartAcc = 0,
                      dEndAcc = 0;

                    let pOffsetId = 0;
                    for (let idt = 0; idt < tagNodes.length - 1; idt++) {
                      let curIdtLength = getNodeLength(tagNodes[idt]);

                      // this is most probably <br>, which was already accounted for
                      if (curIdtLength === 0) continue;

                      if (
                        pOffsetId >= 0 &&
                        dAcc + curIdtLength + startInfo["innerAcc"] >=
                          multiData.parBreaks[pOffsetId]
                      ) {
                        curIdtLength += 1;
                        if (pOffsetId + 1 < multiData.parBreaks.length)
                          pOffsetId++;
                        else pOffsetId = -100;
                      }

                      if (!dStartNodeDefined && dStart < dAcc + curIdtLength) {
                        dStartNode = tagNodes[idt];
                        dStartNodeDefined = true;
                        dStartAcc = dAcc;
                      }
                      if (!dEndNodeDefined && dEnd <= dAcc + curIdtLength) {
                        dEndNode = tagNodes[idt];
                        dEndNodeDefined = true;
                        dEndAcc = dAcc;
                      }

                      if (dStartNodeDefined && dEndNodeDefined) break;
                      dAcc += curIdtLength;
                    }

                    if (
                      utils.isDefined(dStartNode) &&
                      utils.isDefined(dEndNode)
                    ) {
                      let isRestored = control.restoreMarkedSpan(
                        dStartNode,
                        dEndNode,
                        span_labels[dInfo.id],
                        dStartAcc + startInfo["innerAcc"],
                        dEndAcc + startInfo["innerAcc"]
                      );

                      if (isRestored) {
                        state.c2i[dInfo.id] = control.getActiveChunk().id;

                        state.processed[dId].closed = true;
                      } else {
                        state.likelyErrors++;
                      }
                    }
                  }
                } else {
                  state.likelyErrors++;
                }
              }
            }

            for (let keyId in keys2del) delete state.multip[keys2del[keyId]];

            if (
              state.curLabelId >= numLabels &&
              Object.keys(state.multip).length == 0
            )
              break;

            if (
              utils.isDefined(span_labels[state.curLabelId]) &&
              state.acc + cnodeLength > span_labels[state.curLabelId]["start"]
            ) {
              // If the current markable starts within the current paragraph,
              // we might have found an element to mark!

              // an inner accumulator to keep track of the beginning of the next available text node within this paragraph
              let innerAcc = state.acc;

              while (
                span_labels[state.curLabelId]["end"] >
                  state.acc + cnodeLength &&
                state.acc + cnodeLength > span_labels[state.curLabelId]["start"]
              ) {
                // while the end of the current markable is not within the current paragraph,
                // but the beginning of the markable is, keep iterating until finding
                // a markable, which does not satisfy any one of the conditions
                //
                // If we are within this while-loop, it means it's a multi-paragraph node
                // record this node keep iterating

                let overlap = control.updateProcessed(
                  state,
                  span_labels,
                  true // isMultiParagraph
                );

                if (overlap.level === 0) {
                  state.multip[state.curLabelId] = {
                    start: {
                      nodeId: cId,
                      innerAcc: innerAcc,
                    },
                    parBreaks: [], // where we store the breakpoints for the paragraphs, which this markable spans over
                    delayed: [], // here we store nodes with rendering being delayed, because this multip-node was not been able to render
                  };
                } else {
                  for (let i in overlap.mask) {
                    if (overlap.mask[i]) {
                      let proc = state.processed[i];
                      if (proc.multip && !proc.closed) {
                        state.multip[proc["id"]].delayed.push({
                          id: state.curLabelId,
                          acc: innerAcc,
                        });
                      }
                    }
                  }
                }

                state.curLabelId++;
                state.numInner[cId]++;
                if (state.curLabelId >= numLabels) break;
              }

              if (
                state.curLabelId >= numLabels ||
                state.acc + cnodeLength < span_labels[state.curLabelId]["start"]
              ) {
                // if the current markable is suddenly out of the current paragraph's bounds,
                // advance the accumulator and move on
                //
                // NOTE: typically, advancing is done at the end of the loop's iteration,
                //       but here we force the iteration to finish, hence the update
                state.acc += cnodeLength;
                continue;
              }

              while (
                state.curLabelId < numLabels &&
                span_labels[state.curLabelId]["end"] <= state.acc + cnodeLength
              ) {
                // If the current markable ends within bounds of this paragraph,
                // we attempt to render all nodes within this paragraph.
                // NOTE: some of them are impossible to render, because
                //       their parents are multi-paragraph nodes,
                //       in which case, store them as delayed
                let overlap = control.updateProcessed(
                  state,
                  span_labels,
                  false
                );

                let startNode = undefined,
                  endNode = undefined;
                if (overlap.level === 0) {
                  // if no overlap, just select the text node and proceed
                  if (cnodes[cId].nodeType === 1) {
                    if (cnodes[cId].childNodes.length == 1) {
                      // this is the usual case when the only node is a text node
                      startNode = cnodes[cId].childNodes[0];
                      endNode = startNode;
                    } else {
                      // if we have more than 1 node, things get complicated
                      // because suddenly we have many candidate nodes
                      // and furthermore, the label can start in one of them
                      // and finish in another node
                      startNode = control.getClosestTextNode(
                        cnodes[cId].childNodes[0],
                        span_labels[state.curLabelId],
                        true,
                        state.acc
                      );

                      endNode = control.getClosestTextNode(
                        cnodes[cId].childNodes[0],
                        span_labels[state.curLabelId],
                        false,
                        state.acc
                      );
                      state.likelyErrors += startNode.errors + endNode.errors;
                    }
                  } else {
                    startNode = control.getClosestTextNode(
                      cnodes[cId],
                      span_labels[state.curLabelId],
                      true,
                      state.acc
                    );

                    endNode = control.getClosestTextNode(
                      cnodes[cId],
                      span_labels[state.curLabelId],
                      false,
                      state.acc
                    );
                    state.likelyErrors += startNode.errors + endNode.errors;
                  }
                } else {
                  // if there is an overlap, find a parent,
                  // by finding a markable with the closest
                  // enclosing boundaries
                  let minDistId = undefined,
                    minDist = Infinity,
                    sameLevelDist = Infinity,
                    sameLevelId = undefined;

                  overlap.mask.forEach(function (hasOverlap, i) {
                    let label = span_labels[state.processed[i]["id"]],
                      dist =
                        Math.abs(
                          label["end"] - span_labels[state.curLabelId]["end"]
                        ) +
                        Math.abs(
                          label["start"] -
                            span_labels[state.curLabelId]["start"]
                        );

                    if (hasOverlap) {
                      if (
                        dist < minDist &&
                        state.processed[i]["ov"] == overlap.level - 1
                      ) {
                        minDist = dist;
                        minDistId = state.processed[i]["id"];
                      }
                    }
                    if (
                      dist < sameLevelDist &&
                      state.processed[i]["ov"] == overlap.level &&
                      !state.processed[i]["closed"]
                    ) {
                      sameLevelDist = dist;
                      sameLevelId = state.processed[i]["id"];
                    }
                  });

                  if (utils.isDefined(minDistId)) {
                    // if it was found, grab the appropriate text node
                    let searchId = state.c2i[minDistId],
                      tagItem = utils.isDefined(searchId)
                        ? document.querySelector(
                            'span.tag[data-i="' + searchId + '"]'
                          )
                        : undefined;

                    if (utils.isDefined(tagItem)) {
                      let tagNodes = tagItem.childNodes;
                      let prevLength = previousTextLength(tagNodes[0]);
                      startNode = control.getClosestTextNode(
                        tagNodes[0],
                        span_labels[state.curLabelId],
                        true,
                        prevLength
                      );
                      endNode = control.getClosestTextNode(
                        tagNodes[0],
                        span_labels[state.curLabelId],
                        false,
                        prevLength
                      );

                      // this is to render nodes that are nested on the same level
                      if (
                        state.numInner[cId] !== 0 &&
                        utils.isDefined(sameLevelId)
                      ) {
                        for (let i = 0; i <= state.curLabelId; i++) {
                          if (overlap.level < state.processed[i]["ov"]) {
                            state.processed[i]["closed"] = true;
                          }
                        }

                        if (span_labels[sameLevelId]["end"] > innerAcc) {
                          innerAcc = span_labels[sameLevelId]["end"];
                        }
                      }
                    } else if (!state.processed[minDistId].closed) {
                      // if current label depends on rendering a non-closed label,
                      // the non-closed one is either multi-paragraph (1st if)
                      // or depends on a multi-paragraph (2nd if)
                      if (state.processed[minDistId].multip) {
                        state.multip[minDistId].delayed.push({
                          id: state.curLabelId,
                          acc: innerAcc,
                        });
                      } else {
                        for (let candMaster in state.multip) {
                          if (
                            state.multip[candMaster].delayed
                              .map((x) => x.id)
                              .includes(minDistId)
                          ) {
                            state.multip[candMaster].delayed.push({
                              id: state.curLabelId,
                              acc: innerAcc,
                            });
                            break;
                          }
                        }
                      }
                    }
                  } else {
                    // if it's not defined, find the closest of the split nodes
                    let searchRes = control.getClosestTextNode(
                      cnodes[cId],
                      span_labels[state.curLabelId],
                      true,
                      state.acc
                    );
                    startNode = searchRes;
                    endNode = startNode;
                    innerAcc = searchRes.acc;
                    state.likelyErrors += searchRes.errors;
                  }
                }

                if (utils.isDefined(startNode) && utils.isDefined(endNode)) {
                  // the only case when we don't come here
                  // is when the parent is a multi-paragraph label
                  // this is handled separately
                  let hasRestored = control.restoreMarkedSpan(
                    startNode.node,
                    endNode.node,
                    span_labels[state.curLabelId],
                    startNode.acc,
                    endNode.acc
                  );

                  if (hasRestored) {
                    state.numInner[cId]++; // a default counter for labels within this paragraph, nested or not
                    state.c2i[state.curLabelId] = control.getActiveChunk().id;
                    innerAcc = span_labels[state.curLabelId]["start"];
                  } else {
                    state.likelyErrors++;
                  }
                }

                state.curLabelId++;
              }
            }
            state.acc += cnodeLength;
          } else {
            break;
          }
        }

        if (state.likelyErrors > 0) {
          alert(
            "The annotations are likely to be restored incorrectly.\nPlease do NOT submit any edits for these annotations\nand report this by clicking the red flag button\nnear the selected annotation button."
          );
        }
      },
      getCurrentDatasource: function () {
        return this.selectorArea.getAttribute("data-s");
      },
      getCurrentDatapoint: function () {
        return this.selectorArea.getAttribute("data-dp");
      },
      restoreBatch: function (uuid, url) {
        let control = this;
        if (utils.isDefined(url)) {
          $.ajax({
            method: "GET",
            url: url,
            data: {
              uuid: uuid,
            },
            success: function (d) {
              control.clearBatch();
              control.postSubmitHandler();

              chunks = [];

              editingBatch = uuid;

              if (!utils.isDefined(originalConfig)) {
                originalConfig = {
                  "data-s": control.getCurrentDatasource(),
                  "data-dp": control.getCurrentDatapoint(),
                  resetText: resetText,
                  resetTextHTML: resetTextHTML,
                };
              }

              control.selectorArea.setAttribute("data-s", d.context.ds_id);
              control.selectorArea.setAttribute("data-dp", d.context.dp_id);
              control.selectorArea.innerHTML = d.context.content;
              control.restart();

              control.restoreNonUnitMarkers(d.non_unit_markers);
              control.restoreTextMarkers(d.text_labels);
              control.restoreSpanMarkers(d.span_labels);
            },
            error: function () {
              console.log("ERROR!");
            },
          });
        }
      },
      clearBatch: function () {
        $(this.markersArea)
          .find(
            'input[type="text"],input[type="radio"],input[type="checkbox"],textarea'
          )
          .each(function (i, x) {
            x.removeAttribute("data-h");
            if (x.type != "radio" && x.type != "checkbox") x.value = "";
            if (x.type == "radio" || x.type == "checkbox") x.checked = false;
          });
        $(this.markerGroupsArea)
          .find(
            '#markerGroups input[type="text"],input[type="radio"],input[type="checkbox"]'
          )
          .each(function (i, x) {
            x.removeAttribute("data-h");
            if (x.type != "radio" && x.type != "checkbox") x.value = "";
            if (x.type == "radio" || x.type == "checkbox") x.checked = false;
          });
      },
      restoreOriginal: function () {
        editingBatch = undefined;
        if (utils.isDefined(originalConfig)) {
          this.selectorArea.setAttribute("data-s", originalConfig["data-s"]);
          this.selectorArea.setAttribute("data-dp", originalConfig["data-dp"]);
          resetText = originalConfig["resetText"];
          resetTextHTML = originalConfig["resetTextHTML"];

          this.selectorArea.innerHTML = resetTextHTML;
          originalConfig = undefined;
          this.postSubmitHandler();
          this.restart();
        }
      },
      getEditingBatch: function () {
        return editingBatch;
      },
      changeBatchFlag: function (uuid, url, flag, csrfValue, callback) {
        $.ajax({
          method: "POST",
          url: url,
          dataType: "json",
          data: {
            csrfmiddlewaretoken: csrfValue,
            uuid: uuid,
            flag: flag,
          },
          success: function (data) {
            if (data.errors) console.log("Caught errors!");
            else callback();
          },
          error: function () {
            console.log("ERROR!");
          },
        });
      },
    };
    return labeler;
  })();

  $(document).ready(function () {
    labelerModule.init();

    /**
     * Labeler plugins
     */
    let labelerPluginsDOM = document.querySelector("#labelerPlugins"),
      labelerPlugins = JSON.parse(labelerPluginsDOM.textContent);
    for (let markerShort in labelerPlugins) {
      for (let i = 0, len = labelerPlugins[markerShort].length; i < len; i++) {
        let pluginCfg = labelerPlugins[markerShort][i];
        $.getScript(
          labelerPluginsDOM.getAttribute("data-url") + pluginCfg["file"],
          (function (cfg, ms) {
            return function () {
              // plugin variable will be defined in each of plugin files
              labelerModule.register(plugin(cfg, labelerModule), ms);
            };
          })(pluginCfg, markerShort)
        );
        labelerModule.expectToRegister();
      }
    }

    // disable the undo button, since we haven't submitted anything
    $("#undoLast").attr("disabled", true);

    // undo last relation/label if the button is clicked
    $("#undoLast").on("click", function (e) {
      e.preventDefault();
      let $target = $("#undoLast");

      $.ajax({
        method: "POST",
        url: $target.attr("data-url"),
        dataType: "json",
        data: {
          csrfmiddlewaretoken: $target
            .closest("form")
            .find('input[name="csrfmiddlewaretoken"]')
            .val(),
        },
        success: function (data) {
          labelerModule.undo(data.batch);

          let $submitted = $("#submittedTotal"),
            $submittedToday = $("#submittedToday");

          $submitted.text(data["submitted"]);
          $submitted.append($('<span class="smaller">q</span>'));

          $submittedToday.text(data["submitted_today"]);
          $submittedToday.append($('<span class="smaller">q</span>'));

          $(labelerModule.submitForm)
            .find('input[type="text"]')
            .val(data["input"]);
        },
        error: function () {
          console.log("ERROR!");
        },
      });
    });

    function getNewText(confirmationCallback, $button, saveForLater) {
      let confirmation = confirmationCallback();
      $button.attr("disabled", true);

      if (!utils.isDefined(saveForLater)) saveForLater = false;

      if (confirmation) {
        let $el = $(labelerModule.selectorArea);
        $el.addClass("is-loading");

        $.ajax({
          type: "POST",
          url: $button.attr("href"),
          dataType: "json",
          data: {
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
            sId: $el.attr("data-s"),
            dpId: $el.attr("data-dp"),
            saveForLater: saveForLater,
          },
          success: function (d) {
            // update text, source id and datapoint id
            $el.attr("data-s", d.dp_info.source_id);
            $el.attr("data-dp", d.dp_info.id);
            let dpName = $("#dpName");
            if (dpName.text()) {
              dpName.text("(" + d.dp_info.source_name + ")");
            }

            let $selector = $(labelerModule.selectorArea);

            if (d.dp_info.is_empty) {
              let $text = $selector.closest("article.text");
              if ($text) {
                $text.removeClass("text");
              }

              // TODO: great_job image path should be dynamic
              $selector.html(d.text);
              $text.siblings("article").remove();

              $(labelerModule.markersArea).remove();
              $(labelerModule.relationsArea).remove();
              $(labelerModule.markerGroupsArea).remove();
              $(labelerModule.actionsArea).remove();
            } else {
              $selector.html(d.text);
              labelerModule.restart();
              $("#undoLast").attr("disabled", true);
              $button.attr("disabled", false);
            }
            $("#markerGroups input").each(function (i, x) {
              $(x).val("");
            });
            $el.removeClass("is-loading");
          },
          error: function () {
            console.log("ERROR!");
            $el.removeClass("is-loading");
            $button.attr("disabled", false);
          },
        });
      } else {
        $button.attr("disabled", false);
      }
    }

    // TODO(dmytro):
    // - after the relationship is submitted, the ID starts over, whereas old ID is still there - confusing
    // - making labels in relationships transparent works very poorly for nested labels, so think of another way

    // submitting the marked labels and/or relations with(out) inputs
    $(labelerModule.submitForm)
      .find('a[data-type="submit"]')
      .on("click", function (e) {
        e.preventDefault();

        // check if restrictions are violated
        if (!labelerModule.checkRestrictions()) return;

        let $inputForm = $(labelerModule.submitForm);

        let inputFormData = $inputForm.serializeObject();

        // if there's an input form field, then create input_context
        // the reason why we use `false` as a param to getContextText
        // (which makes us rely on `textContent` instaed of `innerText`)
        // is because sometimes browser will auto-correct small mistakes
        // like double spaces, which are present in the data,
        // but when .surroundContext happens, it does so on the TEXT_NODE
        // which contains the original uncorrected text.
        // The flip-side of the problem is that `textContent` removes
        // the newlines, unlike `innerText`, but this is handled inside
        // the `getContextText` function
        inputFormData["context"] = labelerModule.getContextText(false);

        $.extend(inputFormData, labelerModule.getSubmittableDict());

        inputFormData["datasource"] = parseInt(
          labelerModule.getCurrentDatasource(),
          10
        );
        inputFormData["datapoint"] = parseInt(
          labelerModule.getCurrentDatapoint(),
          10
        );

        let editPageBtn = document.querySelector(
          "#editingBoard a[data-page].is-current"
        );

        if (utils.isDefined(editPageBtn))
          inputFormData["p"] = editPageBtn.getAttribute("data-page");

        if (labelerModule.hasNewInfo(inputFormData)) {
          labelerModule.getMarkerTypes().forEach(function (x) {
            inputFormData[x] = JSON.stringify(inputFormData[x]);
          });

          if (inputFormData["mode"] == "e" || inputFormData["mode"] == "rev") {
            inputFormData["batch"] = labelerModule.getEditingBatch();

            let mode = utils.expandMode(inputFormData["mode"]);

            let searchForm = document.querySelector("#" + mode + "SearchForm");
            if (utils.isDefined(searchForm)) {
              let searchData = $(searchForm).serializeObject();
              for (let key in searchData) inputFormData[key] = searchData[key];

              if (inputFormData["random"] == "on") {
                // we want to keep exactly the same batches shown then
                inputFormData["batch_ids"] = Array.from(
                  document.querySelectorAll('li[data-mode="e"]')
                ).map((x) => x.getAttribute("data-id"));
              }
            }

            let curPage;
            if (inputFormData["mode"] == "e") {
              curPage = labelerModule.currentPage["editing"];
            } else if (inputFormData["mode"] == "rev") {
              curPage = labelerModule.currentPage["reviewing"];
            }

            if (utils.isDefined(curPage)) inputFormData["p"] = curPage;
          }

          $.ajax({
            method: "POST",
            url: $inputForm.attr("action"),
            dataType: "json",
            data: inputFormData,
            success: function (data) {
              if (data["error"] === false) {
                if (data["mode"] == "r") {
                  if (labelerModule.disableSubmittedLabels)
                    labelerModule.disableChunks(
                      JSON.parse(inputFormData["chunks"])
                    );
                  else
                    labelerModule.unmark(JSON.parse(inputFormData["chunks"]));

                  $(labelerModule.markersArea)
                    .find("textarea")
                    .each(function (i, x) {
                      $(x).val("");
                    });
                  $(labelerModule.markerGroupsArea)
                    .find("#markerGroups textarea")
                    .each(function (i, x) {
                      $(x).val("");
                    });
                  $(labelerModule.markersArea)
                    .find("input")
                    .each(function (i, x) {
                      if (
                        x.type != "radio" &&
                        x.type != "checkbox" &&
                        x.type != "submit" &&
                        x.type != "hidden"
                      )
                        x.value = "";
                      if (x.type == "radio" || x.type == "checkbox")
                        x.checked = false;
                    });
                  $(labelerModule.markersArea)
                    .find("output")
                    .each(function (i, x) {
                      $(x).text("???");
                    }); // labels for input[type="range"]
                  $(labelerModule.markerGroupsArea)
                    .find("#markerGroups input")
                    .each(function (i, x) {
                      $(x).val("");
                    });
                  $(labelerModule.markerGroupsArea)
                    .find("output")
                    .each(function (i, x) {
                      $(x).text("???");
                    }); // labels for input[type="range"]
                  if (data["trigger_update"] === true) {
                    getNewText(function () {
                      return true;
                    }, $("#getNewArticle"));
                  }
                } else if (data["mode"] == "e" || data["mode"] == "rev") {
                  let mode = data["mode"] == "e" ? "editing" : "reviewing";
                  let closestPsArea = document.querySelector(
                    "#" + mode + "Board"
                  );
                  let batch = null; // current batch
                  let nextBatchId = null;

                  let seqEditingHandle =
                    document.querySelector("#sequentialEditing");
                  let isSequentialEditing =
                    utils.isDefined(seqEditingHandle) &&
                    seqEditingHandle.checked;

                  // Select next batch to be edited
                  if (isSequentialEditing) {
                    batch = closestPsArea.querySelector(
                      '[data-id="' + labelerModule.getEditingBatch() + '"]'
                    );
                    let nextBatch = batch.nextElementSibling;
                    if (utils.isDefined(nextBatch))
                      nextBatchId = nextBatch.getAttribute("data-id");
                  } else {
                    nextBatchId = labelerModule.getEditingBatch();
                  }

                  if (data.partial) {
                    let mainPart = closestPsArea.querySelector("main");
                    mainPart.innerHTML = data.template;
                  } else {
                    closestPsArea.outerHTML = data.template;
                  }

                  batch = closestPsArea.querySelector(
                    '[data-id="' + labelerModule.getEditingBatch() + '"]'
                  );
                  if (utils.isDefined(batch)) batch.classList.add("is-hovered");
                  let item = data["mode"] == "e" ? "edit" : "review";
                  alert("Your " + item + " is successfully saved!");

                  if (isSequentialEditing) {
                    if (utils.isDefined(nextBatchId)) {
                      let nextBatch = closestPsArea.querySelector(
                        '[data-id="' + nextBatchId + '"]'
                      );
                      if (utils.isDefined(nextBatch)) {
                        nextBatch.click();
                        if (utils.isDefined(labelerModule.ui.collapsibles))
                          labelerModule.ui.collapsibles.forEach(
                            function (inst) {
                              if (inst.element.id == "editingBody") {
                                inst.collapse();
                              }
                            }
                          );
                      } else
                        alert(
                          "Error during editing, please, do NOT edit more before contacting your system administrator!"
                        );
                    } else
                      alert(
                        "You have finished the page! Please choose a new one."
                      );
                  } else {
                    batch.scrollIntoView();
                  }
                }
              }

              // TODO; trigger iff .countdown is present
              // $('.countdown').trigger('cdAnimateStop').trigger('cdAnimate');

              labelerModule.postSubmitHandler(data.batch);

              $("#undoLast").attr("disabled", false);
            },
            error: function () {
              console.log("ERROR!");
              $("#undoLast").attr("disabled", true);
              // $('.countdown').trigger('cdAnimateReset').trigger('cdAnimate');
            },
          });
        }
      });

    // get a new article from the data source(s)
    $("#getNewArticle").on("click", function (e) {
      e.preventDefault();

      let $button = $(this);

      if ($button.attr("disabled")) return;

      // TODO: should I also count relations here?
      getNewText(function () {
        let confirmationText =
          "All your unsubmitted annotations will be removed. Are you sure?";
        return labelerModule.countUnsubmittedChunks() > 0
          ? confirm(confirmationText)
          : true;
      }, $button);
    });

    $("#skipForLater").on("click", function (e) {
      e.preventDefault();

      let $button = $(this);

      if ($button.attr("disabled")) return;

      // TODO: should I also count relations here?
      getNewText(
        function () {
          let confirmationText =
            "You chose to save this text for later. All your unsubmitted annotations will be removed. Are you sure?";
          return labelerModule.countUnsubmittedChunks() > 0
            ? confirm(confirmationText)
            : true;
        },
        $button,
        true
      );
    });

    // get a new article from the data source(s)
    $("#finishRound").on("click", function (e) {
      e.preventDefault();

      let $button = $(this);

      if ($button.attr("disabled")) return;

      getNewText(function () {
        let confirmationText =
          "Are you sure that you have completed the task to the best of your ability?";
        return confirm(confirmationText);
      }, $button);
    });

    $("#flagTextButton").on("click", function () {
      $(".flag.modal").addClass("is-active");
    });

    $("#flagTextForm").on("submit", function (e) {
      e.preventDefault();
      let $form = $("#flagTextForm");

      let data = $form.serializeObject();
      let csrf = data["csrfmiddlewaretoken"];

      if (data.hasOwnProperty("csrfmiddlewaretoken"))
        delete data["csrfmiddlewaretoken"];

      let keys = Object.keys(data);
      for (let i = 0, len = keys.length; i < len; i++) {
        if (
          (typeof data[keys[i]] === "string" ||
            data[keys[i]] instanceof String) &&
          !data[keys[i]].trim()
        ) {
          delete data[keys[i]];
        }
      }

      $.ajax({
        type: $form.attr("method"),
        url: $form.attr("action"),
        dataType: "json",
        data: {
          csrfmiddlewaretoken: csrf,
          feedback: JSON.stringify(data),
          ds_id: labelerModule.getCurrentDatasource(),
          dp_id: labelerModule.getCurrentDatapoint(),
        },
        success: function () {
          //alert("Thank you for your feedback!");
          $(".flag.modal").removeClass("is-active");
          $form.find("textarea").each(function (i, x) {
            $(x).val("");
          });
          $form.find("input").each(function (i, x) {
            if (
              x.type != "radio" &&
              x.type != "checkbox" &&
              x.type != "submit" &&
              x.type != "hidden"
            )
              x.value = "";
            if (x.type == "radio" || x.type == "checkbox") x.checked = false;
          });
          // getNewText(function () {
          //   return true;
          // }, $("#getNewArticle"));
        },
        error: function () {
          alert("Your feedback was not recorded. Please try again later.");
        },
      });
    });

    $("#prevRelation").on("click", function (e) {
      e.preventDefault();
      labelerModule.showRelationGraph(labelerModule.previousRelation());
    });

    $("#nextRelation").on("click", function (e) {
      e.preventDefault();
      labelerModule.showRelationGraph(labelerModule.nextRelation());
    });

    $("#removeRelation").on("click", function (e) {
      e.preventDefault();
      labelerModule.showRelationGraph(labelerModule.removeCurrentRelation());
    });

    function adjustModeWindow(e, actionTitle, callbackOk, callbackData) {
      let $target = $(e.target).closest("a"),
        mode = $target.attr("data-mode");

      if (!utils.isDefined(callbackOk)) callbackOk = function () {};

      if (!utils.isDefined(callbackData))
        callbackData = function () {
          return {};
        };

      let isOk =
        mode != "o" ||
        confirm(
          "Any unsaved annotations on the current text will be lost. Proceed?"
        );

      if (isOk) {
        let $lastCol = $(labelerModule.taskArea).find(".column:last");

        if (mode === "o") {
          $.ajax({
            type: "GET",
            url: $target.attr("href"),
            dataType: "json",
            data: callbackData(),
            success: function (d) {
              $lastCol.prepend(d.template);
              callbackOk($target, $lastCol, mode);
              $target.attr("data-mode", "c");
              $target.empty();
              $target.append(
                $(
                  "<span class='icon'><i class='fas fa-times-circle'></i></span>"
                )
              );
              $target.append(
                $(
                  "<span>" +
                    utils.title(django.gettext("stop " + actionTitle)) +
                    "</span>"
                )
              );

              labelerModule.ui.initCollapsibles();
            },
            error: function () {
              console.log("Error while invoking " + actionTitle + " mode!");
            },
          });
        } else if (mode === "c") {
          $target.attr("data-mode", "o");
          $target.empty();
          callbackOk($target, $lastCol, mode);

          labelerModule.currentPage[mode] = null;

          labelerModule.ui.collapsibles = null;

          labelerModule.restoreOriginal();
          labelerModule.clearBatch();
          labelerModule.fixUI();
        }
      }
    }

    $("#editingModeButton").on("click", function (e) {
      e.preventDefault();
      adjustModeWindow(e, "editing", function ($target, $lastCol, mode) {
        if (mode === "o") {
          $(labelerModule.submitForm).find("input[name='mode']").val("e");
        } else if (mode === "c") {
          $lastCol.find("#editingBoard").remove();
          $(labelerModule.submitForm).find("input[name='mode']").val("r");
          $target.append(
            $("<span class='icon'><i class='fas fa-edit'></i></span>")
          );
          $target.append(
            $("<span>" + utils.title(django.gettext("edit")) + "</span>")
          );
        }
      });
    });

    $("#reviewingModeButton").on("click", function (e) {
      e.preventDefault();
      adjustModeWindow(
        e,
        "reviewing",
        function ($target, $lastCol, mode) {
          if (mode === "o") {
            $(labelerModule.submitForm).find("input[name='mode']").val("rev");
          } else if (mode == "c") {
            $lastCol.find("#reviewingBoard").remove();
            $target.append(
              $("<span class='icon'><i class='fas fa-pencil-ruler'></i></span>")
            );
            $target.append(
              $("<span>" + utils.title(django.gettext("review")) + "</span>")
            );
          }
        },
        function () {
          return {
            ds: labelerModule.getCurrentDatasource(),
            dp: labelerModule.getCurrentDatapoint(),
          };
        }
      );
    });
  });
})(
  window.jQuery,
  window.d3,
  window.tippy,
  window.django,
  window.bulmaCollapsible
);
