import socket
import threading
import time
import json
import os
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
        self.skip_type_check = False
        self.start_time = 0
        self.cards_played = 0

    def handle_incoming_data(self, data):
        self.latest_sensor_raw = data.strip()

    def set_decision(self, text, duration=5):
        self.last_decision = text
        self.lock_until = time.time() + duration

    def save_stats(self, winner):
        stats_file = 'stats.json'
        duration = int(time.time() - self.start_time) if self.start_time > 0 else 0
        new_entry = {
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "winner": winner,
            "duration": duration,
            "cards_played": self.cards_played
        }
        data = []
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    data = json.load(f)
            except: data = []
        data.append(new_entry)
        with open(stats_file, 'w') as f:
            json.dump(data, f)

    def get_best_color(self):
        colors = [c.split(';')[0] for c in self.hand if not c.startswith("Black")]
        return max(set(colors), key=colors.count) if colors else "Red"

    def robot_auto_play(self):
        if self.game_over: return self.last_decision
        if time.time() < self.lock_until: return self.last_decision

        try:
            old_color, old_type = self.last_card_seen.split(';')
            
            if self.skip_type_check:
                playable = [c for c in self.hand if c.startswith(old_color) or c.startswith("Black")]
                self.skip_type_check = False
            else:
                playable = [c for c in self.hand if c.startswith(old_color) or c.split(';')[1] == old_type or c.startswith("Black")]
            
            if playable:
                chosen = playable[0]
                self.hand.remove(chosen)
                self.cards_played += 1
                
                if len(self.hand) == 0:
                    self.game_over = True
                    self.save_stats("Robot")
                    res = f"I PLAYED {chosen.replace(';', ' ')}. I WIN! 🏆"
                    self.set_decision(res, 999)
                    return res

                msg_extra = ""
                if chosen.startswith("Black"):
                    best = self.get_best_color()
                    self.last_card_seen = f"{best};{chosen.split(';')[1]}"
                    msg_extra = f" ➔ NEW COLOR: {best.upper()}!"
                    if "Plus4" in chosen: msg_extra += " DRAW 4!"
                else:
                    self.last_card_seen = chosen
                    if "Plus2" in chosen: msg_extra = " ➔ DRAW 2!"

                if any(x in chosen for x in ["Skip", "Reverse", "Plus"]):
                    res = f"I PLAYED {chosen.replace(';', ' ')}{msg_extra}. I GO AGAIN!"
                    self.current_turn = "Human"
                else:
                    self.current_turn = "Human"
                    res = f"I PLAYED {chosen.replace(';', ' ')}{msg_extra}. YOUR TURN!"
                
                self.set_decision(res, 4)
                return res
            else:
                self.current_turn = "Human"
                res = "I HAVE NOTHING... DRAWING AND PASSING."
                self.set_decision(res, 5)
                return res
        except: return "ERROR SYNCING TABLE"

    def analyze_human_move(self, chosen_color=None):
        if self.latest_sensor_raw == "---": return False, "NOVA DETECTS NOTHING"
        try:
            n_c, n_t = self.latest_sensor_raw.split(';')
            
            if n_c == "Black" and chosen_color:
                self.last_card_seen = f"{chosen_color};{n_t}"
            else:
                self.last_card_seen = self.latest_sensor_raw
            
            if any(x in n_t for x in ["Reverse", "Skip"]):
                self.current_turn = "Human"
                self.set_decision("TURN SKIPPED! YOU GO AGAIN.", 5)
                return True, "You go again."
            
            if "Plus" in n_t:
                nb = "2" if "Plus2" in n_t else "4"
                self.current_turn = "Human"
                self.set_decision(f"OUCH! I DRAW {nb} AND PASS. YOUR TURN!", 6)
                return True, "Attack received."

            self.current_turn = "Robot"
            return True, "VALID MOVE"
        except: return False, "INVALID FORMAT"

robot = UnoRobot()

@app.route('/')
def index(): return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    robot.hand = []
    robot.game_started = True
    robot.is_init_phase = True
    robot.waiting_for_discard = False
    robot.game_over = False
    robot.current_turn = None
    robot.last_decision = ""
    robot.lock_until = 0
    robot.cards_played = 0
    robot.start_time = time.time()
    return jsonify({"status": "ok"})

@app.route('/human_wins', methods=['POST'])
def human_wins():
    if not robot.game_over:
        robot.game_over = True
        robot.save_stats("Human")
        robot.set_decision("CONGRATS! YOU WIN! 🏆", 999)
    return jsonify({"status": "ok"})

@app.route('/get_status')
def get_status():
    if robot.game_over: dec = robot.last_decision
    elif robot.is_init_phase: dec = f"SCAN HAND: {len(robot.hand)} / 7"
    elif robot.waiting_for_discard: dec = "SCAN INITIAL DISCARD"
    elif time.time() < robot.lock_until: dec = robot.last_decision
    elif robot.current_turn == "Robot": dec = robot.robot_auto_play()
    else: dec = "YOUR TURN"
    
    return jsonify({
        "hand": robot.hand, "is_init": robot.is_init_phase, 
        "waiting_discard": robot.waiting_for_discard, "game_started": robot.game_started, 
        "last_card": robot.last_card_seen, "raw": robot.latest_sensor_raw, 
        "current_turn": robot.current_turn, "decision": dec, "game_over": robot.game_over
    })

@app.route('/human_played', methods=['POST'])
def human_played():
    color = request.json.get('color')
    success, msg = robot.analyze_human_move(chosen_color=color)
    return jsonify({"success": success, "message": msg})

@app.route('/human_draw', methods=['POST'])
def human_draw():
    robot.skip_type_check = True
    robot.current_turn = "Robot"
    robot.set_decision("YOU DREW... MY TURN!", 3)
    return jsonify({"success": True})

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

@app.route('/get_stats')
def get_stats():
    if not os.path.exists('stats.json'): return jsonify({"total_games": 0, "win_rate": 0, "avg_duration": 0})
    with open('stats.json', 'r') as f:
        data = json.load(f)
    total = len(data)
    robot_wins = len([g for g in data if g['winner'] == 'Robot'])
    avg_dur = sum(g['duration'] for g in data) / total if total > 0 else 0
    return jsonify({"total_games": total, "win_rate": round((robot_wins/total)*100, 1) if total > 0 else 0, "avg_duration": round(avg_dur, 1)})

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)