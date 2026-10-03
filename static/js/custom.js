// =========================================================
// Spa Relax - JS general
// Va en static/js/custom.js
// Se carga DESPUES de bootstrap.bundle.min.js en base.html
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

  // 1. Marca como "active" el link del navbar que corresponde
  //    a la página actual, comparando con la URL del navegador.
  //    Util porque el sitio no usa un framework de frontend,
  //    solo Django + Bootstrap.
  const rutaActual = window.location.pathname;
  document.querySelectorAll(".navbar-spa .nav-link").forEach(function (link) {
    const rutaLink = link.getAttribute("href");
    if (rutaLink && rutaActual.startsWith(rutaLink) && rutaLink !== "/") {
      link.classList.add("active");
    }
  });

  // 2. Activa los tooltips de Bootstrap en toda la app
  //    (por ejemplo, para mostrar detalles de una terapia al pasar el mouse)
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

  // 3. Confirmación simple antes de acciones sensibles
  //    (ej: botón "Nueva asignación" o "Agregar cita" en los paneles)
  document.querySelectorAll(".confirmar-accion").forEach(function (boton) {
    boton.addEventListener("click", function (e) {
      const ok = confirm("¿Confirmas esta acción?");
      if (!ok) {
        e.preventDefault();
      }
    });
  });

});

// =========================================================
// Visor de fotos: al tocar una .foto-evidencia se abre en grande
// (funciona en la vista de usuario y en la de administrador)
// =========================================================
document.addEventListener("DOMContentLoaded", function () {
  const fotos = document.querySelectorAll("img.foto-evidencia");
  if (!fotos.length || typeof bootstrap === "undefined") return;

  const el = document.createElement("div");
  el.className = "modal fade";
  el.tabIndex = -1;
  el.setAttribute("aria-hidden", "true");
  el.innerHTML =
    '<div class="modal-dialog modal-dialog-centered modal-xl">' +
    '<div class="modal-content bg-transparent border-0">' +
    '<div class="text-end mb-2"><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Cerrar"></button></div>' +
    '<img class="lightbox-img" alt="">' +
    "</div></div>";
  document.body.appendChild(el);
  const modal = new bootstrap.Modal(el);
  const grande = el.querySelector("img");

  fotos.forEach(function (foto) {
    foto.addEventListener("click", function () {
      grande.src = foto.src;
      grande.alt = foto.alt;
      modal.show();
    });
  });
});
