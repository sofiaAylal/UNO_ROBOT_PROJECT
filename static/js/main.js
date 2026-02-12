function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(tabId).classList.remove('hidden');
    if(tabId === 'tab-stats') loadStats();
}

async function loadStats() {
    const res = await fetch('/get_stats');
    const data = await res.json();
    document.getElementById('stat-total').innerText = data.total_games;
    document.getElementById('stat-winrate').innerText = data.win_rate + "%";
    document.getElementById('stat-duration').innerText = data.avg_duration + "s";
}

async function startGame() { await fetch('/start_game', { method: 'POST' }); }

async function resetGame() {
    if(confirm("Start a new round?")) {
        await fetch('/start_game', { method: 'POST' });
        document.getElementById('main-btn').classList.replace('bg-red-600', 'bg-emerald-600');
        document.getElementById('reset-btn').classList.add('hidden');
    }
}

async function declareHumanWin() {
    if(confirm("Declare your victory? (Ends match)")) {
        await fetch('/human_wins', { method: 'POST' });
    }
}

async function handleAction() {
    const resStatus = await fetch('/get_status');
    const data = await resStatus.json();
    if (data.game_over) return;
    
    if (data.is_init || data.waiting_discard) {
        await fetch('/record_next', { method: 'POST' });
    } else if (data.current_turn === "Human") {
        let chosenColor = null;
        if (data.raw.includes("Black")) {
            chosenColor = prompt("Wild Card! Choose a color (Red, Blue, Yellow, Green):");
            if (!chosenColor) return;
        }
        const hRes = await fetch('/human_played', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ color: chosenColor })
        });
        const hData = await hRes.json();
        if(!hData.success) alert(hData.message);
    }
}

async function humanDraw() { await fetch('/human_draw', { method: 'POST' }); }
async function addCard() { await fetch('/add_to_hand', { method: 'POST' }); }

setInterval(async () => {
    try {
        const res = await fetch('/get_status');
        const data = await res.json();
        
        const overlay = document.getElementById('start-overlay');
        const mainBtn = document.getElementById('main-btn');
        const btnText = document.getElementById('btn-text');
        const resetBtn = document.getElementById('reset-btn');
        const extraControls = document.getElementById('extra-controls');

        if (data.game_started) {
            overlay.classList.add('hidden');
            if (data.game_over) {
                btnText.innerText = "MATCH TERMINATED";
                mainBtn.classList.replace('bg-emerald-600', 'bg-red-600');
                mainBtn.classList.add('pointer-events-none');
                extraControls.classList.add('hidden');
                resetBtn.classList.remove('hidden');
            } else if (data.is_init || data.waiting_discard) {
                btnText.innerText = data.is_init ? `SCAN HAND (${data.hand.length}/7)` : "SCAN INITIAL DISCARD";
                resetBtn.classList.add('hidden');
            } else {
                extraControls.classList.remove('hidden');
                resetBtn.classList.add('hidden');
                if (data.current_turn === "Human") {
                    btnText.innerText = "OPPONENT HAS PLAYED";
                    mainBtn.style.opacity = "1";
                    mainBtn.classList.remove('pointer-events-none');
                } else {
                    btnText.innerText = "ROBOT IS THINKING...";
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