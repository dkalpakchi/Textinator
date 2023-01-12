(function ($) {
  let helpers = {
    verbalizeTransformation: function (t, i) {
      let p = document.createElement("div");
      p.setAttribute("data-i", i);
      if (t.action.length > 0) p.innerText = t.action + ": ";
      if (t.from.length > 0) {
        p.innerText += t.from + " ";
      }

      let to = Array.from(t.to);

      if (to.length > 0) {
        if (t.from.length > 0) p.innerText += " -> ";
        for (let i = 0, len = to.length; i < len; i++) {
          p.innerText += to[i];
          if (i < to.length - 1) {
            p.innerText += " OR ";
          }
        }
      }

      if (p.innerText.length > 0) {
        let deleteButton = document.createElement("button");
        deleteButton.className = "button is-small";
        deleteButton.innerText = "Delete";

        deleteButton.addEventListener(
          "click",
          function (e) {
            let target = e.target,
              ruleDiv = target.parentNode,
              idx = ruleDiv.getAttribute("data-i");

            let res = combinator.deleteTransformation(idx);
            if (!res)
              combinator.currentTransformation =
                combinator.initTransformation();
            ruleDiv.parentNode.removeChild(ruleDiv);
          },
          false
        );

        p.appendChild(deleteButton);
        return p;
      } else {
        return null;
      }
    },
  };

  let combinator = {
    transformations: {},
    currentTransformation: null,
    init: function () {
      this.sourceArea = document.querySelector("textarea#source");
      this.targetArea = document.querySelector("textarea#target");
      this.generationArea = document.querySelector("textarea#generationArea");
      this.currentTransformation = this.initTransformation();
      this.renewButton = document.querySelector("button#renew");
      this.recordButton = document.querySelector("button#record");
      this.generateButton = document.querySelector("button#generate");
      this.transformationMemoryArea = document.querySelector(
        "div#transformationMemoryArea"
      );
      this.initEvents();
    },
    initTransformation: function () {
      return {
        action: "",
        from: "",
        to: new Set(),
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
            control.currentTransformation["from"] = text
              .substring(selStart, selEnd)
              .trim();
          }
        },
        false
      );

      this.recordButton.addEventListener(
        "click",
        function () {
          let replacement = control.targetArea.value.trim(),
            toRemove = control.currentTransformation["from"];

          if (replacement.length > 0) {
            control.currentTransformation["action"] =
              toRemove.length > 0 ? "replace" : "add";
            let options = replacement.split("\n");
            for (let i = 0, len = options.length; i < len; i++) {
              control.currentTransformation["to"].add(options[i]);
            }
          } else {
            control.currentTransformation["action"] = "remove";
          }
          control.verbalizeTransformations();
        },
        false
      );

      this.renewButton.addEventListener("click", function () {
        let ct = control.currentTransformation;
        if (control.checkUpdate(ct.from)) {
          let to = Array.from(ct.to);
          for (let i = 0, len = to.length; i < len; i++) {
            control.transformations[ct.from].to.add(to[i]);
          }
        } else {
          control.transformations[ct.from] = ct;
        }
        control.currentTransformation = control.initTransformation();
        control.targetArea.value = "";
        control.verbalizeTransformations(false);
      });

      this.generateButton.addEventListener("click", function () {
        let sources = control.sourceArea.value.split("\n");
        control.generationArea.value = "";
        control.transform(sources, 1);
      });
    },
    transform: function (sources, maxDepth) {
      if (maxDepth < 0) {
        return;
      }

      let targets = [];
      for (let key in this.transformations) {
        let t = this.transformations[key];

        for (let i = 0, len = sources.length; i < len; i++) {
          let source = sources[i];
          if (source.includes(t.from)) {
            let to = Array.from(t.to);
            for (let to_id = 0, to_len = to.length; to_id < to_len; to_id++) {
              let target = source.slice();
              target = target.replaceAll(t.from, to[to_id]);
              targets.push(target);
              this.generationArea.value += target + "\n";
            }
          }
        }
      }
      if (targets.length > 0) {
        this.transform(targets, --maxDepth);
      }
    },
    deleteTransformation: function (i) {
      return delete this.transformations[i];
    },
    verbalizeTransformations: function (addCurrent) {
      if (addCurrent === undefined) addCurrent = true;

      this.transformationMemoryArea.innerHTML = "";
      let transformations = this.transformations;
      let control = this;
      for (let key in transformations) {
        let rule = helpers.verbalizeTransformation(transformations[key], key);
        if (rule !== null) this.transformationMemoryArea.appendChild(rule);
      }

      if (addCurrent) {
        let ct = control.currentTransformation;
        this.transformationMemoryArea.appendChild(
          helpers.verbalizeTransformation(ct, ct.from)
        );
      }
    },
  };

  $(document).ready(function () {
    combinator.init();
    window.c = combinator;
  });
})(window.jQuery);
