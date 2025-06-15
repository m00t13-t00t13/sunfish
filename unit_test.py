import sys
import os
import pytest

# Add current directory and tools to sys.path for import
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "tools")))

from sunfish import Position, Searcher
import tools.uci as uci

# Helper to create a Position from FEN using tools/uci.py
def create_position(fen):
    # uci.fen_to_pos returns a Position object
    return uci.fen_to_pos(fen)

def get_position_score(pos, depth=3):
    searcher = Searcher()
    # Minimal search to get the position score
    score = None
    for _, _, s, _ in searcher.search([pos]):
        score = s
        break
    return score

def is_king_capturable(pos):
    # If the king is gone, it's capturable (score is mate value or worse)
    return pos.score <= -60000 + 1

def test_passed_pawn_bonus():
    # White has a passed pawn on d5, black pawns can't stop it
    pos_with_passed = create_position("8/8/3P4/8/8/8/8/8 w - - 0 1")
    # White pawn on d4 but black pawn on d5 blocks it
    pos_without_passed = create_position("8/3p4/3P4/8/8/8/8/8 w - - 0 1")
    assert pos_with_passed.score > pos_without_passed.score

def test_doubled_pawn_punish():
    # Doubled white pawns on b2/b3
    pos_doubled = create_position("8/8/8/8/8/1P6/1P6/8 w - - 0 1")
    # Spread white pawns on b2 and c2
    pos_not_doubled = create_position("8/8/8/8/8/8/1P1P4/8 w - - 0 1")
    assert pos_not_doubled.score > pos_doubled.score

def test_isolated_pawn_penalty():
    # Isolated white pawn on b2
    pos_isolated = create_position("8/8/8/8/8/8/1P6/8 w - - 0 1")
    # Connected white pawns on b2 and c2
    pos_connected = create_position("8/8/8/8/8/8/1P1P4/8 w - - 0 1")
    assert pos_connected.score > pos_isolated.score

def test_king_safety_evaluation():
    # Castled king with full pawn shield
    safe_king_pos = create_position("8/8/8/8/8/8/PPP5/5K2 w - - 0 1")
    # King on open file, no pawn shield
    exposed_king_pos = create_position("8/8/8/8/8/8/8/4K3 w - - 0 1")
    assert safe_king_pos.score > exposed_king_pos.score

def test_attacking_pieces_near_king():
    # King surrounded by its pieces (safe)
    safe_king_pos = create_position("8/8/8/8/8/8/PPP5/5K2 w - - 0 1")
    # King attacked by enemy queen
    attacked_king_pos = create_position("8/8/8/8/8/8/8/4K2q w - - 0 1")
    assert safe_king_pos.score > attacked_king_pos.score

def test_king_mobility():
    # King trapped in the corner
    trapped_king = create_position("8/8/8/8/8/8/8/K7 w - - 0 1")
    # King in the center with space
    free_king = create_position("8/8/8/8/3K4/8/8/8 w - - 0 1")
    assert free_king.score > trapped_king.score

def test_legal_moves_in_check():
    # White king in check from black rook, only moves get out of check
    check_position = create_position("8/8/8/8/8/8/1r6/4K3 w - - 0 1")
    legal_moves = list(check_position.gen_moves())
    # All moves should escape check
    for move in legal_moves:
        after_move = check_position.move(move)
        assert not is_king_capturable(after_move)

def test_checkmate_detection():
    # Fool's mate: Black to move, white is checkmated
    checkmate_pos = create_position("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPP1/RNBQKBNR b KQkq - 0 1")
    # Move black queen to h4, checkmate
    checkmate_pos = checkmate_pos.move((parse("d8"), parse("h4"), ""))
    # Now white to move, but checkmated
    legal_moves = list(checkmate_pos.gen_moves())
    assert len(legal_moves) == 0

def test_search_prefers_better_positions():
    # Position 1: White up a queen
    pos1 = create_position("8/8/8/8/8/8/8/Q3K3 w - - 0 1")
    # Position 2: White up a pawn
    pos2 = create_position("8/8/8/8/8/8/8/P3K3 w - - 0 1")
    score1 = get_position_score(pos1, depth=3)
    score2 = get_position_score(pos2, depth=3)
    assert score1 > score2

# Helper for move parsing, borrowed from sunfish
def parse(c):
    fil, rank = ord(c[0]) - ord("a"), int(c[1]) - 1
    return 91 + fil - 10 * rank

if __name__ == "__main__":
    pytest.main([__file__])