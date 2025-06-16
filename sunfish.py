#!/usr/bin/env pypy3
from __future__ import print_function

import time, math
from itertools import count
from collections import namedtuple, defaultdict

# If we could rely on the env -S argument, we could just use "pypy3 -u"
# as the shebang to unbuffer stdout. But alas we have to do this instead:
#from functools import partial
#print = partial(print, flush=True)

version = "sunfish 2023"

###############################################################################
# Piece-Square tables. Tune these to change sunfish's behaviour
###############################################################################

# With xz compression this whole section takes 652 bytes.
# That's pretty good given we have 64*6 = 384 values.
# Though probably we could do better...
# For one thing, they could easily all fit into int8.
piece = {"P": 100, "N": 280, "B": 320, "R": 479, "Q": 929, "K": 60000}
pst = {
    'P': (   0,   0,   0,   0,   0,   0,   0,   0,
            78,  83,  86,  73, 102,  82,  85,  90,
             7,  29,  21,  44,  40,  31,  44,   7,
           -17,  16,  -2,  15,  14,   0,  15, -13,
           -26,   3,  10,   9,   6,   1,   0, -23,
           -22,   9,   5, -11, -10,  -2,   3, -19,
           -31,   8,  -7, -37, -36, -14,   3, -31,
             0,   0,   0,   0,   0,   0,   0,   0),
    'N': ( -66, -53, -75, -75, -10, -55, -58, -70,
            -3,  -6, 100, -36,   4,  62,  -4, -14,
            10,  67,   1,  74,  73,  27,  62,  -2,
            24,  24,  45,  37,  33,  41,  25,  17,
            -1,   5,  31,  21,  22,  35,   2,   0,
           -18,  10,  13,  22,  18,  15,  11, -14,
           -23, -15,   2,   0,   2,   0, -23, -20,
           -74, -23, -26, -24, -19, -35, -22, -69),
    'B': ( -59, -78, -82, -76, -23,-107, -37, -50,
           -11,  20,  35, -42, -39,  31,   2, -22,
            -9,  39, -32,  41,  52, -10,  28, -14,
            25,  17,  20,  34,  26,  25,  15,  10,
            13,  10,  17,  23,  17,  16,   0,   7,
            14,  25,  24,  15,   8,  25,  20,  15,
            19,  20,  11,   6,   7,   6,  20,  16,
            -7,   2, -15, -12, -14, -15, -10, -10),
    'R': (  35,  29,  33,   4,  37,  33,  56,  50,
            55,  29,  56,  67,  55,  62,  34,  60,
            19,  35,  28,  33,  45,  27,  25,  15,
             0,   5,  16,  13,  18,  -4,  -9,  -6,
           -28, -35, -16, -21, -13, -29, -46, -30,
           -42, -28, -42, -25, -25, -35, -26, -46,
           -53, -38, -31, -26, -29, -43, -44, -53,
           -30, -24, -18,   5,  -2, -18, -31, -32),
    'Q': (   6,   1,  -8,-104,  69,  24,  88,  26,
            14,  32,  60, -10,  20,  76,  57,  24,
            -2,  43,  32,  60,  72,  63,  43,   2,
             1, -16,  22,  17,  25,  20, -13,  -6,
           -14, -15,  -2,  -5,  -1, -10, -20, -22,
           -30,  -6, -13, -11, -16, -11, -16, -27,
           -36, -18,   0, -19, -15, -15, -21, -38,
           -39, -30, -31, -13, -31, -36, -34, -42),
    'K': (   4,  54,  47, -99, -99,  60,  83, -62,
           -32,  10,  55,  56,  56,  55,  10,   3,
           -62,  12, -57,  44, -67,  28,  37, -31,
           -55,  50,  11,  -4, -19,  13,   0, -49,
           -55, -43, -52, -28, -51, -47,  -8, -50,
           -47, -42, -43, -79, -64, -32, -29, -32,
            -4,   3, -14, -50, -57, -18,  13,   4,
            17,  30,  -3, -14,   6,  -1,  40,  18),
}
# Pad tables and join piece and pst dictionaries
for k, table in pst.items():
    padrow = lambda row: (0,) + tuple(x + piece[k] for x in row) + (0,)
    pst[k] = sum((padrow(table[i * 8 : i * 8 + 8]) for i in range(8)), ())
    pst[k] = (0,) * 20 + pst[k] + (0,) * 20

