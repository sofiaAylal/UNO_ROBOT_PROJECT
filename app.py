import socket
import threading
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

    def handle_incoming_data(self, data):
        self.latest_sensor_raw = data.strip()

    def get_best_color(self):
        colors = [c.split(';')[0] for c in self.hand if not c.startswith("Noir")]
        return max(set(colors), key=colors.count) if colors else "Rouge"

    def robot_auto_play(self):
        try:
            old_color, old_type = self.last_card_seen.split(';')
            playable = [c for c in self.hand if c.startswith(old_color) or c.split(';')[1] == old_type or c.startswith("Noir")]
            
            if playable:
                chosen = playable[0]
                self.hand.remove(chosen)
                msg_color = ""
                if chosen.startswith("Noir"):
                    best = self.get_best_color()
                    self.last_card_seen = f"{best};{chosen.split(';')[1]}"
                    msg_color = f" ➔ COULEUR : {best.upper()}"
                else:
                    self.last_card_seen = chosen

                if "Passer" in chosen or "Inversion" in chosen:
                    return f"J'AI JOUÉ {chosen.replace(';', ' ')}{msg_color}. JE REJOUE !"
                
                self.current_turn = "Humain"
                return f"J'AI JOUÉ {chosen.replace(';', ' ')}{msg_color}. À VOUS !"
            else:
                self.current_turn = "Humain"
                return "JE N'AI RIEN... JE PIOCHE ET PASSE."
        except: return "ERREUR ANALYSE TAPIS"

    def analyze_human_move(self):
        if self.latest_sensor_raw == "---": return False, "NOVA NE VOIT RIEN"
        try:
            n_c, n_t = self.latest_sensor_raw.split(';')
            o_c, o_t = self.last_card_seen.split(';')
            if n_c == o_c or n_t == o_t or n_c == "Noir":
                self.last_card_seen = self.latest_sensor_raw
                if "Passer" in n_t or "Inversion" in n_t: return True, "SPÉCIAL ! VOUS REJOUEZ."
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
    dec = ""
    if robot.is_init_phase: dec = f"SCAN MAIN : {len(robot.hand)} / 7"
    elif robot.waiting_for_discard: dec = "SCANNEZ LE TAPIS"
    elif robot.current_turn == "Robot": dec = robot.robot_auto_play()
    else: dec = "À VOUS DE JOUER"
    return jsonify({
        "hand": robot.hand, 
        "is_init": robot.is_init_phase, 
        "waiting_discard": robot.waiting_for_discard, 
        "game_started": robot.game_started, 
        "last_card": robot.last_card_seen, 
        "raw": robot.latest_sensor_raw, 
        "current_turn": robot.current_turn, 
        "decision": dec
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

@app.route('/human_played', methods=['POST'])
def human_played():
    success, msg = robot.analyze_human_move()
    return jsonify({"success": success, "message": msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)