(function (JSONEditor, django) {
  const adminJsonEditors = {
    editors: {},
    specs: {},
    initialized: false,
    initEditor: function (field, containerId, options, textAreaId, value) {
      if (containerId.includes("__prefix__")) {
        this.specs[containerId.replace("__prefix__", "\\d+")] = {
          field: field,
          opt: options,
          taId: textAreaId,
          val: value,
        };
      } else {
        let container = document.querySelector("#" + containerId),
          ctx = this;
        this.editors[containerId] = new JSONEditor(container, options);
        this.editors[containerId].on("ready", function () {
          ctx.editors[containerId].on("change", function () {
            let editor = ctx.editors[containerId];
            let errors = editor.validate();
            if (errors.length) {
              console.log(errors);
            } else {
              let json = editor.getValue();
              document.getElementById(textAreaId).value = JSON.stringify(json);
            }
          });
          if (value !== undefined) ctx.editors[containerId].setValue(value);
        });
      }
    },
    findSpecs: function (idx) {
      let ctx = this;
      for (let key in ctx.specs) {
        let regex = new RegExp("(" + key + ")");
        let cand = idx + "-" + ctx.specs[key].field + "_editor";
        if (cand.match(regex))
          return {
            key: key,
            id: cand,
          };
      }
      return undefined;
    },
    initEvents: function () {
      let ctx = this;
      django
        .jQuery(document)
        .on("djnesting:added", function (e, $form, $inline) {
          let inline = $inline[0];
          let data = ctx.findSpecs(inline.id);

          if (data !== undefined) {
            let inlineSpecs = ctx.specs[data.key];
            ctx.initEditor(
              inlineSpecs.field,
              data.id,
              inlineSpecs.opt,
              inlineSpecs.taId,
              inlineSpecs.val
            );
          }
        });
    },
  };

  adminJsonEditors.initEvents();

  window.adminJsonEditors = adminJsonEditors;
})(window.JSONEditor, window.django);
