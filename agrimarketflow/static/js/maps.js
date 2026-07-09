/* maps.js — AgriMarketFlow AI
   Deux usages de l'API Google Maps JavaScript :
   1) initPickerMap()  : sélection de la position (inscription, publication de récolte)
   2) initRecolteMap() : visualisation de la récolte + prestataires suggérés (détail récolte)
*/

const AGRI_MAP_STYLE = [
  { elementType: "geometry", stylers: [{ color: "#f6f2e9" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#5b5a52" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#f6f2e9" }] },
  { featureType: "water", elementType: "geometry", stylers: [{ color: "#c9d9d0" }] },
  { featureType: "landscape", elementType: "geometry", stylers: [{ color: "#eee8d8" }] },
  { featureType: "poi", stylers: [{ visibility: "off" }] },
  { featureType: "road", elementType: "geometry", stylers: [{ color: "#ffffff" }] },
  { featureType: "administrative", elementType: "geometry.stroke", stylers: [{ color: "#c9c2a8" }] },
];

/* ---------- 1) Sélecteur de position (marqueur déplaçable) ---------- */
function initPickerMap() {
  const mapEl = document.getElementById("map-picker");
  if (!mapEl) return;

  const latInput = document.getElementById(mapEl.dataset.latInput);
  const lonInput = document.getElementById(mapEl.dataset.lonInput);
  const startLat = parseFloat(latInput.value) || -18.8792;
  const startLon = parseFloat(lonInput.value) || 47.5079;

  const map = new google.maps.Map(mapEl, {
    center: { lat: startLat, lng: startLon },
    zoom: 11,
    styles: AGRI_MAP_STYLE,
    streetViewControl: false,
    mapTypeControl: false,
  });

  const marker = new google.maps.Marker({
    position: { lat: startLat, lng: startLon },
    map,
    draggable: true,
    title: "Faites glisser pour ajuster la position",
  });

  function syncInputs(position) {
    latInput.value = position.lat().toFixed(6);
    lonInput.value = position.lng().toFixed(6);
  }

  marker.addListener("dragend", () => syncInputs(marker.getPosition()));

  map.addListener("click", (event) => {
    marker.setPosition(event.latLng);
    syncInputs(event.latLng);
  });

  const locateBtn = document.getElementById("btn-locate-me");
  if (locateBtn && navigator.geolocation) {
    locateBtn.addEventListener("click", () => {
      navigator.geolocation.getCurrentPosition((pos) => {
        const here = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        map.setCenter(here);
        map.setZoom(13);
        marker.setPosition(here);
        syncInputs(new google.maps.LatLng(here.lat, here.lng));
      });
    });
  }
}

/* ---------- 2) Carte récolte + prestataires suggérés ---------- */
function initRecolteMap() {
  const mapEl = document.getElementById("map-recolte");
  if (!mapEl) return;

  const data = JSON.parse(mapEl.dataset.payload);
  const center = { lat: data.recolte.lat, lng: data.recolte.lon };

  const map = new google.maps.Map(mapEl, {
    center,
    zoom: 9,
    styles: AGRI_MAP_STYLE,
    streetViewControl: false,
    mapTypeControl: false,
  });

  const bounds = new google.maps.LatLngBounds();
  const infoWindow = new google.maps.InfoWindow();

  const recolteMarker = new google.maps.Marker({
    position: center,
    map,
    title: data.recolte.libelle,
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 9,
      fillColor: "#C1440E",
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 2,
    },
  });
  recolteMarker.addListener("click", () => {
    infoWindow.setContent(`<strong>${data.recolte.libelle}</strong><br>${data.recolte.quantite} kg`);
    infoWindow.open(map, recolteMarker);
  });
  bounds.extend(center);

  data.prestataires.forEach((p) => {
    const pos = { lat: p.lat, lng: p.lon };
    const marker = new google.maps.Marker({
      position: pos,
      map,
      title: p.nom,
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 7,
        fillColor: p.disponible ? "#2F5233" : "#B4362A",
        fillOpacity: 1,
        strokeColor: "#ffffff",
        strokeWeight: 2,
      },
    });
    marker.addListener("click", () => {
      infoWindow.setContent(
        `<strong>${p.nom}</strong> (${p.type})<br>${p.distance_km} km ·
         ${p.disponible ? "disponible" : "indisponible"}${p.score ? "<br>Score : " + p.score + "/100" : ""}`
      );
      infoWindow.open(map, marker);
    });
    bounds.extend(pos);
  });

  if (data.prestataires.length > 0) {
    map.fitBounds(bounds, 60);
  }
}

window.initPickerMap = initPickerMap;
window.initRecolteMap = initRecolteMap;
