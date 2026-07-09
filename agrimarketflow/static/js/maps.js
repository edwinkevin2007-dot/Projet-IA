/* maps.js — AgriMarketFlow AI
   Cartographie basée sur Leaflet + tuiles OpenStreetMap : entièrement gratuit,
   sans clé API ni compte à créer.
   1) initPickerMap()  : sélection de la position (inscription, publication de récolte)
   2) initRecolteMap() : visualisation de la récolte + prestataires suggérés (détail récolte)
*/

const OSM_TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const OSM_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/* ---------- 1) Sélecteur de position (marqueur déplaçable) ---------- */
function initPickerMap() {
  const mapEl = document.getElementById("map-picker");
  if (!mapEl || typeof L === "undefined") return;

  const latInput = document.getElementById(mapEl.dataset.latInput);
  const lonInput = document.getElementById(mapEl.dataset.lonInput);
  const startLat = parseFloat(latInput.value) || -18.8792;
  const startLon = parseFloat(lonInput.value) || 47.5079;

  const map = L.map(mapEl).setView([startLat, startLon], 11);
  L.tileLayer(OSM_TILE_URL, { attribution: OSM_ATTRIBUTION, maxZoom: 19 }).addTo(map);

  const marker = L.marker([startLat, startLon], { draggable: true }).addTo(map);

  function syncInputs(lat, lon) {
    latInput.value = lat.toFixed(6);
    lonInput.value = lon.toFixed(6);
  }

  marker.on("dragend", () => {
    const pos = marker.getLatLng();
    syncInputs(pos.lat, pos.lng);
  });

  map.on("click", (e) => {
    marker.setLatLng(e.latlng);
    syncInputs(e.latlng.lat, e.latlng.lng);
  });

  const locateBtn = document.getElementById("btn-locate-me");
  if (locateBtn && navigator.geolocation) {
    locateBtn.addEventListener("click", () => {
      navigator.geolocation.getCurrentPosition((pos) => {
        const lat = pos.coords.latitude, lon = pos.coords.longitude;
        map.setView([lat, lon], 13);
        marker.setLatLng([lat, lon]);
        syncInputs(lat, lon);
      });
    });
  }

  // Leaflet a besoin d'un recalcul de taille si le conteneur était masqué au chargement.
  setTimeout(() => map.invalidateSize(), 150);
}

/* ---------- 2) Carte récolte + prestataires suggérés ---------- */
function initRecolteMap() {
  const mapEl = document.getElementById("map-recolte");
  if (!mapEl || typeof L === "undefined") return;

  const data = JSON.parse(mapEl.dataset.payload);
  const center = [data.recolte.lat, data.recolte.lon];

  const map = L.map(mapEl).setView(center, 9);
  L.tileLayer(OSM_TILE_URL, { attribution: OSM_ATTRIBUTION, maxZoom: 19 }).addTo(map);

  const iconRecolte = L.divIcon({ className: "map-pin map-pin-recolte", iconSize: [18, 18] });
  const iconDispo = L.divIcon({ className: "map-pin map-pin-dispo", iconSize: [14, 14] });
  const iconIndispo = L.divIcon({ className: "map-pin map-pin-indispo", iconSize: [14, 14] });

  const bounds = [center];

  L.marker(center, { icon: iconRecolte }).addTo(map)
    .bindPopup(`<strong>${data.recolte.libelle}</strong><br>${data.recolte.quantite} kg`);

  data.prestataires.forEach((p) => {
    const pos = [p.lat, p.lon];
    const icon = p.disponible ? iconDispo : iconIndispo;
    L.marker(pos, { icon }).addTo(map).bindPopup(
      `<strong>${p.nom}</strong> (${p.type})<br>${p.distance_km} km · ` +
      `${p.disponible ? "disponible" : "indisponible"}` +
      (p.score ? `<br>Score : ${p.score}/100` : "")
    );
    bounds.push(pos);
  });

  if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [40, 40] });
  }
  setTimeout(() => map.invalidateSize(), 150);
}

window.initPickerMap = initPickerMap;
window.initRecolteMap = initRecolteMap;
