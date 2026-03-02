// v1.0.1
// Glavna JavaScript datoteka. SADA SE NALAZI U app/scripts/

$(document).ready(function() {
    // Inicijalizacija Bootstrap Tooltipa (važno za IP Mapu)
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    console.log("IPAM UI Engine Initialized from app/scripts/");
});