// Service video pop-up shared by all service cards. Each "Watch video" button
// carries data-jto-video="<slug>"; the file is <slug>-<lang>.mp4 (and .jpg poster).
// Bump VIDEO_VERSION whenever the .mp4 files change: browsers and Cloudflare cache them.
const VIDEO_VERSION = 2;
document.addEventListener("show.bs.modal", (ev) => {
    const modal = ev.target;
    const slug = ev.relatedTarget?.dataset?.jtoVideo;
    if (!modal.matches?.(".jto-video-modal") || !slug) {
        return;
    }
    const video = modal.querySelector("video");
    const file = `${modal.dataset.base}${slug}-${modal.dataset.lang || "en"}`;
    video.poster = `${file}.jpg`;
    video.src = `${file}.mp4?v=${VIDEO_VERSION}`;
});
document.addEventListener("shown.bs.modal", (ev) => {
    const video = ev.target.matches?.(".jto-video-modal") && ev.target.querySelector("video");
    if (video) {
        video.play().catch(() => {});
    }
});
document.addEventListener("hidden.bs.modal", (ev) => {
    const video = ev.target.matches?.(".jto-video-modal") && ev.target.querySelector("video");
    if (video) {
        video.pause();
        video.removeAttribute("src");
        video.load();
    }
});