###############################################################################
# Global constants
###############################################################################

# Our board is represented as a 120 character string. The padding allows for
# fast detection of moves that don't stay within the board.
A1, H1, A8, H8 = 91, 98, 21, 28
initial = (
    "         \n"  #   0 -  9
    "         \n"  #  10 - 19
    " rnbqkbnr\n"  #  20 - 29
    " pppppppp\n"  #  30 - 39
    " ........\n"  #  40 - 49
    " ........\n"  #  50 - 59
    " ........\n"  #  60 - 69
    " ........\n"  #  70 - 79
    " PPPPPPPP\n"  #  80 - 89
    " RNBQKBNR\n"  #  90 - 99
    "         \n"  # 100 -109
    "         \n"  # 110 -119
)

# Lists of possible moves for each piece type.
N, E, S, W = -10, 1, 10, -1
directions = {
    "P": (N, N+N, N+W, N+E),
    "N": (N+N+E, E+N+E, E+S+E, S+S+E, S+S+W, W+S+W, W+N+W, N+N+W),
    "B": (N+E, S+E, S+W, N+W),
    "R": (N, E, S, W),
    "Q": (N, E, S, W, N+E, S+E, S+W, N+W),
    "K": (N, E, S, W, N+E, S+E, S+W, N+W)
}

# Mate value must be greater than 8*queen + 2*(rook+knight+bishop)
# King value is set to twice this value such that if the opponent is
# 8 queens up, but we got the king, we still exceed MATE_VALUE.
# When a MATE is detected, we'll set the score to MATE_UPPER - plies to get there
# E.g. Mate in 3 will be MATE_UPPER - 6
MATE_LOWER = piece["K"] - 10 * piece["Q"]
MATE_UPPER = piece["K"] + 10 * piece["Q"]

# Constants for tuning search
QS = 40
QS_A = 140
EVAL_ROUGHNESS = 15

# minifier-hide start
opt_ranges = dict(
    QS = (0, 300),
    QS_A = (0, 300),
    EVAL_ROUGHNESS = (0, 50),
)
# minifier-hide end


###############################################################################
# Chess logic
###############################################################################


Move = namedtuple("Move", "i j prom")


