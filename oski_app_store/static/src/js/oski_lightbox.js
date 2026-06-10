document.addEventListener("show.bs.modal", (ev) => {
    if (ev.target.id !== "oskiLightbox") {
        return;
    }
    const src = ev.relatedTarget && ev.relatedTarget.dataset.shotSrc;
    if (src) {
        ev.target.querySelector(".oski-lightbox-img").src = src;
    }
});
