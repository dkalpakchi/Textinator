(function ($, adminJsonEditors, JSONEditor) {
  let templates = {
    TextFile: {
      files: [],
      folders: [],
    },
    Json: {
      files: [],
      folders: [],
      key: "",
    },
    PlainText: {
      texts: [],
    },
    TextsAPI: {
      endpoint: "",
    },
  };

  let schemas = {
    PlainText: {
      type: "object",
      properties: {
        texts: {
          type: "array",
          items: {
            type: "string",
            format: "textarea",
          },
        },
      },
    },
    TextFile: {
      type: "object",
      properties: {
        files: {
          type: "array",
          items: {
            type: "string",
          },
        },
        folders: {
          type: "array",
          items: {
            type: "string",
          },
        },
      },
    },
    TextsAPI: {
      type: "object",
      endpoint: {
        type: "string",
      },
    },
    Json: {
      type: "object",
      properties: {
        files: {
          type: "array",
          items: {
            type: "string",
          },
        },
        folders: {
          type: "array",
          items: {
            type: "string",
          },
        },
        key: "string",
      },
    },
  };

  function updateSchema(spec_editor, option) {
    // NOTE: `spec` everywhere is just the name of the field in the model
    //       if the name changes djang-admin-json-editor, changes the name of JS variable as well
    if (schemas.hasOwnProperty(option)) {
      let schema = schemas[option],
        element = spec_editor.element;
      spec_editor.destroy();
      schema["title"] = " ";
      spec_editor = new JSONEditor(element, {
        theme: "spectre",
        schema: schema,
      });

      spec_editor.on("ready", function () {
        spec_editor.on("change", function () {
          var errors = spec_editor.validate();
          if (errors.length) {
            console.log(errors);
          } else {
            var json = spec_editor.getValue();
            document.getElementById("id_spec").value = JSON.stringify(json);
          }
        });
      });
    }
    return spec_editor;
  }

  $(document).ready(function () {
    let spec_editor = adminJsonEditors.editors.spec_editor;

    $("#id_source_type").on("select2:select", function (e) {
      let $target = $(e.target);
      let option = $target.find("option:selected").val();

      spec_editor = updateSchema(spec_editor, option);

      spec_editor.on("ready", function () {
        spec_editor.setValue(templates[option]);

        $('input[name="root[db_type]"]').off("change");
        $('input[name="root[db_type]"]').on("change", function (e) {
          if (e.target.value == "mongodb") {
            var options = { ...templates[option] };
            options["db_type"] = e.target.value;
            options["collection"] = "";
            options["field"] = "";
            spec_editor.setValue(options);
          } else if (
            ["mysql", "postgresql", "postgres"].includes(e.target.value)
          ) {
            let options = { ...templates[option] };
            options["db_type"] = e.target.value;
            options["rand_dp_query"] = "";
            options["size_query"] = "";
            spec_editor.setValue(options);
          }
        });
      });
    });
  });
})(window.$, window.adminJsonEditors, window.JSONEditor);
