(function (JSONEditor, bulmaCollapsible, $) {
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

  const ui = {
    widgets: {
      areas: {
        structure: null,
        steps: null,
      },
      buttons: {
        use: null,
        reset: null,
        process: null,
      },
      inputs: {
        fileLoader: null,
        sourceFields: null,
      },
      forms: {
        process: null,
      },
      templates: {
        markers: null,
      },
    },
    placeholders: {
      step: "No JSON field is currently selected.",
    },
    editor: null,
    init: function () {
      let control = this;
      this.widgets.areas.structure = document.querySelector("#structureArea");
      this.widgets.areas.steps = document.querySelector("#stepsArea");

      this.widgets.inputs.fileLoader = document.querySelector(
        'input[type="file"]#dataSourceFile'
      );
      this.widgets.inputs.sourceFields =
        this.widgets.areas.steps.querySelector("input#sourceFields");

      this.widgets.buttons.use = this.widgets.areas.steps.querySelectorAll(
        'a[data-role="selector"]'
      );
      this.widgets.buttons.reset = this.widgets.areas.steps.querySelectorAll(
        'a[data-role="reset"]'
      );
      this.widgets.buttons.process = document.querySelector("button#process");

      this.widgets.templates.markers = document.querySelector(
        "select#markerTemplate"
      );

      this.widgets.forms.process =
        this.widgets.areas.steps.querySelector("form#processForm");

      this.widgets.areas.steps
        .querySelectorAll(".card-content:not([no-placeholder])")
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
    visualizeTable: function (container, propName, valName) {
      let table = document.createElement("table");
      table.className = "table is-fullwidth";
      let head = document.createElement("thead");
      head.classList.add("head");
      let headers = document.createElement("tr");
      let propCell = document.createElement("th");
      let valCell = document.createElement("th");
      propCell.innerText = propName;
      valCell.innerText = valName;
      headers.appendChild(propCell);
      headers.appendChild(valCell);
      head.appendChild(headers);
      table.appendChild(head);
      table.appendChild(document.createElement("tbody"));
      container.appendChild(table);
    },
    visualizeTemplateForDataSource: function (fields) {
      let cell = document.querySelector('[data-source="true"]');
      if (cell.innerHTML.trim().length > 0) {
        cell.innerHTML += ", ";
      }
      cell.innerHTML += fields.join(", ");
      this.widgets.inputs.sourceFields.value = cell.innerHTML;
    },
    visualizeTemplateRowForMarker: function (field) {
      let row = document.createElement("tr");
      let pathCell = document.createElement("td");
      let markerCell = document.createElement("td");
      pathCell.innerText = field;
      let clone = this.widgets.templates.markers.cloneNode(true);
      clone.setAttribute("data-name", field);
      markerCell.appendChild(clone);
      row.appendChild(pathCell);
      row.appendChild(markerCell);
      return row;
    },
    visualizeTemplateForMarker: function (fields, container) {
      if (container.childNodes.length == 0) {
        this.visualizeTable(container, "JSON path", "Marker");
      }
      let tbody = container.querySelector("table tbody");
      for (let i = 0, len = fields.length; i < len; i++) {
        tbody.appendChild(this.visualizeTemplateRowForMarker(fields[i]));
      }
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
            parentContainer = document.querySelector("#" + href),
            recordContainer = parentContainer.querySelector(".card-content");

          if (templateKey == "markers") {
            if (!importer.template.isRecorded(templateKey)) {
              recordContainer.innerHTML = "";
            }
            control.visualizeTemplateForMarker(fields, recordContainer);
          } else if (templateKey == "dataSource") {
            control.visualizeTemplateForDataSource(fields, recordContainer);
          }
          parentContainer.style.height = parentContainer.scrollHeight + "px";
          importer.template.record(templateKey, fields);
        });
      });

      this.widgets.buttons.reset.forEach(function (x) {
        x.addEventListener("click", function (e) {
          let target = e.target,
            href = target.getAttribute("data-href");

          let templateKey = href.replace("Step", ""),
            parentContainer = document.querySelector("#" + href),
            recordContainer = parentContainer.querySelector(".card-content");

          parentContainer.style.height = "";
          if (templateKey == "markers") {
            recordContainer.innerHTML = control.placeholders.step;
          } else if (templateKey == "dataSource") {
            let cell = document.querySelector('[data-source="true"]');
            cell.innerHTML = "";
            this.widgets.inputs.sourceFields.value = "";
          }
          parentContainer.style.height = parentContainer.scrollHeight + "px";
          importer.template.reset(templateKey);
        });
      });

      this.widgets.buttons.process.addEventListener(
        "click",
        function (e) {
          e.preventDefault();
          e.stopPropagation();

          let form = control.widgets.forms.process,
            fdata = $(form).serializeObject();

          let markerSelects = form.querySelectorAll("select[data-name]"),
            markerMapping = {};

          for (let i = 0, len = markerSelects.length; i < len; i++) {
            let s = markerSelects[i];
            markerMapping[s.getAttribute("data-name")] = s.value;
          }
          fdata["markerMapping"] = markerMapping;

          $.ajax({
            method: form.getAttribute("method"),
            url: form.getAttribute("action"),
            dataType: "json",
            data: {
              data: JSON.stringify(fdata),
              // This assumes that the file on top of the queue
              // is the one we're working with. OK for starters,
              // but need a better system later, probably.
              fileData: JSON.stringify(importer.getLatest()),
              csrfmiddlewaretoken: form.querySelector(
                'input[name="csrfmiddlewaretoken"]'
              ).value,
            },
            success: function (data) {
              alert(data);
            },
            error: function () {
              console.log("ERROR!");
            },
          });
        },
        false
      );

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
      window.imp = importer;
      window.ui = ui;
    },
    false
  );
})(window.JSONEditor, window.bulmaCollapsible, window.jQuery);
