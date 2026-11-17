// Images de la description : cliquables comme la galerie du haut. Le modal
// #oskiLightbox est toujours rendu ; l'API data de Bootstrap écoute les clics
// sur le document, les attributs posés ici suffisent. Une image déjà dans un
// lien garde son lien.
function oskiZoomDescriptionImages() {
    for (const img of document.querySelectorAll(".oski-desc img")) {
        if (img.closest("a") || img.classList.contains("oski-desc-zoom")) {
            continue;
        }
        img.classList.add("oski-desc-zoom");
        img.dataset.bsToggle = "modal";
        img.dataset.bsTarget = "#oskiLightbox";
        img.dataset.shotSrc = img.src;
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", oskiZoomDescriptionImages);
} else {
    oskiZoomDescriptionImages();
}

// Lightbox : injecte la capture cliquée dans le modal plein écran.
document.addEventListener("show.bs.modal", (ev) => {
    if (ev.target.id !== "oskiLightbox") {
        return;
    }
    const src = ev.relatedTarget && ev.relatedTarget.dataset.shotSrc;
    if (src) {
        ev.target.querySelector(".oski-lightbox-img").src = src;
    }
});

// Compteur de galerie : met à jour « N / total » à chaque diapositive.
document.addEventListener("slid.bs.carousel", (ev) => {
    if (ev.target.id !== "oskiGallery") {
        return;
    }
    const cur = ev.target.querySelector(".oski-cur");
    if (cur && typeof ev.to === "number") {
        cur.textContent = ev.to + 1;
    }
});
