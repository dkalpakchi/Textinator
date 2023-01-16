(function ($, JSONEditor) {
  const utils = {
    isDefined: function (n) {
      return n !== undefined && n !== null;
    },
    title: function (string) {
      return string.charAt(0).toUpperCase() + string.slice(1);
    },
    setUnion: function (setA, setB) {
      let _union = new Set(setA);
      for (const elem of setB) {
        _union.add(elem);
      }
      return _union;
    },
    parseComments: function (line) {
      let l = line.replace(combinator.commentSymbol, "").trim();
      let o = {};
      let parts = l.split(";");

      for (let i = 0, len = parts.length; i < len; i++) {
        let fields = parts[i].split(":");
        o[fields[0].trim()] = fields[1].trim();
      }
      return o;
    },
    stringifyComments: function (obj) {
      let s = "";
      let keys = Object.keys(obj);
      for (let i = 0, len = keys.length; i < len; i++) {
        s += keys[i] + ": " + obj[keys[i]];
        if (i != len - 1) s += "; ";
      }
      return s;
    },
  };

  const db = {
    saveRule: function (op) {
      // saves a tentative rule to DB, so that it becomes permanent
      if (!utils.isDefined(op)) op = "save";

      let control = combinator;

      $.ajax({
        method: control.recordForm.getAttribute("method"),
        url: control.recordForm.getAttribute("action"),
        dataType: "json",
        data: {
          rule: JSON.stringify(control.jsonifyTentative()),
          op: op,
          csrfmiddlewaretoken: control.recordForm.querySelector(
            'input[name="csrfmiddlewaretoken"]'
          ).value,
        },
        success: function (data) {
          if (utils.isDefined(data) && utils.isDefined(data.uuid)) {
            control.transformations[data.from].uuid = data.uuid;
          }
        },
        error: function () {
          console.log("ERROR!");
        },
      });
    },
    saveTransformations: function () {
      let control = combinator;
      let form = control.generationForm;

      if (control.editor instanceof JSONEditor) {
        let removedSentences = [];
        let history = control.editor.history;

        for (let i = 0; i <= history.index; i++) {
          let hEvent = history.history[i];
          if (hEvent.action != "removeNodes") continue;

          let parentNode = control.editor.node.findNodeByInternalPath(
            hEvent.params.parentPath
          );

          if (
            parentNode.field != "transformations" ||
            parentNode.type != "array"
          )
            continue;

          let affectedNodes = hEvent.params.nodes;
          for (
            let nodeId = 0, nodeLen = affectedNodes.length;
            nodeId < nodeLen;
            nodeId++
          ) {
            removedSentences.push(affectedNodes[nodeId].value);
            control.banned.add(affectedNodes[nodeId].value);
          }
        }

        $.ajax({
          method: form.getAttribute("method"),
          url: form.getAttribute("action"),
          dataType: "json",
          data: {
            batch: control.loaded,
            removed: JSON.stringify(removedSentences),
            data: JSON.stringify(control.editor.get()),
            csrfmiddlewaretoken: form.querySelector(
              'input[name="csrfmiddlewaretoken"]'
            ).value,
          },
          success: function (data) {
            if (data.action) {
              control.loaded = data.batch;
              alert(utils.title(data.action) + " successfully!");
            }
          },
          error: function () {
            console.log("ERROR!");
          },
        });
      }
    },
    search: function () {
      let control = combinator;
      let form = control.editingSearchForm;

      let formData = new FormData(form);

      $.ajax({
        method: form.getAttribute("method"),
        url: form.getAttribute("action"),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: Object.fromEntries(formData.entries()),
        success: function (data) {
          control.searchResultsArea.innerHTML = data.template;
          let searchResultItems = document.querySelectorAll("li[data-id]");
          searchResultItems.forEach(function (x) {
            x.addEventListener("click", function (e) {
              let target = e.target;
              let uuid = target.parentNode.getAttribute("data-id");
              searchResultItems.forEach(function (item) {
                item.querySelector(".button").classList.remove("is-hovered");
              });
              if (control.loaded == uuid) {
                target.classList.remove("is-hovered");
                control.loaded = null;
                control.restore();
              } else {
                db.load(uuid);
                control.loaded = uuid;
                target.classList.add("is-hovered");
              }
            });
          });
        },
      });
    },
    load: function (uuid) {
      let control = combinator;
      $.ajax({
        method: "GET",
        url: combinator.searchResultsArea.getAttribute("data-url"),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: {
          uuid: uuid,
        },
        success: function (res) {
          control.restore(res.data);
        },
      });
    },
  };

  const combinator = {
    transformations: {},
    tentative: null,
    editor: null,
    loaded: null,
    banned: new Set(),
    commentSymbol: "//",
    maxTransformationDepth: 100,
    placeholders: {
      remove: "[[empty]]",
      space: "*",
    },
    init: function () {
      this.generationForm = document.querySelector("#generationArea");
      this.recordForm = document.querySelector("#recordForm");
      this.editingSearchForm = document.querySelector("#editingSearchForm");

      this.sourceArea = document.querySelector("textarea#source");
      this.targetArea = document.querySelector("textarea#target");
      this.generationArea = this.generationForm.querySelector("fieldset");
      this.transformationMemoryArea = document.querySelector(
        "div#transformationMemoryArea"
      );
      this.searchResultsArea = document.querySelector("ul#searchResults");

      this.generateButton = document.querySelector("button#generate");

      this.tentative = this.initTransformation();

      this.initEvents();
      this.preloadRules();
    },
    preloadRules: function () {
      let loadedBanned = document.querySelector("script#banned");
      if (utils.isDefined(loadedBanned)) {
        let newArrivals = new Set(JSON.parse(loadedBanned.innerText));
        this.banned = utils.setUnion(this.banned, newArrivals);
        loadedBanned.parentNode.removeChild(loadedBanned);
      }

      let loadedBank = document.querySelector("script#loadedBank");
      if (utils.isDefined(loadedBank)) {
        let bank = JSON.parse(loadedBank.innerText);
        for (let i = 0, len = bank.length; i < len; i++) {
          bank[i].to = new Set(bank[i].to);
          this.transformations[bank[i].from] = bank[i];
        }
        loadedBank.parentNode.removeChild(loadedBank);
        this.visualize(false);
      }
    },
    initTransformation: function () {
      return {
        action: "",
        from: "",
        to: new Set(),
        uuid: "",
      };
    },
    checkUpdate: function (key) {
      return this.transformations.hasOwnProperty(key);
    },
    initEvents: function () {
      let control = this;
      this.sourceArea.addEventListener(
        "mouseup",
        function (e) {
          let target = e.target,
            text = target.value,
            selStart = target.selectionStart,
            selEnd = target.selectionEnd;

          if (selEnd - selStart > 0) {
            let toAdd = Array.from(control.tentative.to);
            control.tentative["from"] = text.substring(selStart, selEnd).trim();
            control.tentative["action"] =
              toAdd.length > 0 ? "replace" : "remove";
            control.visualize();
          }
        },
        false
      );

      this.targetArea.addEventListener(
        "input",
        function () {
          let replacement = control.targetArea.value.trim(),
            toRemove = control.tentative["from"];

          control.tentative["to"].clear();
          if (replacement.includes("->")) {
            let parts = replacement.split("->");
            if (parts.length > 1) {
              control.tentative["action"] = "replace";
              control.tentative["from"] = parts[0].trim();
              let clauses = parts[1].split("|");
              for (let i = 0, len = clauses.length; i < len; i++) {
                control.tentative.to.add(clauses[i].trim());
              }
            } else {
              control.tentative["action"] = "remove";
            }
          } else {
            if (replacement.length > 0) {
              control.tentative["action"] =
                toRemove.length > 0 ? "replace" : "add";
              let options = replacement.split("\n");
              for (let i = 0, len = options.length; i < len; i++) {
                control.tentative["to"].add(options[i].trim());
              }
            } else {
              control.tentative["action"] = "remove";
            }
          }

          control.visualize();
        },
        false
      );

      this.recordForm.addEventListener("submit", function (e) {
        e.preventDefault();
        e.stopPropagation();
        let ct = control.tentative;
        if (control.checkUpdate(ct.from)) {
          if (ct.action == "remove") {
            control.transformations[ct.from].to.add("");
          } else {
            let to = Array.from(ct.to);
            for (let i = 0, len = to.length; i < len; i++) {
              control.transformations[ct.from].to.add(to[i]);
            }
          }
          control.tentative = control.transformations[ct.from];
          db.saveRule("update");
        } else {
          control.transformations[ct.from] = ct;
          db.saveRule();
        }
        control.tentative = control.initTransformation();
        control.targetArea.value = "";
        control.visualize(false);
      });

      this.generationForm.addEventListener("submit", function (e) {
        e.preventDefault();
        db.saveTransformations();
      });

      this.editingSearchForm.addEventListener("submit", function (e) {
        e.preventDefault();
        db.search();
      });

      this.generateButton.addEventListener("click", function () {
        let lines = control.sourceArea.value.split("\n");
        let previousComment = false;
        let sources = [];
        let extra = {};

        for (let i = 0, len = lines.length; i < len; i++) {
          let line = lines[i].trim();
          if (line.startsWith(control.commentSymbol)) {
            if (!previousComment) extra = {};
            extra = Object.assign(extra, utils.parseComments(line));
            previousComment = true;
          } else if (line.length > 0) {
            sources.push({
              text: line,
              extra: extra,
            });
            previousComment = false;
          }
        }

        control.history = {};
        let res = control.transform(sources, control.maxTransformationDepth);
        control.showHierarchical(res);
      });
    },
    jsonifyTentative: function () {
      let copy = Object.assign({}, this.tentative);
      copy.to = Array.from(copy.to);
      return copy;
    },
    initJsonEditor: function () {
      if (!utils.isDefined(this.editor)) {
        this.generationArea.innerHTML = "";
        let control = this;
        const options = {
          mode: "tree",
          onCreateMenu: function (items, nodeInfo) {
            let clickedNode = control.editor.node.findNodeByPath(nodeInfo.path);

            function convert(type) {
              return function () {
                let value = clickedNode.getValue();

                if (type == "object") {
                  clickedNode.update({
                    value: value,
                  });
                } else if (type == "array") {
                  clickedNode.update([value]);
                }
              };
            }

            if (nodeInfo.path) {
              let insertIndex = items.findIndex((x) => x.text == "Insert");

              let convertSubmenu = [
                {
                  text: "array",
                  title: "Array",
                  className: "jsoneditor-type-array",
                  click: convert("array"),
                },
                {
                  text: "object",
                  title: "Object",
                  className: "jsoneditor-type-object",
                  click: convert("object"),
                },
              ];

              convertSubmenu = convertSubmenu.filter(
                (x) => x.text != clickedNode.type
              );

              items.splice(insertIndex + 1, 0, {
                text: "Convert", // the text for the menu item
                title: "convert element to...", // the HTML title attribute
                submenu: convertSubmenu,
              });
            }

            return items;
          },
        };
        this.editor = new JSONEditor(this.generationArea, options);

        let saveButton = document.createElement("button");
        saveButton.setAttribute("type", "button");
        saveButton.className = "scombinator-save";
        let saveIcon = document.createElement("i");
        saveIcon.className = "fas fa-save";
        saveButton.appendChild(saveIcon);
        saveButton.addEventListener(
          "click",
          function () {
            db.saveTransformations();
          },
          false
        );
        this.editor.menu.appendChild(saveButton);
      }
    },
    showHierarchical: function (data) {
      this.initJsonEditor();
      this.editor.set(data);
    },
    transform: function (sources, maxDepth, history) {
      if (!utils.isDefined(sources) || sources.length === 0 || maxDepth < 0) {
        return new Set();
      }

      if (!utils.isDefined(history)) history = {};

      let res = maxDepth == this.maxTransformationDepth ? {} : new Set();
      for (let i = 0, len = sources.length; i < len; i++) {
        let source;

        if (maxDepth == this.maxTransformationDepth) {
          let parts = sources[i].text.trim().split(this.commentSymbol);
          source = parts[0].trim();
          delete sources[i].text;
          res[source] = sources[i];
          if (parts.length > 1) {
            res[source].extra = Object.assign(
              {},
              res[source].extra,
              utils.parseComments(parts[1])
            );
          }
          res[source].transformations = new Set();
        } else {
          source = sources[i].trim();
        }

        for (let key in this.transformations) {
          let t = this.transformations[key];

          if (source.includes(t.from)) {
            let to = Array.from(t.to);
            let toIncludesSource = to.some((x) => source.includes(x));
            for (let toId = 0, toLen = to.length; toId < toLen; toId++) {
              if (to[toId].length === 0 || !toIncludesSource) {
                let target = source.slice();
                let toRep = to[toId];

                if (!history.hasOwnProperty(t.from))
                  history[t.from] = new Set();

                if (history[t.from].has(toRep)) {
                  // we have already applied this rule once,
                  // so it's potentially an infinite recursion!
                  continue;
                }

                history[t.from].add(toRep);

                if (toRep.startsWith(this.placeholders.space)) {
                  toRep = toRep.replace(this.placeholders.space, " ");
                }

                target = target.replaceAll(t.from, toRep);
                target = target.replaceAll(/ {2,}/gi, " ").trim();

                if (maxDepth == this.maxTransformationDepth) {
                  if (!this.banned.has(target))
                    res[source].transformations.add(target);
                  if (!toRep.includes(" ")) {
                    res[source].transformations = utils.setUnion(
                      res[source].transformations,
                      this.transform([target], maxDepth - 1, history)
                    );

                    if (res[source].transformations.has(source)) {
                      res[source].transformations.delete(source);
                    }
                  }
                } else {
                  if (!this.banned.has(target)) res.add(target);
                  if (!toRep.includes(" "))
                    res = utils.setUnion(
                      res,
                      this.transform([target], maxDepth - 1, history)
                    );
                }
              }
            }
          }
        }
      }

      if (maxDepth == this.maxTransformationDepth) {
        for (var key in res) {
          res[key].transformations = Array.from(res[key].transformations);
        }
      }

      return res;
    },
    deleteTransformation: function (i) {
      let oldTentative = Object.assign({}, this.tentative);
      this.tentative = this.transformations[i];
      db.saveRule("delete");
      this.tentative = oldTentative;
      return delete this.transformations[i];
    },
    isEmptyTransformation: function (i) {
      return this.transformations[i].to.size === 0;
    },
    deleteTransformationClause: function (i, j) {
      this.transformations[i].to.delete(j);
      let oldTentative = Object.assign({}, this.tentative);
      if (this.isEmptyTransformation(i)) {
        this.transformations[i].action = "remove";
      }
      this.tentative = this.transformations[i];
      db.saveRule("update");
      this.tentative = oldTentative;
    },
    createOpNode: function (op) {
      let opNode = document.createElement("span");
      opNode.setAttribute("data-rel", "op");
      opNode.innerText = " " + op + " ";
      return opNode;
    },
    isOpNode: function (n) {
      return (
        utils.isDefined(n) &&
        n.hasAttribute("data-rel") &&
        n.getAttribute("data-rel") == "op"
      );
    },
    visualizeTransformation: function (t, i, isTentative) {
      if (!utils.isDefined(isTentative)) isTentative = false;

      let p = document.createElement("div");
      let control = this;
      p.setAttribute("data-i", i);
      if (isTentative) {
        p.style.color = "grey";
      }

      if (t.action.length > 0) {
        let actionSpan = document.createElement("span");
        actionSpan.setAttribute("data-rel", "action");
        actionSpan.innerHTML = t.action + ": ";
        p.appendChild(actionSpan);
      }
      let fromSpan;
      if (t.from.length > 0) {
        fromSpan = document.createElement("span");
        fromSpan.setAttribute("data-rel", "from");
        fromSpan.innerHTML = t.from + " ";
        p.appendChild(fromSpan);
      }

      let to = Array.from(t.to);

      if (to.length > 0) {
        if (t.from.length > 0) fromSpan.innerHTML += " -> ";
        let span = null;
        for (let toId = 0, len = to.length; toId < len; toId++) {
          span = document.createElement("span");
          span.setAttribute("data-rel", "clause");
          if (span != null && toId > 0) {
            p.appendChild(control.createOpNode("OR"));
          }
          if (to[toId].length === 0) {
            span.innerHTML = "<i>" + control.placeholders.remove + "</i>";
          } else {
            span.innerText = to[toId];
          }

          let delBtn = document.createElement("button");
          delBtn.className = "delete is-small";

          delBtn.addEventListener("click", function (e) {
            let target = e.target;
            let clause = target.parentNode;
            let rule = clause.parentNode;
            let ruleId = rule.getAttribute("data-i");

            if (control.isOpNode(clause.nextSibling))
              rule.removeChild(clause.nextSibling);
            let clauseRule = clause.innerText.trim();
            control.deleteTransformationClause(
              ruleId,
              clauseRule == control.placeholders.remove ? "" : clauseRule
            );

            if (control.isEmptyTransformation(ruleId)) {
              control.transformations[ruleId].action = "remove";
              let fromSpan = rule.querySelector('[data-rel="from"]');
              fromSpan.innerText = fromSpan.innerText.replace("->", "").trim();
              let actionSpan = rule.querySelector('[data-rel="action"]');
              actionSpan.innerText = "remove: ";
            }

            rule.removeChild(clause);
            let lastClause = rule.lastChild;
            if (utils.isDefined(lastClause) && control.isOpNode(lastClause))
              rule.removeChild(lastClause);
          });

          span.appendChild(delBtn);
          p.appendChild(span);
        }
      }

      if (p.innerText.length > 0) {
        if (!isTentative) {
          let deleteButton = document.createElement("button");
          deleteButton.className = "button is-small mr-2";
          deleteButton.innerText = "Delete";

          deleteButton.addEventListener(
            "click",
            function (e) {
              let target = e.target,
                ruleDiv = target.parentNode,
                idx = ruleDiv.getAttribute("data-i");

              let res = control.deleteTransformation(idx);
              if (!res) control.tentative = control.initTransformation();
              ruleDiv.parentNode.removeChild(ruleDiv);
            },
            false
          );

          p.prepend(deleteButton);
        }

        return p;
      } else {
        return null;
      }
    },
    visualize: function (withTentative) {
      if (withTentative === undefined) withTentative = true;

      this.transformationMemoryArea.innerHTML = "";
      let transformations = this.transformations;
      let control = this;
      for (let key in transformations) {
        let rule = control.visualizeTransformation(transformations[key], key);
        if (rule !== null) this.transformationMemoryArea.appendChild(rule);
      }

      if (withTentative) {
        let ct = control.tentative;
        if (ct.action) {
          this.transformationMemoryArea.appendChild(
            control.visualizeTransformation(ct, ct.from, true)
          );
        }
      }
    },
    restore: function (data) {
      if (utils.isDefined(data)) {
        let sources = Object.keys(data);

        for (let i = 0, len = sources.length; i < len; i++) {
          if (Object.keys(data[sources[i]].extra).length !== 0) {
            sources[i] =
              sources[i] +
              " " +
              this.commentSymbol +
              " " +
              utils.stringifyComments(data[sources[i]].extra);
          }
        }

        this.sourceArea.value = sources.join("\n");
        this.showHierarchical(data);
      } else {
        this.sourceArea.value = "";
        this.showHierarchical();
      }
      this.targetArea.value = "";
    },
  };

  $(document).ready(function () {
    combinator.init();
    window.c = combinator;
  });
})(window.jQuery, window.JSONEditor);
