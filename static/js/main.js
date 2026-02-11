async function startGame() { 
    await fetch('/start_game', { method: 'POST' }); 
}

async function handleAction() {
    const resStatus = await fetch('/get_status');
    const data = await resStatus.json();

    if (data.is_init || data.waiting_discard) {
        const resRecord = await fetch('/record_next', { method: 'POST' });
        const resData = await resRecord.json();
        if (!resData.success) alert("Nova ne détecte rien. Vérifiez le flux RAW.");
    } else if (data.current_turn === "Humain") {
        const resPlay = await fetch('/human_played', { method: 'POST' });
        const resData = await resPlay.json();
        if (!resData.success) alert(resData.message);
    }
}

setInterval(async () => {
    try {
        const res = await fetch('/get_status');
        const data = await res.json();
        
        const overlay = document.getElementById('start-overlay');
        const mainBtn = document.getElementById('main-btn');
        const btnText = document.getElementById('btn-text');

        if (data.game_started) {
            overlay.classList.add('hidden');
            if (data.is_init) {
                btnText.innerText = `ENREGISTRER MAIN (${data.hand.length}/7)`;
                mainBtn.classList.remove('opacity-50', 'pointer-events-none');
            } else if (data.waiting_discard) {
                btnText.innerText = "ENREGISTRER TAPIS INITIAL";
                mainBtn.classList.remove('opacity-50', 'pointer-events-none');
            } else if (data.current_turn === "Humain") {
                btnText.innerText = "L'ADVERSAIRE A JOUÉ";
                mainBtn.classList.remove('opacity-50', 'pointer-events-none');
            } else {
                btnText.innerText = "ROBOT RÉFLÉCHIT...";
                mainBtn.classList.add('opacity-50', 'pointer-events-none');
            }
        } else {
            overlay.classList.remove('hidden');
        }

        document.getElementById('decision-text').innerText = data.decision;
        document.getElementById('discard-card').innerText = data.last_card;
        document.getElementById('raw-data').innerText = data.raw;
        document.getElementById('scan-val').innerText = data.hand.length;

        document.getElementById('hand-list').innerHTML = data.hand.map(c => 
            `<div class="bg-slate-700 px-3 py-1 rounded-xl border border-slate-500 text-[10px] uppercase font-bold text-blue-200 shadow-sm">${c}</div>`
        ).join('');
    } catch (e) { }
}, 800);