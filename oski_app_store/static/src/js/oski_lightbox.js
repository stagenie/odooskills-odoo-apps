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
