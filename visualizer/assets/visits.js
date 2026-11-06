// Contador de visitas del sitio publicado: GoatCounter, sin cookies ni datos
// personales. Panel: https://cs2-osm-toolkit.goatcounter.com
//
// Lo cargan la landing (src/shared/landing.py) y map.html. Solo cuenta en
// osyanne.github.io: ni en localhost (tests, miniaturas) ni en la copia que
// alguien publique desde un fork. Para no contar las visitas propias, abrir
// una vez .../visualizer/#toggle-goatcounter en cada navegador.
(function () {
  "use strict";
  if (location.hostname !== "osyanne.github.io") return;

  var ROOT = "/CitiesSkylines2-osm-toolkit/";

  // La raíz del sitio (index.html) salta a la landing y deja guardado de dónde
  // venía la visita: después del salto, document.referrer es la raíz, o nada.
  // Se lee al cargar, así no queda para una página que se abra después.
  var arrivedFrom = null;
  try {
    arrivedFrom = sessionStorage.getItem("cs2-visit-referrer");
    sessionStorage.removeItem("cs2-visit-referrer");
  } catch (e) { /* sin sessionStorage: cuenta el referrer del navegador */ }

  function isRootPage(url) {
    try {
      var u = new URL(url);
      return u.origin === location.origin && (u.pathname === ROOT || u.pathname === ROOT + "index.html");
    } catch (e) {
      return false;
    }
  }

  window.goatcounter = {
    // En el mapa, una ruta por ciudad: sin la vista ni parámetros de campaña,
    // que GoatCounter igual lee de la consulta
    path: function (p) {
      if (!/\/map\.html$/.test(location.pathname)) return p;
      var city = new URLSearchParams(location.search).get("city");
      return city ? location.pathname + "?city=" + encodeURIComponent(city) : null;
    },
    referrer: function (r) {
      return arrivedFrom !== null && (!r || isRootPage(r)) ? arrivedFrom : r;
    },
  };

  // Versión fija con su hash: si el archivo cambia, el navegador no lo corre
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://gc.zgo.at/count.v5.js";
  s.crossOrigin = "anonymous";
  s.integrity = "sha384-atnOLvQb9t+jTSipvd75X2yginT4PjVbqDdlJAmxMm+wYElFmeR6EmLP5bYeoRVQ";
  s.setAttribute("data-goatcounter", "https://cs2-osm-toolkit.goatcounter.com/count");
  document.head.appendChild(s);
})();
