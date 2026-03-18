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

/* v1.1.6 - Turbo Scan Logic */
function startTurboScan(subnetId) {
    // Dohvaćanje elemenata - ID-ovi moraju biti identični onima u HTML-u!
    const btn = document.getElementById('btnStartScan');
    const btnText = document.getElementById('scanBtnText');
    const consoleDiv = document.getElementById('scanTerminal');
    const terminalCard = document.getElementById('terminalCard');

    if (!btn || !btnText) {
        console.error("Greška: Gumb nije pronađen u DOM-u!");
        return;
    }

    const originalHtml = btn.innerHTML;
    
    // Priprema UI-a
    if (terminalCard) terminalCard.style.display = 'block';
    btn.disabled = true;
    btnText.innerText = 'Skeniram...';

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/discovery/${subnetId}`);

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.type === 'result') {
            const boxId = `ip-${data.ip.replace(/\./g, '-')}`;
            const box = document.getElementById(boxId);
            if (box) {
                box.classList.remove('ip-free', 'ip-used');
                box.classList.add(data.is_online ? 'ip-used' : 'ip-free');
                box.classList.add('box-scanning');
                setTimeout(() => box.classList.remove('box-scanning'), 600);
            }
        }

        if (data.type === 'finish') {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            Swal.fire({ icon: 'success', title: 'Gotovo!', text: 'Mreža je osvježena.', timer: 3000 });
        }
    };

    socket.onerror = function(err) {
        console.error("WS Greška:", err);
        btn.disabled = false;
        btn.innerHTML = originalHtml;
        alert("Veza sa serverom nije uspjela. Provjeri Apache WebSocket postavke.");
    };
}