function customFileBrowser(field_name, url, type, win) {
  // var url = "{{ fb_url }}?pop=4&type=" + type;
  var root = document.querySelector("body").getAttribute("root");
      url = "/" + root + "admin/filebrowser/browse/?pop=2&type=" + type;

  tinyMCE.activeEditor.windowManager.open(
      {
          'file': url,
          'width': 840,
          'height': 600,
          'resizable': "yes",
          'scrollbars': "yes",
          'inline': "no",
          'close_previous': "no"
      },
      {
          'window': win,
          'input': field_name,
          'editor_id': tinyMCE.activeEditor.id
      }
  );
  return false;
}