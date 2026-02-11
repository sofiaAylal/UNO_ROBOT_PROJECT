import socket
import threading
import time
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

class UnoRobot:
    def __init__(self):
        self.hand = []
        self.game_started = False
        self.is_init_phase = False
        self.waiting_for_discard = False
        self.latest_sensor_raw = "---"
        self.last_card_seen = "---" 
        self.current_turn = None
        self.last_decision = ""
        self.lock_until = 0
        self.game_over = False

    def handle_incoming_data(self, data):
        self.latest_sensor_raw = data.strip()

    def set_decision(self, text, duration=5):
        self.last_decision = text
        self.lock_until = time.time() + duration

    def get_best_color(self):
        colors = [c.split(';')[0] for c in self.hand if not c.startswith("Noir")]
        return max(set(colors), key=colors.count) if colors else "Rouge"

    def robot_auto_play(self):
        if self.game_over: return "PARTIE TERMINÉE !"
        if time.time() < self.lock_until: return self.last_decision

        try:
            old_color, old_type = self.last_card_seen.split(';')
            playable = [c for c in self.hand if c.startswith(old_color) or c.split(';')[1] == old_type or c.startswith("Noir")]
            
            if playable:
                chosen = playable[0]
                self.hand.remove(chosen)
                
                if len(self.hand) == 0:
                    self.game_over = True
                    res = f"J'AI JOUÉ {chosen.replace(';', ' ')}. J'AI GAGNÉ ! 🏆"
                    self.set_decision(res, 999)
                    return res

                msg_extra = ""
                if chosen.startswith("Noir"):
                    best = self.get_best_color()
                    self.last_card_seen = f"{best};{chosen.split(';')[1]}"
                    msg_extra = f" ➔ COULEUR : {best.upper()} !"
                    if "Plus4" in chosen: msg_extra += " PIOCHEZ 4 !"
                else:
                    self.last_card_seen = chosen
                    if "Plus2" in chosen: msg_extra = " ➔ PIOCHEZ 2 !"

                # Si le robot joue une carte qui fait sauter le tour de l'humain
                if any(x in chosen for x in ["Passer", "Inversion", "Plus"]):
                    res = f"J'AI JOUÉ {chosen.replace(';', ' ')}{msg_extra}. JE REJOUE !"
                    self.current_turn = "Robot" 
                else:
                    self.current_turn = "Humain"
                    res = f"J'AI JOUÉ {chosen.replace(';', ' ')}{msg_extra}. À VOUS !"
                
                self.set_decision(res, 4)
                return res
            else:
                self.current_turn = "Humain"
                res = "JE N'AI RIEN... JE PIOCHE ET JE PASSE."
                self.set_decision(res, 5)
                return res
        except: return "ERREUR ANALYSE TAPIS"

    def analyze_human_move(self):
        if self.latest_sensor_raw == "---": return False, "NOVA NE VOIT RIEN"
        try:
            n_c, n_t = self.latest_sensor_raw.split(';')
            o_c, o_t = self.last_card_seen.split(';')
            
            if n_c == o_c or n_t == o_t or n_c == "Noir":
                self.last_card_seen = self.latest_sensor_raw
                
                # LOGIQUE DE SAUT DE TOUR (Duel 1vs1)
                # Si l'humain joue Inversion, Passer, +2 ou +4 -> Le robot saute son tour
                if any(x in n_t for x in ["Inversion", "Passer", "Plus2", "Plus4"]):
                    self.current_turn = "Humain" # Le tour reste à l'humain
                    
                    msg = "TOUR SAUTÉ ! "
                    if "Plus" in n_t:
                        nb = "2" if "Plus2" in n_t else "4"
                        msg += f"JE PIOCHE {nb} ET "
                    
                    self.set_decision(f"{msg}VOUS REJOUEZ.", 6)
                    return True, "Coup validé. Vous rejouez !"

                # Coup normal -> Tour au Robot
                self.current_turn = "Robot"
                return True, "COUP VALIDE"
            return False, f"NON ! JOUEZ {o_c} OU {o_t}"
        except: return False, "FORMAT CARTE INVALIDE"

robot = UnoRobot()

def tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 5000))
    s.listen(5)
    while True:
        c, _ = s.accept()
        try:
            while True:
                d = c.recv(1024).decode('utf-8')
                if not d: break
                robot.handle_incoming_data(d)
        except: pass
        finally: c.close()

threading.Thread(target=tcp_server, daemon=True).start()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    robot.__init__()
    robot.game_started = True
    robot.is_init_phase = True
    return jsonify({"status": "ok"})

@app.route('/get_status')
def get_status():
    if robot.game_over: dec = robot.last_decision
    elif robot.is_init_phase: dec = f"SCAN MAIN : {len(robot.hand)} / 7"
    elif robot.waiting_for_discard: dec = "SCANNEZ LE TAPIS"
    elif time.time() < robot.lock_until: dec = robot.last_decision
    elif robot.current_turn == "Robot": dec = robot.robot_auto_play()
    else: dec = "À VOUS DE JOUER"
    
    return jsonify({
        "hand": robot.hand, "is_init": robot.is_init_phase, 
        "waiting_discard": robot.waiting_for_discard, "game_started": robot.game_started, 
        "last_card": robot.last_card_seen, "raw": robot.latest_sensor_raw, 
        "current_turn": robot.current_turn, "decision": dec, "game_over": robot.game_over
    })

@app.route('/record_next', methods=['POST'])
def record_next():
    if robot.latest_sensor_raw == "---": return jsonify({"success": False})
    if robot.is_init_phase:
        robot.hand.append(robot.latest_sensor_raw)
        if len(robot.hand) == 7:
            robot.is_init_phase = False
            robot.waiting_for_discard = True
    elif robot.waiting_for_discard:
        robot.last_card_seen = robot.latest_sensor_raw
        robot.waiting_for_discard = False
        robot.current_turn = "Robot"
    return jsonify({"success": True})

@app.route('/add_to_hand', methods=['POST'])
def add_to_hand():
    if robot.latest_sensor_raw == "---": return jsonify({"success": False})
    robot.hand.append(robot.latest_sensor_raw)
    return jsonify({"success": True})

@app.route('/human_played', methods=['POST'])
def human_played():
    success, msg = robot.analyze_human_move()
    return jsonify({"success": success, "message": msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)