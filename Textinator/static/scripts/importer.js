(function (JSONEditor, bulmaCollapsible) {
  const utils = {
    mime: {
      json: "application/json",
    },
    isDefined: function (x) {
      return x !== null && x !== undefined;
    },
    isString: function (x) {
      return typeof x === "string" || x instanceof String;
    },
    haveIdenticalStructure: function (arr) {
      let keys = arr.map(function (x) {
        let objKeys = Object.keys(x);
        objKeys.sort();
        return objKeys.join("|");
      });
      return new Set(keys).size == 1;
    },
    trimStrings: function (obj, N) {
      for (let k in obj) {
        if (utils.isString(obj[k]) && obj[k].length > N) {
          obj[k] = obj[k].substring(0, N) + "...";
        }
      }
      return obj;
    },
  };
  window.utils = utils;

  const ui = {
    widgets: {
      areas: {
        structure: null,
        steps: null,
      },
      buttons: {
        use: null,
        reset: null,
      },
      inputs: {
        fileLoader: null,
      },
    },
    placeholders: {
      step: "No JSON field is currently selected.",
    },
    editor: null,
    init: function () {
      let control = this;
      this.widgets.inputs.fileLoader = document.querySelector(
        'input[type="file"]#dataSourceFile'
      );
      this.widgets.areas.structure = document.querySelector("#structureArea");
      this.widgets.areas.steps = document.querySelector("#stepsArea");
      this.widgets.buttons.use = this.widgets.areas.steps.querySelectorAll(
        'a[data-role="selector"]'
      );
      this.widgets.buttons.reset = this.widgets.areas.steps.querySelectorAll(
        'a[data-role="reset"]'
      );

      this.widgets.areas.steps
        .querySelectorAll(".card-content")
        .forEach(function (x) {
          x.innerHTML = control.placeholders.step;
        });

      this.initJsonEditor();
      this.initEvents();
    },
    initJsonEditor: function () {
      if (!utils.isDefined(this.editor)) {
        const options = {
          mode: "tree",
          mainMenuBar: false,
          navigationBar: false,
        };
        this.editor = new JSONEditor(this.widgets.areas.structure, options);
      }
    },
    visualizeTemplate: function () {
      let template = importer.template;
      console.log(template);
    },
    initEvents: function () {
      let control = this;
      this.widgets.inputs.fileLoader.addEventListener(
        "change",
        function (e) {
          let target = e.target;
          let files = target.files;

          for (let i = 0, len = files.length; i < len; i++) {
            if (files[i].type == utils.mime.json) {
              importer.importFromJsonFile(files[i]);
              break;
            }
          }
        },
        false
      );

      this.widgets.buttons.use.forEach(function (x) {
        x.addEventListener("click", function (e) {
          let target = e.target,
            href = target.getAttribute("data-href"),
            selection = control.editor.multiselection.nodes,
            fields = [];
          for (let i = 0, len = selection.length; i < len; i++) {
            let node = selection[i];
            fields.push(node.getPath().join("."));
          }

          let templateKey = href.replace("Step", ""),
            recordContainer = document.querySelector(
              "#" + href + " .card-content"
            );

          if (importer.template.isRecorded(templateKey)) {
            recordContainer.innerHTML += ", " + fields.join(", ");
          } else {
            recordContainer.innerHTML = fields.join(", ");
          }
          importer.template.record(templateKey, fields);
        });
      });

      this.widgets.buttons.reset.forEach(function (x) {
        x.addEventListener("click", function (e) {
          let target = e.target,
            href = target.getAttribute("data-href");

          let templateKey = href.replace("Step", ""),
            recordContainer = document.querySelector(
              "#" + href + " .card-content"
            );

          recordContainer.innerHTML = control.placeholders.step;
          importer.template.reset(templateKey);
        });
      });

      document.addEventListener(importer.events.enq, function (e) {
        let obj = e.detail;

        if (utils.isDefined(obj)) {
          if (Array.isArray(obj)) {
            // either an array of objects with identical structure (so jsonlines)
            if (utils.haveIdenticalStructure(obj)) {
              control.editor.set(utils.trimStrings(obj[0], 50));
            }
          } else if (obj.hasOwnProperty("data") && Array.isArray(obj.data)) {
            // or a json object with a "data" field,
            // which in turn is an array of objects with identical structure
            if (utils.haveIdenticalStructure(obj.data)) {
              control.editor.set(utils.trimStrings(obj.data[0], 50));
            }
          }
        }
      });
    },
  };

  const importer = {
    queue: [],
    template: {
      keys: new Set(),
      value: null,
      init: function () {
        let t = {
          title: "",
          lang: "",
          desc: "",
          dataSource: [],
          markers: [],
        };
        this.keys = new Set(Object.keys(t));
        this.value = t;
      },
      record: function (k, v) {
        if (this.keys.has(k)) {
          this.value[k] = v;
        }
      },
      reset: function (k) {
        if (this.keys.has(k)) {
          if (utils.isString(this.value[k])) {
            this.value[k] = "";
          } else if (Array.isArray(this.value[k])) {
            this.value[k] = [];
          }
        }
      },
      isRecorded: function (k) {
        return utils.isDefined(this.value[k]) && this.value[k].length > 0;
      },
    },
    events: {
      enq: "ENQUEUE",
    },
    init: function () {
      this.template.init();
      ui.init();
    },
    importFromJsonFile: function (f) {
      let ctx = this;
      const fr = new FileReader();
      fr.addEventListener("load", function () {
        let item = JSON.parse(fr.result);
        ctx.queue.push(item);
        const enqEvent = new CustomEvent(ctx.events.enq, { detail: item });
        document.dispatchEvent(enqEvent);
      });

      fr.readAsText(f);
    },
    getLatest: function () {
      return this.queue[this.queue.length - 1];
    },
  };

  document.addEventListener(
    "DOMContentLoaded",
    function () {
      importer.init();
      const collapsibles = bulmaCollapsible.attach();

      collapsibles.forEach(function (instance) {
        instance.on("after:expand", function () {
          // bug fix
          instance._originalHeight = instance.scrollHeight + "px";
        });
      });

      window.ui = ui;
      window.im = importer;
    },
    false
  );
})(window.JSONEditor, window.bulmaCollapsible);
