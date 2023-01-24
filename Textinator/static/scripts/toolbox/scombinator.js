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
      let l = line.replace(combinator.symbols.comment, "").trim();
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

  const grammar = {
    words: {
      en: null,
    },
    init: function () {
      let dict = JSON.parse(
        document.querySelector("#dictionaryData").textContent.trim()
      );
      this.words.en = new Set(dict.words);
    },
    check: function (word) {
      return this.words.en.has(word);
    },
  };

  const db = {
    saveRule: function (op) {
      // saves a tentative rule to DB, so that it becomes permanent
      if (!utils.isDefined(op)) op = "save";

      $.ajax({
        method: ui.recordForm.getAttribute("method"),
        url: ui.recordForm.getAttribute("action"),
        dataType: "json",
        data: {
          rule: JSON.stringify(combinator.jsonifyTentative()),
          op: op,
          csrfmiddlewaretoken: ui.recordForm.querySelector(
            'input[name="csrfmiddlewaretoken"]'
          ).value,
        },
        success: function (data) {
          if (utils.isDefined(data) && utils.isDefined(data.uuid)) {
            combinator.transformations.active[data.from].uuid = data.uuid;
          }
        },
        error: function () {
          console.log("ERROR!");
        },
      });
    },
    saveTransformations: function () {
      let form = ui.generationForm;

      if (ui.editor instanceof JSONEditor) {
        let removedSentences = [];
        let history = ui.editor.history;

        for (let i = 0; i <= history.index; i++) {
          let hEvent = history.history[i];
          if (hEvent.action != "removeNodes") continue;

          let parentNode = ui.editor.node.findNodeByInternalPath(
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
            combinator.banned.add(affectedNodes[nodeId].value);
          }
        }

        // it's not necessary to transform `to` field in active,
        // since uuid are the only thing we need
        // but for the disabled `to` fields are essential,
        // so we have to transform them
        let transformations = Object.assign({}, combinator.transformations);
        for (let key in transformations.disabled) {
          transformations.disabled[key].to = Array.from(
            transformations.disabled[key].to
          );
        }

        $.ajax({
          method: form.getAttribute("method"),
          url: form.getAttribute("action"),
          dataType: "json",
          data: {
            batch: combinator.loaded,
            transformations: JSON.stringify(transformations),
            removed: JSON.stringify(removedSentences),
            data: JSON.stringify(ui.editor.get()),
            csrfmiddlewaretoken: form.querySelector(
              'input[name="csrfmiddlewaretoken"]'
            ).value,
          },
          success: function (data) {
            if (data.action) {
              combinator.loaded = data.batch;
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
      let form = ui.editingSearchForm;

      let formData = new FormData(form);

      $.ajax({
        method: form.getAttribute("method"),
        url: form.getAttribute("action"),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: Object.fromEntries(formData.entries()),
        success: function (data) {
          ui.searchResultsArea.innerHTML = data.template;
          let searchResultItems = document.querySelectorAll("li[data-id]");
          searchResultItems.forEach(function (x) {
            x.addEventListener("click", function (e) {
              let target = e.target;
              let uuid = target.parentNode.getAttribute("data-id");
              searchResultItems.forEach(function (item) {
                item.querySelector(".button").classList.remove("is-hovered");
              });
              if (combinator.loaded == uuid) {
                target.classList.remove("is-hovered");
                combinator.loaded = null;
                ui.restore();
                combinator.unstash();
              } else {
                db.load(uuid);
                combinator.loaded = uuid;
                target.classList.add("is-hovered");
              }
            });
          });
        },
      });
    },
    load: function (uuid) {
      $.ajax({
        method: "GET",
        url: ui.searchResultsArea.getAttribute("data-url"),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: {
          uuid: uuid,
        },
        success: function (res) {
          combinator.stash();
          ui.restore(res.data);
          for (let from in res.disabled) {
            let to = res.disabled[from].to;
            let fromNode = ui.getFromNode(from);
            if (res.disabled[from].whole) {
              ui._disable(fromNode.parentNode);
              combinator.disableTransformation(from);
            } else if (to.length > 0) {
              for (let i = 0, len = to.length; i < len; i++) {
                let toNode = ui.getToNode(from, to[i]);
                ui._disable(toNode);
                combinator.disableTransformation(from, to[i]);
              }
            }
          }
        },
      });
    },
  };

  const ui = {
    tabNames: {
      rules: "rule-builder",
      generations: "generation-area",
    },
    attr: {
      disabled: "data-disabled",
      disabledClass: "stroken-red",
      localStorage: {
        text: "scombinator_text",
        exclude: "scombinator_ignore",
      },
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
      this.renewButton = document.querySelector("button#renew");

      this.tabsArea = document.querySelector(".tabs");
      this.tabs = this.tabsArea.querySelectorAll("li[data-tab]");
      this.tabContentsArea = document.querySelector("#tabContent");
      this.tabContents = document.querySelectorAll("#tabContent > div");

      this.exclusionArea = document.querySelector("textarea#exclusion");

      let preloadExclude = localStorage.getItem(this.attr.localStorage.exclude);
      if (utils.isDefined(this.attr.localStorage.exclude)) {
        this.exclusionArea.value = preloadExclude;
      }

      let preloadText = localStorage.getItem(this.attr.localStorage.text);
      if (utils.isDefined(this.attr.localStorage.text)) {
        this.sourceArea.value = preloadText;
      }

      this.initTabs();
      this.initEvents();
    },
    initPersistenceEvents: function () {
      let control = this;
      this.sourceArea.addEventListener("keyup", function (e) {
        let target = e.target;
        let text = target.value;
        localStorage.setItem(control.attr.localStorage.text, text);
      });

      this.exclusionArea.addEventListener("keyup", function (e) {
        let target = e.target;
        let text = target.value;
        localStorage.setItem(control.attr.localStorage.exclude, text);
      });
    },
    initSourceAreaEvents: function () {
      let control = this;
      this.sourceArea.addEventListener(
        "mouseup",
        function (e) {
          let target = e.target,
            text = target.value,
            selStart = target.selectionStart,
            selEnd = target.selectionEnd;

          if (selEnd - selStart > 0) {
            let toAdd = Array.from(combinator.tentative.to);
            combinator.tentative["from"] = text
              .substring(selStart, selEnd)
              .trim();
            combinator.tentative["action"] =
              toAdd.length > 0 ? "replace" : "remove";
            control.visualize(combinator.getState());
          }
        },
        false
      );
    },
    initTargetAreaEvents: function () {
      let control = this;
      this.targetArea.addEventListener(
        "input",
        function () {
          combinator.changeTentative(control.targetArea.value.trim());
          ui.visualize(combinator.getState());
        },
        false
      );
    },
    initTransfomrationEvents: function () {
      let control = this;
      this.recordForm.addEventListener("submit", function (e) {
        e.preventDefault();
        e.stopPropagation();
        combinator.recordRule();
        control.targetArea.value = "";
        ui.visualize(combinator.getState(false));
      });

      this.generationForm.addEventListener("submit", function (e) {
        e.preventDefault();
        db.saveTransformations();
      });

      this.editingSearchForm.addEventListener("submit", function (e) {
        e.preventDefault();
        db.search();
      });

      this.renewButton.addEventListener("click", function () {
        combinator.loaded = null;
        ui.restore();
        ui.searchResultsArea.innerHTML = "";
      });

      this.generateButton.addEventListener("click", function () {
        let lines = control.sourceArea.value.split("\n");
        let previousComment = false;
        let sources = [];
        let extra = {};

        for (let i = 0, len = lines.length; i < len; i++) {
          let line = lines[i].trim();
          if (line.startsWith(combinator.symbols.comment)) {
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

        combinator.history = {};
        let res = combinator.transform(sources, control.maxTransformationDepth);
        control.showHierarchical(res);
        control.switchTab(control.tabNames.generations);
      });
    },
    initEvents: function () {
      this.initPersistenceEvents();
      this.initSourceAreaEvents();
      this.initTargetAreaEvents();
      this.initTransfomrationEvents();

      let control = this;

      document.addEventListener("click", function (e) {
        let target = e.target;
        if (target.hasAttribute("data-rel")) {
          let rel = target.getAttribute("data-rel");
          let ruleDiv = target.parentNode;
          let from = ruleDiv
            .querySelector('[data-rel="from"]')
            .getAttribute("data-val");

          if (rel == "action") {
            let wasDisabled = control.toggleState(ruleDiv);
            combinator.toggleTransformation(wasDisabled, from);
          } else if (rel == "clause") {
            let to = target.innerText.trim();
            let wasDisabled = control.toggleState(target);
            combinator.toggleTransformation(wasDisabled, from, to);
          }
        }
      });
    },
    initTabs: function () {
      let control = this;
      this.tabs.forEach(function (x) {
        x.addEventListener("click", function (e) {
          let target = e.target;
          if (target.tagName != "LI") target = target.parentNode;
          let tab = target.getAttribute("data-tab");
          control.switchTab(tab);
        });
      });
      this.switchTab(this.tabNames.rules);
    },
    switchTab: function (tab) {
      this.tabs.forEach((t) => t.classList.remove("is-active"));
      this.tabsArea
        .querySelector('[data-tab="' + tab + '"]')
        .classList.add("is-active");
      this.tabContents.forEach((t) => t.classList.remove("is-active"));
      this.tabContentsArea
        .querySelector('div[data-content="' + tab + '"]')
        .classList.add("is-active");
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
        actionSpan.setAttribute(
          "data-rel",
          isTentative ? "action/t" : "action"
        );
        actionSpan.innerHTML = t.action + ": ";
        p.appendChild(actionSpan);
      }
      let fromSpan;
      if (t.from.length > 0) {
        fromSpan = document.createElement("span");
        fromSpan.setAttribute("data-rel", isTentative ? "from/t" : "from");
        fromSpan.setAttribute("data-val", t.from);
        fromSpan.innerHTML = t.from + " ";
        p.appendChild(fromSpan);
      }

      let to = Array.from(t.to);

      if (to.length > 0) {
        if (t.from.length > 0)
          fromSpan.innerHTML += " " + combinator.symbols.ruleSep + " ";
        let span = null;
        for (let toId = 0, len = to.length; toId < len; toId++) {
          span = document.createElement("span");
          span.setAttribute("data-rel", isTentative ? "clause/t" : "clause");
          span.setAttribute("data-val", to[toId]);
          if (span != null && toId > 0) {
            p.appendChild(control.createOpNode("OR"));
          }
          if (to[toId].length === 0) {
            span.innerHTML = "<i>" + combinator.placeholders.remove + "</i>";
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

            let replace2remove = combinator.deleteCallback(ruleId, clauseRule);

            if (replace2remove) {
              let fromSpan = rule.querySelector('[data-rel="from"]');
              fromSpan.innerText = fromSpan.innerText
                .replace(combinator.symbols.ruleSep, "")
                .trim();
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
          let copyButton = document.createElement("button");
          copyButton.className = "button is-small mr-2";
          copyButton.innerText = "Copy";

          copyButton.addEventListener("click", function (e) {
            let target = e.target,
              ruleDiv = target.parentNode;

            let reg = new RegExp("DeleteCopy.*:");

            // Copy the text inside the text field
            navigator.clipboard.writeText(
              ruleDiv.innerText.replace(reg, "").replace("OR", "|").trim()
            );
          });

          let deleteButton = document.createElement("button");
          deleteButton.className = "button is-small mr-2";
          deleteButton.innerText = "Delete";

          deleteButton.addEventListener(
            "click",
            function (e) {
              let target = e.target,
                ruleDiv = target.parentNode,
                idx = ruleDiv.getAttribute("data-i");

              let confirmation = confirm(
                "Are you sure to accept this reply as your favor?"
              );

              if (confirmation) {
                combinator.deleteCallback(idx);
                ruleDiv.parentNode.removeChild(ruleDiv);
              }
            },
            false
          );

          p.prepend(copyButton);
          p.prepend(deleteButton);
        }
        return p;
      } else {
        return null;
      }
    },
    visualize: function (state) {
      this.transformationMemoryArea.innerHTML = "";

      for (let i in state.keys.sorted) {
        let key = state.keys.sorted[i];
        if (key.length === 0) continue;
        if (state.keys.disabled.has(key)) {
          if (state.keys.active.has(key)) {
            let t = Object.assign({}, state.t.active[key]);
            t.to = utils.setUnion(t.to, state.t.disabled[key].to);
            let rule = ui.visualizeTransformation(t, key);
            if (rule !== null) {
              ui.transformationMemoryArea.appendChild(rule);
              let toDisable = Array.from(state.t.disabled[key].to);
              for (let dId = 0, dLen = toDisable.length; dId < dLen; dId++) {
                this.disable(key, toDisable[dId]);
              }
            }
          } else {
            let rule = ui.visualizeTransformation(state.t.disabled[key], key);
            if (rule !== null) {
              this.transformationMemoryArea.appendChild(rule);
              this.disable(key);
            }
          }
        } else if (state.keys.active.has(key)) {
          let rule = ui.visualizeTransformation(state.t.active[key], key);
          if (rule !== null) ui.transformationMemoryArea.appendChild(rule);
        }
      }

      if (utils.isDefined(state.tentative)) {
        if (state.tentative.action) {
          ui.transformationMemoryArea.prepend(
            ui.visualizeTransformation(
              state.tentative,
              state.tentative.from,
              true
            )
          );
        }
      }
    },
    _enable: function (node) {
      // callback, which is why we say ui.attr and not this
      if (utils.isDefined(node)) {
        node.removeAttribute(ui.attr.disabled);
        node.classList.remove(ui.attr.disabledClass);
      }
    },
    _disable: function (node) {
      if (utils.isDefined(node)) {
        node.setAttribute(ui.attr.disabled, true);
        node.classList.add(ui.attr.disabledClass);
      }
    },
    getFromNode: function (from) {
      return document.querySelector(
        '[data-rel="from"][data-val="' + from + '"]'
      );
    },
    getToNode: function (fromNode, to) {
      let ruleDiv = fromNode.parentNode;
      return ruleDiv.querySelector(
        '[data-rel="clause"][data-val="' + to + '"]'
      );
    },
    _changeState: function (from, to, callback) {
      // changes state only for the first occurrence
      // this is because normally the rules are not allowed to duplicate
      let fromNode = this.getFromNode(from);

      if (utils.isDefined(to)) {
        let toNode = this.getToNode(fromNode, to);
        callback(toNode);
      } else {
        callback(fromNode.parentNode);
      }
    },
    enable: function (from, to) {
      this._changeState(from, to, this._enable);
    },
    disable: function (from, to) {
      this._changeState(from, to, this._disable);
    },
    toggleState: function (node) {
      let wasDisabled = node.hasAttribute(this.attr.disabled);
      if (wasDisabled) {
        this._enable(node);
      } else {
        this._disable(node);
      }
      return wasDisabled;
    },
    clearDisabled: function () {
      let control = this;
      document
        .querySelectorAll("." + this.attr.disabledClass)
        .forEach(function (x) {
          x.classList.remove(control.attr.disabledClass);
        });
    },
    restore: function (data) {
      this.clearDisabled();
      if (utils.isDefined(data)) {
        let sources = Object.keys(data);

        for (let i = 0, len = sources.length; i < len; i++) {
          if (Object.keys(data[sources[i]].extra).length !== 0) {
            sources[i] =
              sources[i] +
              " " +
              combinator.symbols.comment +
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
  window.ui = ui;

  const combinator = {
    transformations: {
      active: {},
      disabled: {},
    },
    memory: {},
    tentative: null,
    editor: null,
    loaded: null,
    banned: new Set(),
    symbols: {
      comment: "//",
      phrase: "_",
      ruleSep: "->",
    },
    maxTransformationDepth: 100,
    placeholders: {
      remove: "[[empty]]",
      space: "*",
    },
    init: function () {
      this.tentative = this.initTransformation();

      ui.init();

      this.preloadRules();
      grammar.init();
    },
    stash: function () {
      this.memory.active = Object.assign({}, this.transformations.active);
      this.memory.disabled = Object.assign({}, this.transformations.disabled);
      this.memory.sourceText = ui.sourceArea.value;
      this.memory.excluded = ui.exclusionArea.value;
      this.transformations.disabled = {};
    },
    unstash: function () {
      if (utils.isDefined(this.memory.active)) {
        this.transformations.active = this.memory.active;
        delete this.memory.active;
      }

      if (utils.isDefined(this.memory.disabled)) {
        this.transformations.disabled = this.memory.disabled;
        delete this.memory.disabled;
      }
      if (utils.isDefined(this.memory.sourceText)) {
        ui.sourceArea.value = this.memory.sourceText;
        delete this.memory.sourceText;
      }
      if (utils.isDefined(this.memory.excluded)) {
        ui.exclusionArea.value = this.memory.excluded;
        delete this.memory.excluded;
      }
      ui.visualize(this.getState(false));
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
          if (bank[i].from.trim().length === 0) continue;
          bank[i].to = new Set(bank[i].to);
          this.transformations.active[bank[i].from] = bank[i];
        }
        loadedBank.parentNode.removeChild(loadedBank);
        ui.visualize(this.getState(false));
      }
    },
    changeTentative: function (replacement) {
      let toRemove = this.tentative["from"];

      this.tentative["to"].clear();
      if (replacement.includes(this.symbols.ruleSep)) {
        let parts = replacement.split(this.symbols.ruleSep);
        if (parts.length > 1) {
          this.tentative["action"] = "replace";
          this.tentative["from"] = parts[0].trim();
          let clauses = parts[1].split("|");
          for (let i = 0, len = clauses.length; i < len; i++) {
            this.tentative.to.add(clauses[i].trim());
          }
        } else {
          this.tentative["action"] = "remove";
        }
      } else {
        if (replacement.length > 0) {
          this.tentative["action"] = toRemove.length > 0 ? "replace" : "add";
          let options = replacement.split("\n");
          for (let i = 0, len = options.length; i < len; i++) {
            this.tentative["to"].add(options[i].trim());
          }
        } else {
          this.tentative["action"] = "remove";
        }
      }
    },
    recordRule: function () {
      let ct = this.tentative;
      if (this.checkUpdate(ct.from)) {
        if (ct.action == "remove") {
          this.transformations.active[ct.from].to.add("");
        } else {
          let to = Array.from(ct.to);
          for (let i = 0, len = to.length; i < len; i++) {
            this.transformations.active[ct.from].to.add(to[i]);
          }
          this.transformations.active[ct.from].action = ct.action;
        }
        this.tentative = this.transformations.active[ct.from];
        db.saveRule("update");
      } else {
        this.transformations.active[ct.from] = ct;
        db.saveRule();
      }
      this.tentative = this.initTransformation();
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
      return this.transformations.active.hasOwnProperty(key);
    },
    jsonifyTentative: function () {
      let copy = Object.assign({}, this.tentative);
      copy.to = Array.from(copy.to);
      return copy;
    },
    isSentenceGrammatical: function (sent) {
      let punctuationRegex = new RegExp("[.,/?!$%^&;:{}=`~]", "g");
      let s = sent.slice().replaceAll(punctuationRegex, "");
      s = s.replaceAll(this.symbols.phrase, " ");
      s = s.charAt(0).toLowerCase() + s.slice(1);

      for (let j = 0, len = this.grammarCheckIgnore.length; j < len; j++) {
        s = s.replaceAll(this.grammarCheckIgnore[j], "");
      }

      let words = s.split(" ");

      for (let i = 0, len = words.length; i < len; i++) {
        let word = words[i].trim();

        if (word.length === 0) continue;

        if (utils.isDefined(words[i - 1]) && word == words[i - 1].trim())
          return false;

        if (!grammar.check(word)) {
          return false;
        }
      }
      return true;
    },
    _mainTransformationLoop: function (source, history, callback) {
      for (let key in this.transformations.active) {
        let t = this.transformations.active[key];
        let replaceRegex = new RegExp(
          "(?<!" +
            this.symbols.phrase +
            ")" +
            t.from.replaceAll(" ", "( |_)") +
            "(?!" +
            this.symbols.phrase +
            ")",
          "gi"
        );

        if (t.action == "remove") {
          let target = source.slice();
          target = target.replaceAll(replaceRegex, "");
          target = target.replaceAll(/ {2,}/gi, " ").trim();
          target = utils.title(target);

          if (this.isSentenceGrammatical(target)) {
            callback(source, target);
          }
          continue;
        }

        if (source.search(replaceRegex) !== -1) {
          let to = Array.from(t.to);

          for (let toId = 0, toLen = to.length; toId < toLen; toId++) {
            let target = source.slice();
            let toRep = to[toId];

            if (utils.isDefined(history)) {
              if (!history.hasOwnProperty(t.from))
                history[t.from] = {
                  rules: new Set(),
                  generated: new Set(),
                };

              if (history[t.from].rules.has(toRep)) {
                // we have already applied this rule once,
                // so it's potentially an infinite recursion!
                continue;
              }

              history[t.from].rules.add(toRep);
            }

            if (toRep.startsWith(this.placeholders.space)) {
              toRep = toRep.replace(this.placeholders.space, " ");
            }

            target = target.replaceAll(replaceRegex, toRep);
            target = target.replaceAll(/ {2,}/gi, " ").trim();
            target = utils.title(target);

            if (this.isSentenceGrammatical(target)) {
              callback(source, target);
            }
          }
        }
      }
    },
    _recursiveTransform: function (sources, maxDepth, history, taboo) {
      function remember(src, trg) {
        if (!control.banned.has(trg)) res.add(trg);

        if (!taboo.has(trg)) {
          taboo.add(trg);
          res = utils.setUnion(
            res,
            control._recursiveTransform(
              [trg],
              maxDepth - 1,
              Object.assign({}, history),
              taboo
            )
          );
        }
      }

      if (!utils.isDefined(sources) || sources.length === 0 || maxDepth < 0) {
        return new Set();
      }

      let control = this;
      let res = new Set();
      for (let i = 0, len = sources.length; i < len; i++) {
        let source = sources[i].trim();
        this._mainTransformationLoop(source, history, function (x, y) {
          remember(x, y);
        });
      }
      return res;
    },
    transform: function (sources, maxDepth, history) {
      this.grammarCheckIgnore = ui.exclusionArea.value
        .split("\n")
        .map((x) => x.trim());

      function remember(src, trg) {
        if (!control.banned.has(trg)) res[src].transformations.add(trg);
        res[src].transformations = utils.setUnion(
          res[src].transformations,
          control._recursiveTransform([trg], maxDepth - 1, {}, new Set())
        );

        if (res[src].transformations.has(src)) {
          res[src].transformations.delete(src);
        }
      }

      let control = this;
      let res = {};
      for (let i = 0, len = sources.length; i < len; i++) {
        let parts = sources[i].text.trim().split(this.symbols.comment);
        let source = parts[0].trim();
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

        this._mainTransformationLoop(source, history, function (x, y) {
          remember(x, y);
        });
      }

      let res2 = {};
      for (var key in res) {
        res[key].transformations = Array.from(res[key].transformations).map(
          function (x) {
            return x.replaceAll(control.symbols.phrase, " ");
          }
        );
        if (key.includes(control.symbols.phrase)) {
          let keyReg = new RegExp(control.symbols.phrase, "gi");
          let newKey = utils.title(key.replaceAll(keyReg, " "));
          res2[newKey] = Object.assign({}, res[key]);
        } else {
          res2[utils.title(key)] = Object.assign({}, res[key]);
        }
      }
      return res2;
    },
    enableTransformation: function (i, j) {
      if (utils.isDefined(j)) {
        this.transformations.disabled[i].to.delete(j);

        if (!this.transformations.disabled[i].whole) {
          if (!this.transformations.active.hasOwnProperty(i)) {
            this.transformations.active[i] = Object.assign(
              {},
              this.transformations.disabled[i]
            );
            this.transformations.active[i].to = new Set();
          }
          this.transformations.active[i].to.add(j);
          this.transformations.active[i].action = "replace";

          if (this.transformations.disabled[i].to.size == 0) {
            delete this.transformations.disabled[i];
          }
        }
      } else {
        if (this.transformations.disabled.hasOwnProperty(i)) {
          this.transformations.active[i] = Object.assign(
            {},
            this.transformations.disabled[i]
          );
          delete this.transformations.disabled[i];
        }
      }
    },
    disableTransformation: function (i, j) {
      if (utils.isDefined(j)) {
        if (!this.transformations.disabled.hasOwnProperty(i)) {
          this.transformations.disabled[i] = Object.assign(
            {},
            this.transformations.active[i]
          );
          this.transformations.disabled[i].to = new Set();
        }
        this.transformations.disabled[i].to.add(j);
        if (utils.isDefined(this.transformations.active[i].to))
          this.transformations.active[i].to.delete(j);
        if (this.transformations.active[i].to.size == 0) {
          this.transformations.active[i].action = "remove";
        }
      } else {
        if (this.transformations.active.hasOwnProperty(i)) {
          this.transformations.disabled[i] = Object.assign(
            {},
            this.transformations.active[i]
          );
          delete this.transformations.active[i];
        }
        this.transformations.disabled[i].whole = true;
      }
    },
    toggleTransformation: function (wasDisabled, i, j) {
      wasDisabled
        ? this.enableTransformation(i, j)
        : this.disableTransformation(i, j);
    },
    isEmptyTransformation: function (i) {
      return this.transformations.active[i].to.size === 0;
    },
    deleteTransformationClause: function (i, j) {
      this.transformations.active[i].to.delete(j);
      let oldTentative = Object.assign({}, this.tentative);
      if (this.isEmptyTransformation(i)) {
        this.transformations.active[i].action = "remove";
      }
      this.tentative = this.transformations.active[i];
      db.saveRule("update");
      this.tentative = oldTentative;
    },
    deleteTransformation: function (i) {
      let oldTentative = Object.assign({}, this.tentative);
      this.tentative = this.transformations.active[i];
      db.saveRule("delete");
      this.tentative = oldTentative;
      return delete this.transformations.active[i];
    },
    deleteCallback: function (ruleId, clauseRule) {
      if (utils.isDefined(clauseRule)) {
        this.deleteTransformationClause(
          ruleId,
          clauseRule == this.placeholders.remove ? "" : clauseRule
        );
      } else {
        let res = this.deleteTransformation(ruleId);
        if (!res) this.tentative = this.initTransformation();
      }

      let isEmpty = this.isEmptyTransformation(ruleId);
      if (isEmpty) {
        this.transformations.active[ruleId].action = "remove";
      }
      return isEmpty;
    },
    getState: function (withTentative) {
      if (withTentative === undefined) withTentative = true;

      let transformations = this.transformations.active;
      let curDisabled = this.transformations.disabled;
      let activeKeys = Object.keys(transformations);
      let disabledKeys = Object.keys(curDisabled);
      let fromKeys = [];
      fromKeys.push.apply(fromKeys, activeKeys.concat(disabledKeys));
      fromKeys = Array.from(new Set(fromKeys));
      activeKeys = new Set(activeKeys);
      disabledKeys = new Set(disabledKeys);
      fromKeys.sort();

      let tentative = withTentative ? this.tentative : null;

      return {
        keys: {
          active: activeKeys,
          disabled: disabledKeys,
          sorted: fromKeys,
        },
        t: {
          active: transformations,
          disabled: curDisabled,
        },
        tentative: tentative,
      };
    },
  };

  $(document).ready(function () {
    combinator.init();
    window.c = combinator;
  });
})(window.jQuery, window.JSONEditor);