class Position(namedtuple("Position", "board score wc bc ep kp")):
    """A state of a chess game
    board -- a 120 char representation of the board
    score -- the board evaluation
    wc -- the castling rights, [west/queen side, east/king side]
    bc -- the opponent castling rights, [west/king side, east/queen side]
    ep - the en passant square
    kp - the king passant square
    """

    def gen_moves(self):
        # For each of our pieces, iterate through each possible 'ray' of moves,
        # as defined in the 'directions' map. The rays are broken e.g. by
        # captures or immediately in case of pieces such as knights.
        for i, p in enumerate(self.board):
            if not p.isupper():
                continue
            for d in directions[p]:
                for j in count(i + d, d):
                    q = self.board[j]
                    # Stay inside the board, and off friendly pieces
                    if q.isspace() or q.isupper():
                        break
                    # Pawn move, double move and capture
                    if p == "P":
                        if d in (N, N + N) and q != ".": break
                        if d == N + N and (i < A1 + N or self.board[i + N] != "."): break
                        if (
                            d in (N + W, N + E)
                            and q == "."
                            and j not in (self.ep, self.kp, self.kp - 1, self.kp + 1)
                        ):
                            break
                        # If we move to the last row, we can be anything
                        if A8 <= j <= H8:
                            for prom in "NBRQ":
                                yield Move(i, j, prom)
                            break
                    # Move it
                    yield Move(i, j, "")
                    # Stop crawlers from sliding, and sliding after captures
                    if p in "PNK" or q.islower():
                        break
                    # Castling, by sliding the rook next to the king
                    if i == A1 and self.board[j + E] == "K" and self.wc[0]:
                        yield Move(j + E, j + W, "")
                    if i == H1 and self.board[j + W] == "K" and self.wc[1]:
                        yield Move(j + W, j + E, "")

    def rotate(self, nullmove=False):
        """Rotates the board, preserving enpassant, unless nullmove"""
        return Position(
            self.board[::-1].swapcase(), -self.score, self.bc, self.wc,
            119 - self.ep if self.ep and not nullmove else 0,
            119 - self.kp if self.kp and not nullmove else 0,
        )

    def move(self, move):
        i, j, prom = move
        p, q = self.board[i], self.board[j]
        put = lambda board, i, p: board[:i] + p + board[i + 1 :]
        # Copy variables and reset ep and kp
        board = self.board
        wc, bc, ep, kp = self.wc, self.bc, 0, 0
        # Instead of incremental score, we recompute. This is now needed for rich evaluation.
        #score = self.score + self.value(move)
        # Actual move
        board = put(board, j, board[i])
        board = put(board, i, ".")
        # Castling rights, we move the rook or capture the opponent's
        if i == A1: wc = (False, wc[1])
        if i == H1: wc = (wc[0], False)
        if j == A8: bc = (bc[0], False)
        if j == H8: bc = (False, bc[1])
        # Castling
        if p == "K":
            wc = (False, False)
            if abs(j - i) == 2:
                kp = (i + j) // 2
                board = put(board, A1 if j < i else H1, ".")
                board = put(board, kp, "R")
        # Pawn promotion, double move and en passant capture
        if p == "P":
            if A8 <= j <= H8:
                board = put(board, j, prom)
            if j - i == 2 * N:
                ep = i + N
            if j == self.ep:
                board = put(board, j + S, ".")
        # Instead of incrementally updating score, do a full evaluation.
        newpos = Position(board, 0, wc, bc, ep, kp).rotate()
        score = newpos.evaluate()
        return Position(newpos.board, score, newpos.wc, newpos.bc, newpos.ep, newpos.kp)

    def value(self, move):
        i, j, prom = move
        p, q = self.board[i], self.board[j]
        # Actual move
        score = pst[p][j] - pst[p][i]
        # Capture
        if q.islower():
            score += pst[q.upper()][119 - j]
        # Castling check detection
        if abs(j - self.kp) < 2:
            score += pst["K"][119 - j]
        # Castling
        if p == "K" and abs(i - j) == 2:
            score += pst["R"][(i + j) // 2]
            score -= pst["R"][A1 if j < i else H1]
        # Special pawn stuff
        if p == "P":
            if A8 <= j <= H8:
                score += pst[prom][j] - pst["P"][j]
            if j == self.ep:
                score += pst["P"][119 - (j + S)]
        return score

    def evaluate(self):
        """Rich evaluation: material, PST, pawn structure, king safety, mobility."""
        score = 0
        board = self.board
        # Material and piece-square table
        for i, p in enumerate(board):
            if p.isupper():
                score += piece.get(p, 0) + pst.get(p, [0]*120)[i]
            elif p.islower():
                score -= piece.get(p.upper(), 0) + pst.get(p.upper(), [0]*120)[119 - i]

        # Pawn structure
        score += self.eval_pawn_structure()

        # King safety
        score += self.eval_king_safety()

        # Piece mobility
        score += self.eval_mobility()

        return score

    def eval_pawn_structure(self):
        """Evaluate pawn structure for both sides."""
        score = 0
        white_pawns = [i for i, p in enumerate(self.board) if p == "P"]
        black_pawns = [i for i, p in enumerate(self.board) if p == "p"]
        # Doubled pawns penalty
        score -= 15 * self.count_doubled_pawns(white_pawns, is_white=True)
        score += 15 * self.count_doubled_pawns(black_pawns, is_white=False)
        # Isolated pawns penalty
        score -= 20 * self.count_isolated_pawns(white_pawns, is_white=True)
        score += 20 * self.count_isolated_pawns(black_pawns, is_white=False)
        # Passed pawn bonus
        score += 25 * self.count_passed_pawns(white_pawns, is_white=True)
        score -= 25 * self.count_passed_pawns(black_pawns, is_white=False)
        return score

    def count_doubled_pawns(self, pawn_sqs, is_white):
        """Count doubled pawns (pawns on same file)"""
        files = [((i - A1) % 8) for i in pawn_sqs if A1 <= i <= H1 + 70]
        return sum(max(files.count(f) - 1, 0) for f in set(files))

    def count_isolated_pawns(self, pawn_sqs, is_white):
        """Count isolated pawns (no friendly pawn on adjacent files)"""
        files = [((i - A1) % 8) for i in pawn_sqs if A1 <= i <= H1 + 70]
        isolated = 0
        for f in set(files):
            has_left = (f - 1) in files
            has_right = (f + 1) in files
            if not has_left and not has_right:
                isolated += files.count(f)
        return isolated

    def count_passed_pawns(self, pawn_sqs, is_white):
        """Count passed pawns (no opposing pawn on same or adjacent file ahead)"""
        count = 0
        for i in pawn_sqs:
            file = (i - A1) % 8
            rank = (i - A1) // 10
            passed = True
            for df in (-1, 0, 1):
                f2 = file + df
                if not (0 <= f2 <= 7):
                    continue
                if is_white:
                    for r in range(rank - 1, -1, -1):
                        sq = A1 + f2 + (-10) * r
                        if 0 <= sq < len(self.board):
                            if self.board[sq] == "p":
                                passed = False
                                break
                    if not passed:
                        break
                else:
                    for r in range(rank + 1, 8):
                        sq = A1 + f2 + (-10) * r
                        if 0 <= sq < len(self.board):
                            if self.board[sq] == "P":
                                passed = False
                                break
                    if not passed:
                        break
            if passed:
                count += 1
        return count

    def eval_king_safety(self):
        """Evaluate king safety for both sides."""
        score = 0
        w_king = [i for i, p in enumerate(self.board) if p == "K"]
        b_king = [i for i, p in enumerate(self.board) if p == "k"]
        if w_king:
            score += self.king_safety_at(w_king[0], is_white=True)
        if b_king:
            score -= self.king_safety_at(b_king[0], is_white=False)
        return score

    def king_safety_at(self, king_sq, is_white):
        """Penalize king exposure, reward pawn shield."""
        penalty = 0
        # Pawn shield squares
        pawn_dir = -10 if is_white else 10
        for offset in (-1, 0, 1):
            front_sq = king_sq + pawn_dir + offset
            if 0 <= front_sq < len(self.board):
                if self.board[front_sq] == ("P" if is_white else "p"):
                    penalty -= 15
                else:
                    penalty += 15
        # Check for open files near king
        for offset in (-2, -1, 1, 2):
            sq = king_sq + offset
            if 0 <= sq < len(self.board) and self.board[sq] == ".":
                penalty += 4
        # Bonus/penalty for being castled (crude)
        rank = (king_sq - A1) // 10
        if (is_white and rank == 7) or (not is_white and rank == 0):
            penalty -= 5
        return -penalty

    def eval_mobility(self):
        """Evaluate mobility for both sides."""
        my_mob = self.mobility(is_white=True)
        opp_mob = self.mobility(is_white=False)
        return 2 * (my_mob - opp_mob)

    def mobility(self, is_white):
        """Count legal moves for minor/major pieces."""
        color = str.isupper if is_white else str.islower
        mob = 0
        for i, p in enumerate(self.board):
            if not color(p):
                continue
            if p.upper() in "NBRQ":
                moves = 0
                for d in directions[p.upper()]:
                    for j in count(i + d, d):
                        q = self.board[j]
                        if q.isspace() or color(q):
                            break
                        moves += 1
                        if p.upper() in "N" or q != ".":
                            break
                mob += moves
        return mob

    def is_in_check(self, is_white):
        """Returns True if current player's king is in check."""
        king = "K" if is_white else "k"
        ksq = next((i for i, p in enumerate(self.board) if p == king), None)
        if ksq is None:
            return False
        # Check for attacks from all types of pieces
        opp_color = str.islower if is_white else str.isupper
        for d in directions["Q"]:
            for j in count(ksq + d, d):
                q = self.board[j]
                if q.isspace():
                    break
                if opp_color(q):
                    if (q.upper() == "Q" or
                        (q.upper() == "R" and d in directions["R"]) or
                        (q.upper() == "B" and d in directions["B"])):
                        return True
                    break
                if q != ".":
                    break
        # Knights
        for d in directions["N"]:
            sq = ksq + d
            if opp_color(self.board[sq]) and self.board[sq].upper() == "N":
                return True
        # Pawns
        pawn_dir = -10 if is_white else 10
        for df in (-1, 1):
            sq = ksq + pawn_dir + df
            if self.board[sq] == ("p" if is_white else "P"):
                return True
        # King
        for d in directions["K"]:
            sq = ksq + d
            if opp_color(self.board[sq]) and self.board[sq].upper() == "K":
                return True
        return False

    def is_checkmate(self, is_white):
        """Returns True if current player is checkmated."""
        if not self.is_in_check(is_white):
            return False
        # No legal moves for current player?
        for move in self.gen_moves():
            pos2 = self.move(move)
            if not pos2.is_in_check(is_white):
                return False
        return True

    def is_stalemate(self, is_white):
        """Returns True if stalemated (not in check, no legal moves)."""
        if self.is_in_check(is_white):
            return False
        for move in self.gen_moves():
            pos2 = self.move(move)
            if not pos2.is_in_check(is_white):
                return False
        return True


###############################################################################
# Search logic
###############################################################################

# lower <= s(pos) <= upper
Entry = namedtuple("Entry", "lower upper")


class Searcher:
    def __init__(self):
        self.tp_score = {}
        self.tp_move = {}
        self.history = set()
        self.nodes = 0

    def bound(self, pos, gamma, depth, can_null=True):
        """ Let s* be the "true" score of the sub-tree we are searching.
            The method returns r, where
            if gamma >  s* then s* <= r < gamma  (A better upper bound)
            if gamma <= s* then gamma <= r <= s* (A better lower bound) """
        self.nodes += 1

        # Depth <= 0 is QSearch. Here any position is searched as deeply as is needed for
        # calmness, and from this point on there is no difference in behaviour depending on
        # depth, so so there is no reason to keep different depths in the transposition table.
        depth = max(depth, 0)

        # Sunfish is a king-capture engine, so we should always check if we
        # still have a king. Notice since this is the only termination check,
        # the remaining code has to be comfortable with being mated, stalemated
        # or able to capture the opponent king.
        if pos.score <= -MATE_LOWER:
            return -MATE_UPPER

        # Look in the table if we have already searched this position before.
        # We also need to be sure, that the stored search was over the same
        # nodes as the current search.
        entry = self.tp_score.get((pos, depth, can_null), Entry(-MATE_UPPER, MATE_UPPER))
        if entry.lower >= gamma: return entry.lower
        if entry.upper < gamma: return entry.upper

        # Let's not repeat positions. We don't chat
        # - at the root (can_null=False) since it is in history, but not a draw.
        # - at depth=0, since it would be expensive and break "futility pruning".
        if can_null and depth > 0 and pos in self.history:
            return 0

        # Enhanced checkmate/stalemate detection:
        # If no legal moves, check if in check (checkmate) or not (stalemate)
        legal_moves = list(pos.gen_moves())
        is_white = True  # Always white to move after rotation
        if not legal_moves:
            if pos.is_in_check(is_white):
                return -MATE_UPPER + (100 - depth)
            else:
                return 0  # Stalemate

        # Generator of moves to search in order.
        def moves():
            if depth > 2 and can_null and abs(pos.score) < 500:
                yield None, -self.bound(pos.rotate(nullmove=True), 1 - gamma, depth - 3)

            if depth == 0:
                yield None, pos.score

            killer = self.tp_move.get(pos)
            if not killer and depth > 2:
                self.bound(pos, gamma, depth - 3, can_null=False)
                killer = self.tp_move.get(pos)

            val_lower = QS - depth * QS_A

            if killer and pos.value(killer) >= val_lower:
                yield killer, -self.bound(pos.move(killer), 1 - gamma, depth - 1)

            for val, move in sorted(((pos.value(m), m) for m in legal_moves), reverse=True):
                if val < val_lower:
                    break
                if depth <= 1 and pos.score + val < gamma:
                    yield move, pos.score + val if val < MATE_LOWER else MATE_UPPER
                    break
                yield move, -self.bound(pos.move(move), 1 - gamma, depth - 1)

        best = -MATE_UPPER
        for move, score in moves():
            best = max(best, score)
            if best >= gamma:
                if move is not None:
                    self.tp_move[pos] = move
                break

        # Improved mate/stalemate recognition
        if depth > 2 and best == -MATE_UPPER:
            flipped = pos.rotate(nullmove=True)
            in_check = self.bound(flipped, MATE_UPPER, 0) == MATE_UPPER
            best = -MATE_LOWER if in_check else 0

        if best >= gamma:
            self.tp_score[pos, depth, can_null] = Entry(best, entry.upper)
        if best < gamma:
            self.tp_score[pos, depth, can_null] = Entry(entry.lower, best)

        return best

    def search(self, history):
        """Iterative deepening MTD-bi search"""
        self.nodes = 0
        self.history = set(history)
        self.tp_score.clear()

        gamma = 0
        # In finished games, we could potentially go far enough to cause a recursion
        # limit exception. Hence we bound the ply. We also can't start at 0, since
        # that's quiscent search, and we don't always play legal moves there.
        for depth in range(1, 1000):
            # The inner loop is a binary search on the score of the position.
            # Inv: lower <= score <= upper
            # 'while lower != upper' would work, but it's too much effort to spend
            # on what's probably not going to change the move played.
            lower, upper = -MATE_LOWER, MATE_LOWER
            while lower < upper - EVAL_ROUGHNESS:
                score = self.bound(history[-1], gamma, depth, can_null=False)
                if score >= gamma:
                    lower = score
                if score < gamma:
                    upper = score
                yield depth, gamma, score, self.tp_move.get(history[-1])
                gamma = (lower + upper + 1) // 2


###############################################################################
# UCI User interface
###############################################################################


def parse(c):
    fil, rank = ord(c[0]) - ord("a"), int(c[1]) - 1
    return A1 + fil - 10 * rank


def render(i):
    rank, fil = divmod(i - A1, 10)
    return chr(fil + ord("a")) + str(-rank + 1)

hist = [Position(initial, 0, (True, True), (True, True), 0, 0)]

#input = raw_input

# minifier-hide start
import sys, tools.uci
tools.uci.run(sys.modules[__name__], hist[-1])
sys.exit()
# minifier-hide end

searcher = Searcher()
while True:
    args = input().split()
    if args[0] == "uci":
        print("id name", version)
        print("uciok")

    elif args[0] == "isready":
        print("readyok")

    elif args[0] == "quit":
        break

    elif args[:2] == ["position", "startpos"]:
        del hist[1:]
        for ply, move in enumerate(args[3:]):
            i, j, prom = parse(move[:2]), parse(move[2:4]), move[4:].upper()
            if ply % 2 == 1:
                i, j = 119 - i, 119 - j
            hist.append(hist[-1].move(Move(i, j, prom)))

    elif args[0] == "go":
        wtime, btime, winc, binc = [int(a) / 1000 for a in args[2::2]]
        if len(hist) % 2 == 0:
            wtime, winc = btime, binc
        think = min(wtime / 40 + winc, wtime / 2 - 1)

        start = time.time()
        move_str = None
        for depth, gamma, score, move in Searcher().search(hist):
            # The only way we can be sure to have the real move in tp_move,
            # is if we have just failed high.
            if score >= gamma:
                i, j = move.i, move.j
                if len(hist) % 2 == 0:
                    i, j = 119 - i, 119 - j
                move_str = render(i) + render(j) + move.prom.lower()
                print("info depth", depth, "score cp", score, "pv", move_str)
            if move_str and time.time() - start > think * 0.8:
                break

        print("bestmove", move_str or '(none)')

