function toggleEditSection() {
  var editSection = document.getElementById('edit-section');
  if (editSection.classList.contains('hidden')) {
    editSection.classList.remove('hidden');
  } else {
    editSection.classList.add('hidden');
  }
}

function voltarPagina() {
  window.history.back(); // Volta à página anterior
}
