/**
 * name: comments
 * description: A plugin adding a text field to a marker's context menu, potentially shared between markers
 * admin_filter: boolean
 * author: Dmytro Kalpakchi
 */

var plugin = function (cfg, labeler) {
  let config = {
    name: "comments",
    verboseName: "Add a comment",
    storeFor: "label", // one of "label", "relation"
    dispatch: {}, // an event to be dispatched on update
    subscribe: [],
    allowSingletons: false, // takes effect only if storeFor = "relation"
  };

  function isDefined(x) {
    return x != null && x !== undefined;
  }

  if (isDefined(cfg)) {
    for (let k in cfg) {
      config[k] = cfg[k];
    }
  }

  return {
    name: config.name,
    verboseName: config.verboseName,
    storage: {},
    dispatch: config.dispatch,
    subscribe: config.subscribe,
    storeFor: config.storeFor,
    allowSingletons: config.allowSingletons,
    isAllowed: function (obj) {
      if (this.storeFor == "relation") {
        let relSpan = obj.querySelector("[data-m]"),
          relSpanDefined = isDefined(relSpan);

        if (relSpanDefined) {
          return relSpan.textContent != "+";
        } else {
          return this.allowSingletons;
        }
      } else {
        return true;
      }
    },
    exec: function (label, menuItem) {
      let id = label.getAttribute("data-i"),
        storage = this.storage,
        commentInput = document.createElement("input"),
        scope = undefined,
        prefix = undefined,
        control = this;

      if (this.storeFor == "label") {
        scope = "l" + id;
        prefix = "label";
      } else if (this.storeFor == "relation") {
        let rel = label.querySelector('[data-m="r"]');
        prefix = "relation";
        if (rel) {
          scope = "r" + rel.textContent;
        } else if (this.allowSingletons) {
          scope = "sr" + id;
        }
      }

      if (scope !== undefined) {
        commentInput.setAttribute("data-s", scope);

        if (storage["sr" + id] && scope.startsWith("r")) {
          storage[scope] = storage["sr" + id];
          delete storage["sr" + id];
        }
        commentInput.value = storage[scope] || "";

        commentInput.addEventListener(
          "change",
          function (e) {
            let target = e.target;
            storage[target.getAttribute("data-s")] = target.value;
          },
          false
        );
        commentInput.addEventListener("blur", function () {
          let relSpan = label.querySelector('[data-m="r"]');

          const event = new CustomEvent("labeler_" + prefix + "_blur", {
            detail: {
              sender:
                control.storeFor == "relation" && isDefined(relSpan)
                  ? relSpan.textContent
                  : id,
            },
          });
          document.dispatchEvent(event);
        });

        tippy(isDefined(menuItem) ? menuItem : label, {
          content: commentInput,
          interactive: true,
          placement: "right",
          trigger: "click",
        });
      }
    },
  };
};