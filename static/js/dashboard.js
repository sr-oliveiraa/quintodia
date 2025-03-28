document.addEventListener('DOMContentLoaded', () => {
  const eventoSurpresa = document.querySelector('.evento-surpresa');
  const eventoCrise = document.querySelector('.evento-crise');

  if (eventoSurpresa) {
    setTimeout(() => {
      eventoSurpresa.style.display = 'none';
    }, 5000); // Esconde após 5 segundos
  }

  if (eventoCrise) {
    setTimeout(() => {
      eventoCrise.style.display = 'none';
    }, 5000); // Esconde após 5 segundos
  }
});
