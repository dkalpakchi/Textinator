(function ($, JSONEditor) {
  let utils = {
    isDefined: function (n) {
      return n !== undefined && n !== null;
    },
    setUnion: function (setA, setB) {
      let _union = new Set(setA);
      for (const elem of setB) {
        _union.add(elem);
      }
      return _union;
    },
  };

  let combinator = {
    transformations: {},
    tentative: null,
    maxTransformationDepth: 100,
    placeholders: {
      remove: "[[empty]]",
      space: "*",
    },
    init: function () {
      this.sourceArea = document.querySelector("textarea#source");
      this.targetArea = document.querySelector("textarea#target");
      this.generationArea = document.querySelector("#generationArea fieldset");
      this.tentative = this.initTransformation();
      this.recordForm = document.querySelector("#recordForm");
      this.generateButton = document.querySelector("button#generate");
      this.transformationMemoryArea = document.querySelector(
        "div#transformationMemoryArea"
      );
      this.initEvents();
      this.preloadRules();
    },
    preloadRules: function () {
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
          control.saveToDb("update");
        } else {
          control.transformations[ct.from] = ct;
          control.saveToDb();
        }
        control.tentative = control.initTransformation();
        control.targetArea.value = "";
        control.visualize(false);
      });

      this.generateButton.addEventListener("click", function () {
        let sources = control.sourceArea.value.split("\n");
        control.generationArea.innerHTML = "";
        let res = control.transform(sources, control.maxTransformationDepth);
        control.showHierarchical(res);
      });
    },
    jsonifyTentative: function () {
      let copy = Object.assign({}, this.tentative);
      copy.to = Array.from(copy.to);
      return copy;
    },
    saveToDb: function (op) {
      // saves a tentative rule to DB, so that it becomes permanent
      if (!utils.isDefined(op)) op = "save";

      let control = this;

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
    createBulmaControl: function (isExpanded) {
      if (!utils.isDefined(isExpanded)) isExpanded = false;
      let control = document.createElement("div");
      control.className = "control";
      if (isExpanded) control.className += " is-expanded";
      return control;
    },
    createBulmaButton: function (className, name) {
      let btn = document.createElement("button");
      btn.className = className;
      btn.innerHTML = name;
      return btn;
    },
    createBulmaCheckbox: function (className, name) {
      let label = document.createElement("label");
      let inp = document.createElement("input");
      inp.setAttribute("type", "checkbox");
      inp.className = "is-hidden";
      let btn = document.createElement("span");
      btn.className = className;
      btn.innerHTML = name;

      inp.addEventListener("change", function (e) {
        let target = e.target;
        if (target.checked) {
          btn.classList.add("is-hovered");
        } else {
          btn.classList.remove("is-hovered");
        }
      });

      label.appendChild(inp);
      label.appendChild(btn);
      return label;
    },
    createBulmaRadio: function (className, name, content, checked) {
      let label = document.createElement("label");
      let inp = document.createElement("input");
      inp.setAttribute("type", "radio");
      inp.className = "is-hidden";
      inp.setAttribute("name", name);
      let btn = document.createElement("span");
      btn.setAttribute("for", name);
      btn.className = className;
      btn.innerHTML = content;

      inp.addEventListener("change", function (e) {
        let target = e.target;
        let radioButtons = document.querySelectorAll(
          '[for="' + target.name + '"]'
        );

        for (let i = 0, len = radioButtons.length; i < len; i++) {
          radioButtons[i].classList.remove("is-hovered");
        }

        if (target.checked) {
          btn.classList.add("is-hovered");
        }
      });

      if (!utils.isDefined) checked = false;

      if (checked) {
        inp.checked = true;
        btn.classList.add("is-hovered");
      }

      label.appendChild(inp);
      label.appendChild(btn);
      return label;
    },
    createGenerated: function (s) {
      let container = document.createElement("div");
      container.className = "field has-addons";

      let inpControl = this.createBulmaControl(true);

      let inp = document.createElement("input");
      inp.setAttribute("type", "text");
      inp.value = s;
      inp.className = "input is-small";
      inpControl.appendChild(inp);

      let noAddonControl = this.createBulmaControl();
      let noButton = this.createBulmaCheckbox(
        "button is-danger is-outlined is-small",
        '<i class="fas fa-times">'
      );
      noAddonControl.appendChild(noButton);
      container.appendChild(noAddonControl);
      container.appendChild(inpControl);

      return container;
    },
    showHierarchical: function (data) {
      const options = {
        mode: "tree",
        onCreateMenu: function (items, node) {
          const path = node.path;

          // log the current items and node for inspection
          console.log("items:", items, "node:", node);

          if (path) {
            let insertIndex = items.findIndex((x) => x.text == "Insert");

            items.splice(insertIndex + 1, 0, {
              text: "Convert", // the text for the menu item
              title: "convert element to...", // the HTML title attribute
              submenu: [
                {
                  text: "Object",
                  title: "Object",
                },
              ],
            });
          }

          return items;
        },
      };
      const editor = new JSONEditor(this.generationArea, options);
      editor.set(data);
    },
    transform: function (sources, maxDepth) {
      if (!utils.isDefined(sources) || sources.length === 0 || maxDepth < 0) {
        return new Set();
      }

      let res = maxDepth == this.maxTransformationDepth ? {} : new Set();
      for (let i = 0, len = sources.length; i < len; i++) {
        let source = sources[i].trim();

        if (maxDepth == this.maxTransformationDepth) res[source] = new Set();

        for (let key in this.transformations) {
          let t = this.transformations[key];

          if (source.includes(t.from)) {
            let to = Array.from(t.to);
            for (let toId = 0, toLen = to.length; toId < toLen; toId++) {
              if (
                to[toId].length === 0 ||
                !to.some((x) => source.includes(x))
              ) {
                let target = source.slice();
                let toRep = to[toId];

                if (toRep.startsWith(this.placeholders.space)) {
                  toRep = toRep.replace(this.placeholders.space, " ");
                }

                target = target.replaceAll(t.from, toRep);
                target = target.replaceAll(/ {2,}/gi, " ").trim();
                if (maxDepth == this.maxTransformationDepth) {
                  res[source].add(target);
                  res[source] = utils.setUnion(
                    res[source],
                    this.transform([target], maxDepth - 1)
                  );
                } else {
                  res.add(target);
                  res = utils.setUnion(
                    res,
                    this.transform([target], maxDepth - 1)
                  );
                }
              }
            }
          }
        }
      }

      if (maxDepth == this.maxTransformationDepth) {
        for (var key in res) {
          res[key] = Array.from(res[key]);
        }
      }

      return res;
    },
    deleteTransformation: function (i) {
      let oldTentative = Object.assign({}, this.tentative);
      this.tentative = this.transformations[i];
      this.saveToDb("delete");
      this.tentative = oldTentative;
      return delete this.transformations[i];
    },
    isEmptyTransformation: function (i) {
      return this.transformations[i].to.size === 0;
    },
    deleteTransformationClause: function (i, j) {
      this.transformations[i].to.delete(j);
      let oldTentative = Object.assign({}, this.tentative);
      this.tentative = this.transformations[i];
      this.saveToDb("update");
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

      if (t.action.length > 0) p.innerText = t.action + ": ";
      if (t.from.length > 0) {
        p.innerText += t.from + " ";
      }

      let to = Array.from(t.to);

      if (to.length > 0) {
        if (t.from.length > 0) p.innerText += " -> ";
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
              rule.parentNode.removeChild(rule);
              return;
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
  };

  $(document).ready(function () {
    combinator.init();
    window.c = combinator;
  });
})(window.jQuery, window.JSONEditor);
