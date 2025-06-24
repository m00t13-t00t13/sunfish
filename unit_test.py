import unittest
import subprocess
import sys
import os
import tempfile
import time
import re

ENGINE_PATH = os.path.abspath("./sunfish.py")

def get_eval_from_engine(fen, engine_path=ENGINE_PATH):
    """Starts sunfish engine as UCI, sets position to fen, gets evaluation."""
    # Start the engine as a subprocess
    proc = subprocess.Popen(
        [sys.executable, engine_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
    )

    def send(cmd):
        proc.stdin.write(cmd + "\n")
        proc.stdin.flush()

    def read_until(keyword):
        lines = []
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            lines.append(line)
            if keyword in line:
                break
        return lines

    # Start UCI protocol
    send("uci")
    read_until("uciok")
    send("isready")
    read_until("readyok")

    send(f"position fen {fen}")
    send("go depth 1")
    score = None
    # Wait for info line with score cp
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        if "score cp" in line:
            # Example: info depth 1 score cp 20 pv ...
            m = re.search(r"score cp (-?\d+)", line)
            if m:
                score = int(m.group(1))
        if line.startswith("bestmove"):
            break
    send("quit")
    proc.stdin.close()
    proc.stdout.close()
    proc.stderr.close()
    proc.wait(timeout=5)
    assert score is not None, f"Failed to get score from engine for FEN: {fen}"
    return score

class TestSunfishEvalUCI(unittest.TestCase):
    def test_passed_pawn_bonus(self):
        fen_passed = "8/8/3P4/8/8/8/8/8 w - - 0 1"
        fen_blocked = "8/3p4/3P4/8/8/8/8/8 w - - 0 1"
        eval_passed = get_eval_from_engine(fen_passed)
        eval_blocked = get_eval_from_engine(fen_blocked)
        self.assertGreater(eval_passed, eval_blocked)

    def test_doubled_pawn_punish(self):
        fen_doubled = "8/8/8/8/8/1P6/1P6/8 w - - 0 1"
        fen_not_doubled = "8/8/8/8/8/8/1P1P4/8 w - - 0 1"
        eval_doubled = get_eval_from_engine(fen_doubled)
        eval_not_doubled = get_eval_from_engine(fen_not_doubled)
        self.assertGreater(eval_not_doubled, eval_doubled)

    def test_isolated_pawn_penalty(self):
        fen_isolated = "8/8/8/8/8/8/1P6/8 w - - 0 1"
        fen_connected = "8/8/8/8/8/8/1P1P4/8 w - - 0 1"
        eval_isolated = get_eval_from_engine(fen_isolated)
        eval_connected = get_eval_from_engine(fen_connected)
        self.assertGreater(eval_connected, eval_isolated)

    def test_king_safety_evaluation(self):
        fen_safe = "8/8/8/8/8/8/PPP5/5K2 w - - 0 1"
        fen_exposed = "8/8/8/8/8/8/8/4K3 w - - 0 1"
        eval_safe = get_eval_from_engine(fen_safe)
        eval_exposed = get_eval_from_engine(fen_exposed)
        self.assertGreater(eval_safe, eval_exposed)

    def test_attacking_pieces_near_king(self):
        fen_safe = "8/8/8/8/8/8/PPP5/5K2 w - - 0 1"
        fen_attacked = "8/8/8/8/8/8/8/4K2q w - - 0 1"
        eval_safe = get_eval_from_engine(fen_safe)
        eval_attacked = get_eval_from_engine(fen_attacked)
        self.assertGreater(eval_safe, eval_attacked)

    def test_king_mobility(self):
        fen_trapped = "8/8/8/8/8/8/8/K7 w - - 0 1"
        fen_free = "8/8/8/8/3K4/8/8/8 w - - 0 1"
        eval_trapped = get_eval_from_engine(fen_trapped)
        eval_free = get_eval_from_engine(fen_free)
        self.assertGreater(eval_free, eval_trapped)

    def test_discovered_check(self):
        # Position: White to move, bishop can move to reveal rook check on e-file.
        # 8 . . . . k . . .
        # 7 . . . . p . . .
        # 6 . . . . . . . .
        # 5 . . . . . . . .
        # 4 . . . . . . . .
        # 3 . . B . . . . .
        # 2 . . . . . . . .
        # 1 . . . . R . . .
        # FEN: 4k3/4p3/8/8/8/2B5/8/4R3 w - - 0 1
        fen = "4k3/4p3/8/8/8/2B5/8/4R3 w - - 0 1"
        # The best move should be moving the bishop on c3 (from c3 to any square not blocking e1-e8), giving discovered check.
        # We'll check that the engine's best move is a legal bishop move that results in check.

        # Start engine as before
        proc = subprocess.Popen(
            [sys.executable, ENGINE_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
        )

        def send(cmd):
            proc.stdin.write(cmd + "\n")
            proc.stdin.flush()

        def read_until(keyword):
            lines = []
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                lines.append(line)
                if keyword in line:
                    break
            return lines

        # UCI handshake
        send("uci")
        read_until("uciok")
        send("isready")
        read_until("readyok")
        send(f"position fen {fen}")
        send("go depth 1")

        bestmove = None
        pvline = None
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            if line.startswith("info") and "pv" in line:
                pvline = line
            if line.startswith("bestmove"):
                m = re.search(r"bestmove (\w+)", line)
                if m:
                    bestmove = m.group(1)
                break

        send("quit")
        proc.stdin.close()
        proc.stdout.close()
        proc.stderr.close()
        proc.wait(timeout=5)

        # Acceptable discovered check bishop moves: c3-b2, c3-d2, c3-d4, c3-b4, c3-e5, c3-a5, c3-f6, c3-g7, c3-h8
        discovered_moves = {"c3b2", "c3d2", "c3d4", "c3b4", "c3e5", "c3a5", "c3f6", "c3g7", "c3h8"}

        # The bestmove should be one of these
        self.assertIn(bestmove[:4], discovered_moves, f"Engine bestmove {bestmove} is not a discovered check bishop move! PV: {pvline}")

if __name__ == "__main__":
    unittest.main()