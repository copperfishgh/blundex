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
import chess


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

    def reset_to_initial_position(self) -> None:
        """Reset the entire game state to the initial starting position"""
        self.board = chess.Board()
        self._update_game_status()
        self.move_history = []
        self.last_move = None
        self.undo_stack = []
        self.redo_stack = []


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
        hanging_pieces = []

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.color == color:
                if self._is_piece_hanging_simple(square):
                    hanging_pieces.append(square)

        return hanging_pieces

    def _is_piece_hanging_simple(self, square: chess.Square) -> bool:
        """Simple check: is piece attacked but not defended?"""
        piece = self.board.piece_at(square)
        if not piece:
            return False

        enemy_color = not piece.color

        # Is it attacked by an enemy?
        if not self.board.is_attacked_by(enemy_color, square):
            return False

        # Is it defended by a friendly piece?
        if self.board.is_attacked_by(piece.color, square):
            return False

        return True  # Attacked but not defended = hanging

    def _get_attackers(self, target_square: chess.Square, attacker_color: bool) -> List[chess.Square]:
        """Get all pieces of the given color that attack the target square"""
        attackers = []

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.color == attacker_color:
                piece_attacks = self.board.attacks(square)
                if target_square in piece_attacks:
                    attackers.append(square)

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
        backward_count = 0
        enemy_color = not color
        pawn_direction = 1 if color == chess.WHITE else -1

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.color == color and piece.piece_type == chess.PAWN:
                rank = chess.square_rank(square)
                file = chess.square_file(square)

                # Check if pawn can be defended
                can_be_defended = False
                defend_rank = rank - pawn_direction
                if 0 <= defend_rank <= 7:
                    for defend_file in [file - 1, file + 1]:
                        if 0 <= defend_file <= 7:
                            defend_square = chess.square(defend_file, defend_rank)
                            defender = self.board.piece_at(defend_square)
                            if defender and defender.color == color and defender.piece_type == chess.PAWN:
                                can_be_defended = True
                                break

                # Check if pawn can safely advance
                can_safely_advance = True
                advance_rank = rank + pawn_direction
                if 0 <= advance_rank <= 7:
                    for enemy_file in [file - 1, file + 1]:
                        if 0 <= enemy_file <= 7:
                            enemy_attack_rank = advance_rank + pawn_direction
                            if 0 <= enemy_attack_rank <= 7:
                                enemy_square = chess.square(enemy_file, enemy_attack_rank)
                                enemy_piece = self.board.piece_at(enemy_square)
                                if enemy_piece and enemy_piece.color == enemy_color and enemy_piece.piece_type == chess.PAWN:
                                    can_safely_advance = False
                                    break

                if not can_be_defended and not can_safely_advance:
                    backward_count += 1

        return backward_count

    def count_isolated_pawns(self, color: bool) -> int:
        """Count pawns with no friendly pawns on adjacent files"""
        isolated_count = 0

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.color == color and piece.piece_type == chess.PAWN:
                file = chess.square_file(square)

                # Check adjacent files
                has_adjacent_pawn = False
                for adjacent_file in [file - 1, file + 1]:
                    if 0 <= adjacent_file <= 7:
                        for check_rank in range(8):
                            check_square = chess.square(adjacent_file, check_rank)
                            adjacent_piece = self.board.piece_at(check_square)
                            if adjacent_piece and adjacent_piece.color == color and adjacent_piece.piece_type == chess.PAWN:
                                has_adjacent_pawn = True
                                break
                        if has_adjacent_pawn:
                            break

                if not has_adjacent_pawn:
                    isolated_count += 1

        return isolated_count

    def count_doubled_pawns(self, color: bool) -> int:
        """Count pawns that are doubled (more than one pawn on the same file)"""
        doubled_count = 0

        for file in range(8):
            pawns_on_file = 0
            for rank in range(8):
                square = chess.square(file, rank)
                piece = self.board.piece_at(square)
                if piece and piece.color == color and piece.piece_type == chess.PAWN:
                    pawns_on_file += 1

            if pawns_on_file > 1:
                doubled_count += pawns_on_file - 1

        return doubled_count

    def count_passed_pawns(self, color: bool) -> int:
        """Count passed pawns - pawns with no opponent pawns blocking their path to promotion"""
        passed_count = 0
        enemy_color = not color
        promotion_direction = 1 if color == chess.WHITE else -1

        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece and piece.color == color and piece.piece_type == chess.PAWN:
                rank = chess.square_rank(square)
                file = chess.square_file(square)

                # Check if this pawn is passed
                is_passed = True

                # Check path to promotion on this file and adjacent files
                for check_file in [file - 1, file, file + 1]:
                    if 0 <= check_file <= 7:
                        check_rank = rank + promotion_direction
                        while 0 <= check_rank <= 7:
                            check_square = chess.square(check_file, check_rank)
                            enemy_piece = self.board.piece_at(check_square)
                            if enemy_piece and enemy_piece.color == enemy_color and enemy_piece.piece_type == chess.PAWN:
                                is_passed = False
                                break
                            check_rank += promotion_direction

                        if not is_passed:
                            break

                if is_passed:
                    passed_count += 1

        return passed_count

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
