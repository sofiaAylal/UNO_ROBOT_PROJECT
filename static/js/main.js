async function startGame() { await fetch('/start_game', { method: 'POST' }); }

async function handleAction() {
    const resStatus = await fetch('/get_status');
    const data = await resStatus.json();
    if (data.game_over) return;
    
    if (data.is_init || data.waiting_discard) {
        await fetch('/record_next', { method: 'POST' });
    } else if (data.current_turn === "Humain") {
        const hRes = await fetch('/human_played', { method: 'POST' });
        const hData = await hRes.json();
        // En cas d'erreur de règle, on affiche l'alerte
        if(!hData.success) alert(hData.message);
    }
}

async function addCard() {
    const res = await fetch('/add_to_hand', { method: 'POST' });
    const data = await res.json();
    if(!data.success) alert("Aucune carte détectée par Nova !");
}

setInterval(async () => {
    try {
        const res = await fetch('/get_status');
        const data = await res.json();
        
        const overlay = document.getElementById('start-overlay');
        const mainBtn = document.getElementById('main-btn');
        const btnText = document.getElementById('btn-text');
        const addBtn = document.getElementById('add-card-btn');

        if (data.game_started) {
            overlay.classList.add('hidden');
            
            if (data.game_over) {
                btnText.innerText = "PARTIE TERMINÉE";
                mainBtn.style.backgroundColor = "#dc2626";
                mainBtn.classList.add('pointer-events-none');
                addBtn.classList.add('hidden');
            } else if (data.is_init) {
                btnText.innerText = `ENREGISTRER MAIN (${data.hand.length}/7)`;
            } else if (data.waiting_discard) {
                btnText.innerText = "ENREGISTRER TAPIS INITIAL";
            } else {
                addBtn.classList.remove('hidden');
                // Gestion dynamique de l'état du bouton principal
                if (data.current_turn === "Humain") {
                    btnText.innerText = "L'ADVERSAIRE A JOUÉ";
                    mainBtn.style.opacity = "1";
                    mainBtn.classList.remove('pointer-events-none');
                } else {
                    btnText.innerText = "ROBOT RÉFLÉCHIT...";
                    mainBtn.style.opacity = "0.5";
                    mainBtn.classList.add('pointer-events-none');
                }
            }
        }

        document.getElementById('decision-text').innerText = data.decision;
        document.getElementById('discard-card').innerText = data.last_card;
        document.getElementById('raw-data').innerText = data.raw;
        document.getElementById('scan-val').innerText = data.hand.length;

        document.getElementById('hand-list').innerHTML = data.hand.map(c => 
            `<div class="bg-slate-700 px-3 py-1 rounded-xl border border-slate-500 text-[10px] uppercase font-bold text-blue-200">${c}</div>`
        ).join('');
    } catch (e) {}
}, 800);