$(document).ready(function() {
  var chunks = [],
      selectorArea = document.querySelector('.selector'),
      resetTextHTML = selectorArea.innerHTML,
      resetText = selectorArea.textContent;

  $.fn.serializeObject = function() {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
      if (o[this.name]) {
        if (!o[this.name].push) {
          o[this.name] = [o[this.name]];
        }
        o[this.name].push(this.value || '');
      } else {
        o[this.name] = this.value || '';
      }
    });
    return o;
  };

  function mergeWithNeighbors(node) {
    // check if text node
    var next = node.nextSibling,
        prev = node.previousSibling,
        parent = node.parentNode;

    if (prev.nodeType == 3 && next.nodeType == 3) {
      parent.replaceChild(document.createTextNode(prev.data + node.textContent + next.data), prev);
      parent.removeChild(node);
      parent.removeChild(next);
    } else if (prev.nodeType == 3) {
      parent.replaceChild(document.createTextNode(prev.data + node.textContent), prev);
      parent.removeChild(node);
    } else if (next.nodeType == 3) {
      parent.replaceChild(document.createTextNode(node.textContent + next.data), node);
      parent.removeChild(next);
    }
  }

  function removeAllChildren(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function resetArticle() {
    var node = document.querySelector('.selector');
    removeAllChildren(node);
    node.innerHTML = resetTextHTML;
  }

  $('.marker.tag').on('click', function() {
    var chunk = chunks[chunks.length - 1],
        idc = chunks.length - 1
        cls = this.className.split(' ').filter(c => c != 'marker').join(' '),
        leftTextNode = document.createTextNode(chunk['text'].slice(0, chunk['start'])),
        markedSpan = document.createElement('span'),
        deleteMarkedBtn = document.createElement('button'),
        rightTextNode = document.createTextNode(chunk['text'].slice(chunk['end'])),
        parent = chunk['node'].parentNode;
    markedSpan.className = cls + " is-medium";
    markedSpan.textContent = chunk['text'].slice(chunk['start'], chunk['end']);
    deleteMarkedBtn.className = 'delete is-small';
    deleteMarkedBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var el = e.target,
          parent = el.parentNode; // actual span

      delete chunks[idc];
      mergeWithNeighbors(parent);
      window.chunks = chunks;
    }, true);
    markedSpan.appendChild(deleteMarkedBtn)

    parent.replaceChild(leftTextNode, chunk['node']);
    parent.insertBefore(markedSpan, leftTextNode.nextSibling);
    parent.insertBefore(rightTextNode, markedSpan.nextSibling);
    chunk['marked'] = true;
    chunk['label'] = this.textContent;
    delete chunk['node']
    window.chunks = chunks;
  });

  $('.selector').on('mouseup', function(e) {
    if (!$(e.target).hasClass('delete')) {
      var selection = window.getSelection(),
          chunk = {};
      chunk['node'] = selection.anchorNode;
      chunk['text'] = selection.anchorNode.data;
      if (selection.anchorOffset > selection.focusOffset) {
        chunk['start'] = selection.focusOffset;
        chunk['end'] = selection.anchorOffset;
      } else {
        chunk['start'] = selection.anchorOffset;
        chunk['end'] = selection.focusOffset;
      }
      chunk['marked'] = false;
      chunk['label'] = null;

      if (chunks.length == 0 || (chunks.length > 0 && chunks[chunks.length - 1]['marked'])) {
        chunks.push(chunk);
      } else {
        chunks[chunks.length - 1] = chunk;
      }
    }
  })

  $('#inputForm .submit.button').on('click', function(e) {
    e.preventDefault();

    var inputFormData = $('#inputForm').serializeObject();
    inputFormData['chunks'] = JSON.stringify(chunks);
    inputFormData['context'] = resetText;

    $.ajax({
      method: "POST",
      url: inputForm.action,
      dataType: "json",
      data: inputFormData,
      success: function(data) {
        console.log("SUCCESS!")
        console.log(data)
      },
      error: function() {
        console.log("ERROR!")
      }
    })

    resetArticle();
  })
});