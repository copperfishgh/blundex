"""
Chess Board State Module

This module provides a wrapper around python-chess library with helper methods
for tactical analysis and game statistics.

Uses python-chess types directly:
- chess.Piece (piece type + color)
- chess.Square (0-63 integer)
- chess.WHITE/BLACK (boolean True/False)
- chess.PAWN/KNIGHT/BISHOP/ROOK/QUEEN/KING (integers 1-6)
"""

from typing import Optional, List, Tuple
import copy
import io
import chess
import chess.pgn
from config import GameConstants


class BoardState:
    """
    Chess board state with tactical analysis helpers.
    Wraps python-chess Board with additional functionality.
    """

    def __init__(self):
        """Initialize with standard starting position"""
        self.board = chess.Board()

        # Game status flags
        self.is_check = False
        self.is_in_checkmate = False
        self.is_in_stalemate = False

        # Move history tracking
        self.move_history: List[chess.Move] = []
        self.last_move: Optional[chess.Move] = None

        # Undo/redo stacks - store board copies
        self.undo_stack: List[Tuple[chess.Board, List[chess.Move], Optional[chess.Move]]] = []
        self.redo_stack: List[Tuple[chess.Board, List[chess.Move], Optional[chess.Move]]] = []

        # Mega-loop analysis cache - computed lazily on first access
        self._analysis: Optional[dict] = None
        self._analysis_valid = False

        self._update_game_status()

    @property
    def castling_rights(self):
        """Get castling rights as a named tuple-like object for test compatibility"""
        class CastlingRights:
            def __init__(self, board):
                self.white_kingside = board.has_kingside_castling_rights(chess.WHITE)
                self.white_queenside = board.has_queenside_castling_rights(chess.WHITE)
                self.black_kingside = board.has_kingside_castling_rights(chess.BLACK)
                self.black_queenside = board.has_queenside_castling_rights(chess.BLACK)
        return CastlingRights(self.board)

    # ========== MEGA-LOOP ANALYSIS INFRASTRUCTURE ==========

    def _invalidate_analysis(self) -> None:
        """Invalidate cached analysis after position changes"""
        self._analysis_valid = False

    def _ensure_analysis(self) -> None:
        """Compute analysis if not already cached (lazy evaluation)"""
        if not self._analysis_valid:
            self._analysis = self._compute_board_analysis()
            self._analysis_valid = True

    def _compute_board_analysis(self) -> dict:
        """
        Mega-loop: Single-pass bitboard-optimized board analysis.
        Computes all tactical patterns in one iteration through occupied squares.

        Performance: ~2-3x baseline cost for complete tactical analysis.
        Uses python-chess SquareSet (bitboard wrapper) for O(1) operations.
        """
        analysis = {
            # SECTION 1: Initialize storage
            # Hanging pieces (used by: get_hanging_pieces, hanging piece indicator)
            'white_hanging': [],
            'black_hanging': [],
            # Attacked pieces (used by: count_attacked_pieces, attacked indicator)
            'white_attacked': [],
            'black_attacked': [],
            # Pinned pieces (used by: get_pinned_pieces, pin indicator)
            'white_pinned': [],
            'black_pinned': [],
            # Skewered pieces (used by: get_skewered_pieces, skewer indicator)
            'white_skewered': [],
            'black_skewered': [],
            # Pawn patterns (used by: pawn statistics display)
            'white_isolated': [],
            'black_isolated': [],
            'white_doubled': [],
            'black_doubled': [],
            'white_passed': [],
            'black_passed': [],
            'white_backward': [],
            'black_backward': [],
        }

        # SECTION 2: Basic piece information + hanging/attacked detection
        # BITBOARD: Iterate only occupied squares (~25 pieces) instead of all 64
        for square in chess.SquareSet(self.board.occupied):
            piece = self.board.piece_at(square)
            if not piece:
                continue

            enemy_color = not piece.color

            # BITBOARD: attackers() returns SquareSet (bitboard wrapper)
            # Keep as SquareSet - don't convert to Python set!
            attackers = self.board.attackers(enemy_color, square)
            defenders = self.board.attackers(piece.color, square)

            # Check if attacked (len on SquareSet is O(1) popcount)
            if len(attackers) > 0:
                if piece.color == chess.WHITE:
                    analysis['white_attacked'].append(square)
                else:
                    analysis['black_attacked'].append(square)

                # Check if hanging (attacked AND not defended)
                if len(defenders) == 0:
                    if piece.color == chess.WHITE:
                        analysis['white_hanging'].append(square)
                    else:
                        analysis['black_hanging'].append(square)

        # SECTION 3: Pins and skewers
        # Pin detection: Use built-in board.is_pinned() for efficiency
        # Skewer detection: Custom implementation using BB_RAYS

        # --- PIN DETECTION ---
        # BITBOARD: Get all non-pawn pieces for both colors
        white_pieces = chess.SquareSet(self.board.occupied_co[chess.WHITE])
        black_pieces = chess.SquareSet(self.board.occupied_co[chess.BLACK])

        white_non_pawn = white_pieces & ~chess.SquareSet(self.board.pawns)
        black_non_pawn = black_pieces & ~chess.SquareSet(self.board.pawns)

        # --- PIN DETECTION ---
        # Detect both absolute pins (to king) and relative pins (to valuable pieces)
        for color in [chess.WHITE, chess.BLACK]:
            enemy_color = not color
            color_pieces = white_pieces if color == chess.WHITE else black_pieces

            # Get enemy sliding pieces (B/R/Q can create pins)
            enemy_sliding_pieces = chess.SquareSet(self.board.occupied_co[enemy_color]) & (
                chess.SquareSet(self.board.bishops) |
                chess.SquareSet(self.board.rooks) |
                chess.SquareSet(self.board.queens)
            )

            for attacker_square in enemy_sliding_pieces:
                # Get all squares this sliding piece attacks
                attacked_squares = self.board.attacks(attacker_square)

                # Check each attacked piece of our color
                for attacked_square in (attacked_squares & color_pieces):
                    attacked_piece = self.board.piece_at(attacked_square)

                    # Skip pawns (not considered pinnable for display purposes)
                    if attacked_piece.piece_type == chess.PAWN:
                        continue

                    # Get ray from attacker through attacked piece
                    ray = chess.BB_RAYS[attacker_square][attacked_square]
                    if ray:
                        # Look for valuable pieces behind the attacked piece on the same ray
                        for behind_square in chess.SquareSet(ray):
                            # Skip the attacker and attacked squares
                            if behind_square in (attacker_square, attacked_square):
                                continue

                            # Only check squares beyond the attacked piece
                            if chess.square_distance(attacker_square, behind_square) <= \
                               chess.square_distance(attacker_square, attacked_square):
                                continue

                            behind_piece = self.board.piece_at(behind_square)

                            # Found a piece behind?
                            if behind_piece and behind_piece.color == color:
                                # Check if it's a valid pin (behind piece must be king or higher value)
                                behind_value = GameConstants.PIECE_VALUES[behind_piece.piece_type]
                                front_value = GameConstants.PIECE_VALUES[attacked_piece.piece_type]

                                is_pin = (behind_piece.piece_type == chess.KING or
                                         behind_value > front_value)

                                if is_pin:
                                    # Verify no pieces between front and back
                                    between_squares = chess.SquareSet(chess.between(attacked_square, behind_square))
                                    if not any(self.board.piece_at(sq) for sq in between_squares):
                                        # Valid pin detected!
                                        if color == chess.WHITE:
                                            analysis['white_pinned'].append(attacked_square)
                                        else:
                                            analysis['black_pinned'].append(attacked_square)
                                        break  # Only need first pin on this ray

        # --- SKEWER DETECTION ---
        # Process both colors
        for color in [chess.WHITE, chess.BLACK]:
            enemy_color = not color
            color_pieces = white_pieces if color == chess.WHITE else black_pieces

            # BITBOARD: Get only enemy sliding pieces (B/R/Q can create skewers)
            enemy_sliding_pieces = chess.SquareSet(self.board.occupied_co[enemy_color]) & (
                chess.SquareSet(self.board.bishops) |
                chess.SquareSet(self.board.rooks) |
                chess.SquareSet(self.board.queens)
            )

            for attacker_square in enemy_sliding_pieces:
                # Get all squares this sliding piece attacks
                attacked_squares = self.board.attacks(attacker_square)

                # Check each attacked piece of our color
                for attacked_square in (attacked_squares & color_pieces):
                    attacked_piece = self.board.piece_at(attacked_square)

                    # Skip pawns (not considered skewerable)
                    if attacked_piece.piece_type == chess.PAWN:
                        continue

                    # BITBOARD: Get full ray between attacker and attacked piece (O(1))
                    ray = chess.BB_RAYS[attacker_square][attacked_square]
                    if ray:  # Non-zero bitboard means there's a ray between these squares

                        # Look for pieces behind the attacked piece on the same ray
                        for behind_square in chess.SquareSet(ray):
                            # Skip the attacker and attacked squares
                            if behind_square in (attacker_square, attacked_square):
                                continue

                            # Only check squares beyond the attacked piece
                            if chess.square_distance(attacker_square, behind_square) <= \
                               chess.square_distance(attacker_square, attacked_square):
                                continue

                            behind_piece = self.board.piece_at(behind_square)

                            # Found a piece behind?
                            if behind_piece and behind_piece.color == color:
                                # Check if it's a valid skewer (front >= back in value)
                                # OR if front piece is king (absolute skewer)
                                front_value = GameConstants.PIECE_VALUES[attacked_piece.piece_type]
                                back_value = GameConstants.PIECE_VALUES[behind_piece.piece_type]

                                is_skewer = (front_value >= back_value or
                                           attacked_piece.piece_type == chess.KING)

                                if is_skewer:
                                    # BITBOARD: Verify no pieces between front and back (O(1))
                                    between_squares = chess.SquareSet(chess.between(attacked_square, behind_square))
                                    if not any(self.board.piece_at(sq) for sq in between_squares):
                                        # Valid skewer detected!
                                        if color == chess.WHITE:
                                            analysis['white_skewered'].append(attacked_square)
                                        else:
                                            analysis['black_skewered'].append(attacked_square)
                                        break  # Only need first skewer on this ray

        # SECTION 4: Pawn patterns
        # BITBOARD: Get pawn bitboards for both colors
        white_pawns = chess.SquareSet(self.board.pawns & self.board.occupied_co[chess.WHITE])
        black_pawns = chess.SquareSet(self.board.pawns & self.board.occupied_co[chess.BLACK])

        # File masks for bitboard operations (8 iterations, not 64!)
        FILE_MASKS = [chess.BB_FILES[i] for i in range(8)]

        # --- DOUBLED PAWNS (check each file) ---
        for file_idx in range(8):
            white_on_file = white_pawns & chess.SquareSet(FILE_MASKS[file_idx])
            if len(white_on_file) > 1:
                for square in white_on_file:
                    analysis['white_doubled'].append(square)

            black_on_file = black_pawns & chess.SquareSet(FILE_MASKS[file_idx])
            if len(black_on_file) > 1:
                for square in black_on_file:
                    analysis['black_doubled'].append(square)

        # --- ISOLATED PAWNS ---
        for square in white_pawns:
            file = chess.square_file(square)
            # BITBOARD: Check adjacent files with bitboard operations
            left_file = FILE_MASKS[file-1] if file > 0 else 0
            right_file = FILE_MASKS[file+1] if file < 7 else 0
            adjacent_mask = left_file | right_file
            # Instant check: are there any white pawns on adjacent files?
            if not (white_pawns & chess.SquareSet(adjacent_mask)):
                analysis['white_isolated'].append(square)

        for square in black_pawns:
            file = chess.square_file(square)
            left_file = FILE_MASKS[file-1] if file > 0 else 0
            right_file = FILE_MASKS[file+1] if file < 7 else 0
            adjacent_mask = left_file | right_file
            if not (black_pawns & chess.SquareSet(adjacent_mask)):
                analysis['black_isolated'].append(square)

        # --- PASSED PAWNS ---
        for square in white_pawns:
            rank = chess.square_rank(square)
            file = chess.square_file(square)
            # Check if no enemy pawns block path to promotion (ranks ahead)
            is_passed = True
            for check_file in [file - 1, file, file + 1]:
                if 0 <= check_file <= 7:
                    for check_rank in range(rank + 1, 8):
                        check_square = chess.square(check_file, check_rank)
                        if check_square in black_pawns:
                            is_passed = False
                            break
                    if not is_passed:
                        break
            if is_passed:
                analysis['white_passed'].append(square)

        for square in black_pawns:
            rank = chess.square_rank(square)
            file = chess.square_file(square)
            is_passed = True
            for check_file in [file - 1, file, file + 1]:
                if 0 <= check_file <= 7:
                    for check_rank in range(0, rank):
                        check_square = chess.square(check_file, check_rank)
                        if check_square in white_pawns:
                            is_passed = False
                            break
                    if not is_passed:
                        break
            if is_passed:
                analysis['black_passed'].append(square)

        # --- BACKWARD PAWNS ---
        for square in white_pawns:
            rank = chess.square_rank(square)
            file = chess.square_file(square)
            # Can be defended by friendly pawn?
            can_be_defended = False
            if rank > 0:  # Not on first rank
                for defend_file in [file - 1, file + 1]:
                    if 0 <= defend_file <= 7:
                        defend_square = chess.square(defend_file, rank - 1)
                        if defend_square in white_pawns:
                            can_be_defended = True
                            break
            # Can safely advance?
            can_safely_advance = True
            if rank < 7:  # Not on last rank
                for enemy_file in [file - 1, file + 1]:
                    if 0 <= enemy_file <= 7 and rank + 2 <= 7:
                        enemy_square = chess.square(enemy_file, rank + 2)
                        if enemy_square in black_pawns:
                            can_safely_advance = False
                            break
            if not can_be_defended and not can_safely_advance:
                analysis['white_backward'].append(square)

        for square in black_pawns:
            rank = chess.square_rank(square)
            file = chess.square_file(square)
            can_be_defended = False
            if rank < 7:  # Not on last rank
                for defend_file in [file - 1, file + 1]:
                    if 0 <= defend_file <= 7:
                        defend_square = chess.square(defend_file, rank + 1)
                        if defend_square in black_pawns:
                            can_be_defended = True
                            break
            can_safely_advance = True
            if rank > 0:  # Not on first rank
                for enemy_file in [file - 1, file + 1]:
                    if 0 <= enemy_file <= 7 and rank - 2 >= 0:
                        enemy_square = chess.square(enemy_file, rank - 2)
                        if enemy_square in white_pawns:
                            can_safely_advance = False
                            break
            if not can_be_defended and not can_safely_advance:
                analysis['black_backward'].append(square)

        return analysis

    def reset_to_initial_position(self) -> None:
        """Reset the entire game state to the initial starting position"""
        self.board = chess.Board()
        self._update_game_status()
        self.move_history = []
        self.last_move = None
        self.undo_stack = []
        self.redo_stack = []
        self._invalidate_analysis()  # Invalidate cache after position change


    def is_king_in_check(self, color: bool) -> bool:
        """Check if the king of a specific color is in check"""
        original_turn = self.board.turn
        self.board.turn = color
        in_check = self.board.is_check()
        self.board.turn = original_turn
        return in_check

    def can_castle(self, color: bool, kingside: bool) -> bool:
        """Check if castling is possible"""
        if kingside:
            if not self.board.has_kingside_castling_rights(color):
                return False
        else:
            if not self.board.has_queenside_castling_rights(color):
                return False

        # Check if castling move exists in legal moves
        for move in self.board.legal_moves:
            if self.board.is_castling(move):
                # Check if it's the right color's turn
                king_square = self.board.king(color)
                if move.from_square == king_square:
                    # Check direction
                    if kingside and chess.square_file(move.to_square) == 6:  # g-file
                        return True
                    elif not kingside and chess.square_file(move.to_square) == 2:  # c-file
                        return True

        return False

    def get_hanging_pieces(self, color: bool) -> List[chess.Square]:
        """Get list of hanging pieces (attacked but not defended) for the given color"""
        self._ensure_analysis()
        return self._analysis['white_hanging' if color == chess.WHITE else 'black_hanging']

    def _get_attackers(self, target_square: chess.Square, attacker_color: bool) -> List[chess.Square]:
        """Get all pieces of the given color that attack the target square (including x-ray attacks)"""
        attackers = []

        # First, get direct attackers
        direct_attackers = list(self.board.attackers(attacker_color, target_square))
        attackers.extend(direct_attackers)

        # Now find x-ray attackers: pieces that would attack if direct attackers were removed
        # Only sliding pieces (bishops, rooks, queens) can create x-ray attacks
        target_piece = self.board.piece_at(target_square)

        # Temporarily remove target piece and all direct attackers to reveal x-ray attackers
        removed_pieces = []
        if target_piece:
            self.board.remove_piece_at(target_square)
            removed_pieces.append((target_square, target_piece))

        for sq in direct_attackers:
            piece = self.board.piece_at(sq)
            if piece:
                self.board.remove_piece_at(sq)
                removed_pieces.append((sq, piece))

        # Find new attackers that were previously blocked
        xray_attackers = list(self.board.attackers(attacker_color, target_square))
        attackers.extend(xray_attackers)

        # Restore all removed pieces
        for sq, piece in removed_pieces:
            self.board.set_piece_at(sq, piece)

        return attackers

    def get_tactically_interesting_squares(self) -> List[chess.Square]:
        """Get all squares that have tactical potential for exchange evaluation"""
        interesting_squares = []

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece is not None:
                enemy_color = not piece.color
                if self.board.is_attacked_by(enemy_color, square):
                    interesting_squares.append(square)

        return interesting_squares

    def get_all_attackers_and_defenders(self, target_square: chess.Square) -> Tuple[List[chess.Square], List[chess.Square]]:
        """Get all pieces that can attack or defend a given square"""
        target_piece = self.board.piece_at(target_square)

        if target_piece is None:
            # Empty square - anyone can attack it, but no one defends it
            white_attackers = self._get_attackers(target_square, chess.WHITE)
            black_attackers = self._get_attackers(target_square, chess.BLACK)
            return (white_attackers + black_attackers, [])

        # Square contains a piece
        target_color = target_piece.color
        enemy_color = not target_color

        # Attackers are enemy pieces
        attackers = self._get_attackers(target_square, enemy_color)

        # Defenders: friendly pieces that could recapture if this piece is taken
        defenders = self._get_attackers_if_empty(target_square, target_color)

        # Remove the target piece itself from defenders
        defenders = [sq for sq in defenders if sq != target_square]

        return (attackers, defenders)

    def _get_attackers_if_empty(self, target_square: chess.Square, attacker_color: bool) -> List[chess.Square]:
        """Get all pieces that could attack this square if it were empty"""
        # Temporarily remove the piece
        original_piece = self.board.piece_at(target_square)
        self.board.remove_piece_at(target_square)

        # Get attackers
        attackers = self._get_attackers(target_square, attacker_color)

        # Restore piece
        if original_piece:
            self.board.set_piece_at(target_square, original_piece)

        return attackers

    def get_fen_position(self) -> str:
        """Generate FEN (Forsyth-Edwards Notation) string for the current position"""
        return self.board.fen()

    def calculate_activity(self, color: bool) -> int:
        """Calculate total squares reachable by all pieces of a color (excluding pawns)"""
        reachable_squares = set()

        # Save current turn
        original_turn = self.board.turn

        # Set turn to the color we're checking
        self.board.turn = color

        # Only count squares that pieces can legally reach
        for move in self.board.legal_moves:
            piece = self.board.piece_at(move.from_square)
            if piece and piece.color == color and piece.piece_type != chess.PAWN:
                reachable_squares.add(move.to_square)

        # Restore original turn
        self.board.turn = original_turn

        return len(reachable_squares)

    def get_activity_scores(self) -> Tuple[int, int]:
        """Get activity scores for both colors. Returns (white_activity, black_activity)"""
        white_activity = self.calculate_activity(chess.WHITE)
        black_activity = self.calculate_activity(chess.BLACK)
        return (white_activity, black_activity)

    def count_developed_pieces(self, color: bool) -> int:
        """Count how many pieces are developed (moved off back rank or connected rooks)"""
        if color == chess.WHITE:
            starting_rank = 0  # rank 1
            king_start = chess.E1
            queenside_rook_start = chess.A1
            kingside_rook_start = chess.H1
        else:
            starting_rank = 7  # rank 8
            king_start = chess.E8
            queenside_rook_start = chess.A8
            kingside_rook_start = chess.H8

        developed_count = 0

        # Check knights, bishops, and queen - simple: off back rank = developed
        for piece_type in [chess.KNIGHT, chess.BISHOP, chess.QUEEN]:
            for square in chess.SQUARES:
                piece = self.board.piece_at(square)
                if piece and piece.color == color and piece.piece_type == piece_type:
                    if chess.square_rank(square) != starting_rank:
                        developed_count += 1

        # King: developed if castled (not on starting square)
        king_square = self.board.king(color)
        if king_square != king_start:
            developed_count += 1

        # Rooks: developed if moved OR if rooks are connected
        rook_squares = []
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.color == color and piece.piece_type == chess.ROOK:
                rook_squares.append(square)

        # Check if rooks are connected (can see each other on back rank)
        rooks_connected = False
        if len(rook_squares) == 2:
            r1, r2 = rook_squares
            # Both on starting rank?
            if chess.square_rank(r1) == starting_rank and chess.square_rank(r2) == starting_rank:
                # Check if they can see each other (no pieces between them)
                file1, file2 = chess.square_file(r1), chess.square_file(r2)
                min_file, max_file = min(file1, file2), max(file1, file2)
                pieces_between = False
                for file in range(min_file + 1, max_file):
                    check_square = chess.square(file, starting_rank)
                    if self.board.piece_at(check_square):
                        pieces_between = True
                        break
                if not pieces_between:
                    rooks_connected = True

        # Count developed rooks
        for rook_square in rook_squares:
            if chess.square_rank(rook_square) != starting_rank:
                # Rook moved off back rank
                developed_count += 1
            elif rooks_connected:
                # Rook still on back rank but connected
                developed_count += 1

        return developed_count

    def get_development_scores(self) -> Tuple[int, int]:
        """Get development scores for both colors. Returns (white_dev, black_dev)"""
        white_dev = self.count_developed_pieces(chess.WHITE)
        black_dev = self.count_developed_pieces(chess.BLACK)
        return (white_dev, black_dev)

    def count_attacked_pieces(self, color: bool) -> int:
        """Count how many pieces of this color are attacked by the enemy"""
        self._ensure_analysis()
        attacked_list = self._analysis['white_attacked' if color == chess.WHITE else 'black_attacked']
        return len(attacked_list)

    def get_attacked_scores(self) -> Tuple[int, int]:
        """Get attacked piece counts for both colors. Returns (white_attacked, black_attacked)"""
        white_attacked = self.count_attacked_pieces(chess.WHITE)
        black_attacked = self.count_attacked_pieces(chess.BLACK)
        return (white_attacked, black_attacked)

    def count_hanging_pieces(self, color: bool) -> int:
        """Count how many pieces of this color are hanging (attacked but not defended)"""
        return len(self.get_hanging_pieces(color))

    def get_hanging_scores(self) -> Tuple[int, int]:
        """Get hanging piece counts for both colors. Returns (white_hanging, black_hanging)"""
        white_hanging = self.count_hanging_pieces(chess.WHITE)
        black_hanging = self.count_hanging_pieces(chess.BLACK)
        return (white_hanging, black_hanging)

    def get_pinned_pieces(self, color: bool) -> List[int]:
        """Get list of pinned pieces for the given color"""
        self._ensure_analysis()
        return self._analysis['white_pinned' if color == chess.WHITE else 'black_pinned']

    def get_skewered_pieces(self, color: bool) -> List[int]:
        """Get list of skewered pieces for the given color"""
        self._ensure_analysis()
        return self._analysis['white_skewered' if color == chess.WHITE else 'black_skewered']

    def count_pawns(self, color: bool) -> int:
        """Count the number of pawns for a given color"""
        count = 0
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.color == color and piece.piece_type == chess.PAWN:
                count += 1
        return count

    def get_pawn_counts(self) -> Tuple[int, int]:
        """Get pawn counts for both colors. Returns (white_pawns, black_pawns)"""
        white_pawns = self.count_pawns(chess.WHITE)
        black_pawns = self.count_pawns(chess.BLACK)
        return (white_pawns, black_pawns)

    def count_backward_pawns(self, color: bool) -> int:
        """Count backward pawns - pawns that cannot be defended by other pawns and cannot safely advance"""
        self._ensure_analysis()
        backward_list = self._analysis['white_backward' if color == chess.WHITE else 'black_backward']
        return len(backward_list)

    def count_isolated_pawns(self, color: bool) -> int:
        """Count pawns with no friendly pawns on adjacent files"""
        self._ensure_analysis()
        isolated_list = self._analysis['white_isolated' if color == chess.WHITE else 'black_isolated']
        return len(isolated_list)

    def count_doubled_pawns(self, color: bool) -> int:
        """Count pawns that are doubled (more than one pawn on the same file)"""
        self._ensure_analysis()
        doubled_list = self._analysis['white_doubled' if color == chess.WHITE else 'black_doubled']
        return len(doubled_list)

    def count_passed_pawns(self, color: bool) -> int:
        """Count passed pawns - pawns with no opponent pawns blocking their path to promotion"""
        self._ensure_analysis()
        passed_list = self._analysis['white_passed' if color == chess.WHITE else 'black_passed']
        return len(passed_list)

    def get_pawn_statistics(self) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
        """Get pawn statistics for both colors"""
        white_stats = (
            self.count_backward_pawns(chess.WHITE),
            self.count_isolated_pawns(chess.WHITE),
            self.count_doubled_pawns(chess.WHITE),
            self.count_passed_pawns(chess.WHITE)
        )
        black_stats = (
            self.count_backward_pawns(chess.BLACK),
            self.count_isolated_pawns(chess.BLACK),
            self.count_doubled_pawns(chess.BLACK),
            self.count_passed_pawns(chess.BLACK)
        )
        return (white_stats, black_stats)

    def copy(self) -> 'BoardState':
        """Create a deep copy of the board state"""
        new_state = BoardState()
        new_state.board = self.board.copy()
        new_state.is_check = self.is_check
        new_state.is_in_checkmate = self.is_in_checkmate
        new_state.is_in_stalemate = self.is_in_stalemate
        new_state.move_history = copy.copy(self.move_history)
        new_state.last_move = self.last_move
        # Don't copy undo/redo stacks
        return new_state

    def get_possible_moves(self, square: chess.Square) -> List[chess.Square]:
        """Get all legal moves for a piece at the given square"""
        piece = self.board.piece_at(square)
        if not piece or piece.color != self.board.turn:
            return []

        legal_moves = []
        for move in self.board.legal_moves:
            if move.from_square == square:
                legal_moves.append(move.to_square)

        return legal_moves

    def make_move(self, from_square: chess.Square, to_square: chess.Square) -> bool:
        """Execute a move if it's legal. Returns True if successful."""
        # Find the matching legal move
        chess_move = None
        for move in self.board.legal_moves:
            if move.from_square == from_square and move.to_square == to_square:
                # For pawn promotion, default to queen
                if move.promotion:
                    if move.promotion == chess.QUEEN:
                        chess_move = move
                        break
                else:
                    chess_move = move
                    break

        if chess_move is None:
            return False

        # Save state for undo
        self._save_state_for_undo()

        # Execute the move
        self.board.push(chess_move)
        self.last_move = chess_move
        self.move_history.append(chess_move)

        # Update game status
        self._update_game_status()
        self._invalidate_analysis()  # Invalidate cache after move

        return True

    def make_move_with_promotion(self, from_square: chess.Square, to_square: chess.Square,
                                promotion_piece: int = chess.QUEEN) -> bool:
        """Execute a move with pawn promotion. Returns True if successful."""
        # Find the matching legal move
        chess_move = None
        for move in self.board.legal_moves:
            if move.from_square == from_square and move.to_square == to_square:
                if move.promotion:
                    if move.promotion == promotion_piece:
                        chess_move = move
                        break
                else:
                    chess_move = move
                    break

        if chess_move is None:
            return False

        # Save state for undo
        self._save_state_for_undo()

        # Execute the move
        self.board.push(chess_move)
        self.last_move = chess_move
        self.move_history.append(chess_move)

        # Update game status
        self._update_game_status()
        self._invalidate_analysis()  # Invalidate cache after move

        return True

    def is_pawn_promotion(self, from_square: chess.Square, to_square: chess.Square) -> bool:
        """Check if a move would result in pawn promotion"""
        piece = self.board.piece_at(from_square)
        if not piece or piece.piece_type != chess.PAWN:
            return False

        to_rank = chess.square_rank(to_square)
        if piece.color == chess.WHITE and to_rank == 7:
            return True
        elif piece.color == chess.BLACK and to_rank == 0:
            return False

        return False

    def is_checkmate(self, color: bool) -> bool:
        """Check if the specified color is in checkmate"""
        original_turn = self.board.turn
        self.board.turn = color
        is_mate = self.board.is_checkmate()
        self.board.turn = original_turn
        return is_mate

    def is_stalemate(self, color: bool) -> bool:
        """Check if the specified color is in stalemate"""
        original_turn = self.board.turn
        self.board.turn = color
        is_stale = self.board.is_stalemate()
        self.board.turn = original_turn
        return is_stale

    def _update_game_status(self) -> None:
        """Update is_check, is_in_checkmate, is_in_stalemate"""
        self.is_check = self.board.is_check()
        self.is_in_checkmate = self.board.is_checkmate()
        self.is_in_stalemate = self.board.is_stalemate()

    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return len(self.redo_stack) > 0

    def _save_state_for_undo(self) -> None:
        """Save current board state to undo stack"""
        state_tuple = (self.board.copy(), copy.copy(self.move_history), self.last_move)
        self.undo_stack.append(state_tuple)
        self.redo_stack.clear()

    def undo_move(self) -> bool:
        """Undo the last move. Returns True if successful."""
        if not self.can_undo():
            return False

        # Save current state to redo stack
        current_state = (self.board.copy(), copy.copy(self.move_history), self.last_move)
        self.redo_stack.append(current_state)

        # Restore previous state
        previous_board, previous_history, previous_last_move = self.undo_stack.pop()
        self.board = previous_board.copy()
        self.move_history = previous_history
        self.last_move = previous_last_move

        self._update_game_status()
        self._invalidate_analysis()  # Invalidate cache after undo
        return True

    def redo_move(self) -> bool:
        """Redo the last undone move. Returns True if successful."""
        if not self.can_redo():
            return False

        # Save current state to undo stack
        current_state = (self.board.copy(), copy.copy(self.move_history), self.last_move)
        self.undo_stack.append(current_state)

        # Restore next state
        next_board, next_history, next_last_move = self.redo_stack.pop()
        self.board = next_board.copy()
        self.move_history = next_history
        self.last_move = next_last_move

        self._update_game_status()
        self._invalidate_analysis()  # Invalidate cache after redo
        return True

    def load_pgn_file(self, filename: str) -> bool:
        """Load a game from a PGN file"""
        try:
            with open(filename, 'r') as f:
                pgn_text = f.read()

            # Parse the PGN using python-chess
            import io
            pgn = chess.pgn.read_game(io.StringIO(pgn_text))

            if pgn is None:
                return False

            # Reset to starting position
            self.board = chess.Board()
            self.move_history = []
            self.last_move = None

            # Replay all moves from the PGN
            for move in pgn.mainline_moves():
                self.board.push(move)
                self.move_history.append(move)
                self.last_move = move

            # Clear undo/redo stacks after loading
            self.undo_stack = []
            self.redo_stack = []

            self._update_game_status()
            self._invalidate_analysis()  # Invalidate cache after loading PGN
            return True

        except Exception as e:
            print(f"Error loading PGN file: {e}")
            return False

    def save_pgn_file(self, filename: str, white_player: str = "Player", black_player: str = "Opponent", event: str = "Casual Game") -> bool:
        """Save current game to a PGN file"""
        try:
            # Create a new game
            game = chess.pgn.Game()

            # Set headers
            game.headers["Event"] = event
            game.headers["White"] = white_player
            game.headers["Black"] = black_player
            game.headers["Result"] = "*"

            # Add moves
            node = game
            for move in self.move_history:
                node = node.add_variation(move)

            # Write to file
            with open(filename, 'w') as f:
                f.write(str(game))

            return True

        except Exception as e:
            print(f"Error saving PGN file: {e}")
            return False

    def __str__(self) -> str:
        """String representation of the board"""
        return str(self.board)


# Coordinate conversion helpers for backward compatibility
def square_from_coords(row: int, col: int) -> chess.Square:
    """Convert (row, col) coordinates to chess.Square.
    Row 0 = rank 8, Row 7 = rank 1 (display coordinates)"""
    rank = 7 - row  # Invert: row 0 -> rank 7, row 7 -> rank 0
    file = col
    return chess.square(file, rank)

def coords_from_square(square: chess.Square) -> Tuple[int, int]:
    """Convert chess.Square to (row, col) coordinates.
    Returns display coordinates where row 0 = rank 8"""
    rank = chess.square_rank(square)
    file = chess.square_file(square)
    row = 7 - rank  # Invert: rank 7 -> row 0, rank 0 -> row 7
    col = file
    return (row, col)


# Example usage
if __name__ == "__main__":
    board = BoardState()
    print("Initial Chess Position:")
    print(board)
    print(f"\nFEN: {board.get_fen_position()}")
    print(f"Current turn: {'White' if board.board.turn == chess.WHITE else 'Black'}")
