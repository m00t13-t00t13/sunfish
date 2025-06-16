import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from sunfish import Position

def fen_to_board(fen):
    """Convert FEN piece placement to a sunfish board string."""
    rows = fen.split()[0].split('/')
    board = []
    for r in rows:
        row = ''
        for c in r:
            if c.isdigit():
                row += '.' * int(c)
            else:
                row += c
        board.append(row)
    # Add padding for Sunfish 120-square board
    boardstr = "         \n" * 2
    for row in board:
        boardstr += " " + row + "\n"
    boardstr += "         \n" * 2
    return boardstr

def create_position(fen):
    board = fen_to_board(fen)
    # Default: both sides can castle, ep=kp=0, score will be recomputed
    pos = Position(board, 0, (True, True), (True, True), 0, 0)
    # Only static evaluation, no search
    return pos._replace(score=pos.evaluate())

class TestSunfishEvaluation(unittest.TestCase):
    def test_passed_pawn_bonus(self):
        pos_with_passed = create_position("8/8/3P4/8/8/8/8/8 w - - 0 1")
        pos_without_passed = create_position("8/3p4/3P4/8/8/8/8/8 w - - 0 1")
        self.assertGreater(pos_with_passed.evaluate(), pos_without_passed.evaluate())

    def test_doubled_pawn_punish(self):
        pos_doubled = create_position("8/8/8/8/8/1P6/1P6/8 w - - 0 1")
        pos_not_doubled = create_position("8/8/8/8/8/8/1P1P4/8 w - - 0 1")
        self.assertGreater(pos_not_doubled.evaluate(), pos_doubled.evaluate())

    def test_isolated_pawn_penalty(self):
        pos_isolated = create_position("8/8/8/8/8/8/1P6/8 w - - 0 1")
        pos_connected = create_position("8/8/8/8/8/8/1P1P4/8 w - - 0 1")
        self.assertGreater(pos_connected.evaluate(), pos_isolated.evaluate())

    def test_king_safety_evaluation(self):
        safe_king_pos = create_position("8/8/8/8/8/8/PPP5/5K2 w - - 0 1")
        exposed_king_pos = create_position("8/8/8/8/8/8/8/4K3 w - - 0 1")
        self.assertGreater(safe_king_pos.evaluate(), exposed_king_pos.evaluate())

    def test_attacking_pieces_near_king(self):
        safe_king_pos = create_position("8/8/8/8/8/8/PPP5/5K2 w - - 0 1")
        attacked_king_pos = create_position("8/8/8/8/8/8/8/4K2q w - - 0 1")
        self.assertGreater(safe_king_pos.evaluate(), attacked_king_pos.evaluate())

    def test_king_mobility(self):
        trapped_king = create_position("8/8/8/8/8/8/8/K7 w - - 0 1")
        free_king = create_position("8/8/8/8/3K4/8/8/8 w - - 0 1")
        self.assertGreater(free_king.evaluate(), trapped_king.evaluate())

if __name__ == "__main__":
    unittest.main()