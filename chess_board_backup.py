"""
Chess Board State Data Structure

This module defines a comprehensive chess board state that tracks:
- Current piece positions
- Castling rights (kingside/queenside for both colors)
- En passant target square
- Move history and counters
- Game state information (turn, check status, etc.)

Powered by python-chess library for fast and reliable chess logic.
"""

from typing import Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
import copy
import chess

class PieceType(Enum):
    """Chess piece types"""
    PAWN = "P"
    ROOK = "R"
    KNIGHT = "N"
    BISHOP = "B"
    QUEEN = "Q"
    KING = "K"

class Color(Enum):
    """Chess piece colors"""
    WHITE = "w"
    BLACK = "b"

class GamePhase(Enum):
    """Game phases"""
    OPENING = "opening"
    MIDDLEGAME = "middlegame"
    ENDGAME = "endgame"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    DRAW = "draw"

@dataclass
class Piece:
    """Represents a chess piece"""
    type: PieceType
    color: Color
    has_moved: bool = False  # Important for castling and pawn double moves

    def __str__(self) -> str:
        """String representation: uppercase for white, lowercase for black"""
        symbol = self.type.value
        return symbol.upper() if self.color == Color.WHITE else symbol.lower()

    def get_value(self) -> int:
        """Get the material value of this piece"""
        from config import GameConstants
        return GameConstants.PIECE_VALUES.get(self.type.value.upper(), 0)

@dataclass
class CastlingRights:
    """Tracks castling rights for both colors"""
    white_kingside: bool = True
    white_queenside: bool = True
    black_kingside: bool = True
    black_queenside: bool = True

    def can_castle(self, color: Color, kingside: bool) -> bool:
        """Check if a color can castle in a specific direction"""
        if color == Color.WHITE:
            return self.white_kingside if kingside else self.white_queenside
        else:
            return self.black_kingside if kingside else self.black_queenside

    def lose_castling_right(self, color: Color, kingside: bool) -> None:
        """Remove castling rights"""
        if color == Color.WHITE:
            if kingside:
                self.white_kingside = False
            else:
                self.white_queenside = False
        else:
            if kingside:
                self.black_kingside = False
            else:
                self.black_queenside = False

    def lose_all_castling_rights(self, color: Color) -> None:
        """Remove all castling rights for a color (when king moves)"""
        if color == Color.WHITE:
            self.white_kingside = False
            self.white_queenside = False
        else:
            self.black_kingside = False
            self.black_queenside = False

@dataclass
class Move:
    """Represents a chess move with all relevant information"""
    from_square: Tuple[int, int]  # (row, col)
    to_square: Tuple[int, int]    # (row, col)
    piece: Piece
    captured_piece: Optional[Piece] = None
    promotion: Optional[PieceType] = None
    is_castle: bool = False
    castle_kingside: bool = False
    is_en_passant: bool = False
    is_double_pawn_push: bool = False
    move_number: int = 0
    notation: str = ""  # Algebraic notation like "Nf3", "O-O", "exd5"

    def __str__(self) -> str:
        return self.notation if self.notation else f"{self.from_square} -> {self.to_square}"

@dataclass
class BoardState:
    """
    Comprehensive chess board state that tracks all game information.
    Uses python-chess library for robust chess logic.
    """
    # Internal python-chess board
    _board: chess.Board = field(default_factory=chess.Board)

    # Game status
    is_check: bool = False
    is_in_checkmate: bool = False
    is_in_stalemate: bool = False
    game_phase: GamePhase = GamePhase.OPENING

    # Move history (for our custom Move objects)
    move_history: List[Move] = field(default_factory=list)

    # Last move for highlighting (None if no moves made yet)
    last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None  # ((from_row, from_col), (to_row, to_col))

    # Undo/Redo functionality - store board copies and move history
    undo_stack: List[Tuple[chess.Board, List[Move], Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]] = field(default_factory=list)
    redo_stack: List[Tuple[chess.Board, List[Move], Optional[Tuple[Tuple[int, int], Tuple[int, int]]]]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize the board with starting position"""
        self._update_game_status()

    # Conversion utilities between python-chess and our coordinate system
    @staticmethod
    def _pos_to_square(row: int, col: int) -> chess.Square:
        """Convert (row, col) to chess.Square. Row 0 = rank 8, Row 7 = rank 1"""
        rank = 7 - row  # Invert row: our row 0 is rank 8
        file = col
        return chess.square(file, rank)

    @staticmethod
    def _square_to_pos(square: chess.Square) -> Tuple[int, int]:
        """Convert chess.Square to (row, col)"""
        rank = chess.square_rank(square)
        file = chess.square_file(square)
        row = 7 - rank  # Invert rank: rank 8 is our row 0
        col = file
        return (row, col)

    @staticmethod
    def _piece_type_to_chess(piece_type: PieceType) -> chess.PieceType:
        """Convert our PieceType to chess.PieceType"""
        mapping = {
            PieceType.PAWN: chess.PAWN,
            PieceType.ROOK: chess.ROOK,
            PieceType.KNIGHT: chess.KNIGHT,
            PieceType.BISHOP: chess.BISHOP,
            PieceType.QUEEN: chess.QUEEN,
            PieceType.KING: chess.KING
        }
        return mapping[piece_type]

    @staticmethod
    def _chess_piece_type_to_ours(piece_type: chess.PieceType) -> PieceType:
        """Convert chess.PieceType to our PieceType"""
        mapping = {
            chess.PAWN: PieceType.PAWN,
            chess.ROOK: PieceType.ROOK,
            chess.KNIGHT: PieceType.KNIGHT,
            chess.BISHOP: PieceType.BISHOP,
            chess.QUEEN: PieceType.QUEEN,
            chess.KING: PieceType.KING
        }
        return mapping[piece_type]

    @staticmethod
    def _color_to_chess(color: Color) -> chess.Color:
        """Convert our Color to chess.Color"""
        return chess.WHITE if color == Color.WHITE else chess.BLACK

    @staticmethod
    def _chess_color_to_ours(color: chess.Color) -> Color:
        """Convert chess.Color to our Color"""
        return Color.WHITE if color == chess.WHITE else Color.BLACK

    def _chess_piece_to_ours(self, piece: chess.Piece) -> Piece:
        """Convert chess.Piece to our Piece"""
        piece_type = self._chess_piece_type_to_ours(piece.piece_type)
        color = self._chess_color_to_ours(piece.color)
        return Piece(piece_type, color, has_moved=False)  # has_moved tracked separately

    @property
    def board(self) -> List[List[Optional[Piece]]]:
        """Get 8x8 board representation for compatibility"""
        result = [[None for _ in range(8)] for _ in range(8)]
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece:
                    result[row][col] = piece
        return result

    @property
    def current_turn(self) -> Color:
        """Get current turn"""
        return Color.WHITE if self._board.turn == chess.WHITE else Color.BLACK

    @property
    def move_number(self) -> int:
        """Get current move number"""
        return self._board.fullmove_number

    @property
    def halfmove_clock(self) -> int:
        """Get halfmove clock (for 50-move rule)"""
        return self._board.halfmove_clock

    @property
    def fullmove_number(self) -> int:
        """Get fullmove number"""
        return self._board.fullmove_number

    @property
    def castling_rights(self) -> CastlingRights:
        """Get castling rights"""
        rights = CastlingRights()
        rights.white_kingside = self._board.has_kingside_castling_rights(chess.WHITE)
        rights.white_queenside = self._board.has_queenside_castling_rights(chess.WHITE)
        rights.black_kingside = self._board.has_kingside_castling_rights(chess.BLACK)
        rights.black_queenside = self._board.has_queenside_castling_rights(chess.BLACK)
        return rights

    @property
    def en_passant_target(self) -> Optional[Tuple[int, int]]:
        """Get en passant target square"""
        if self._board.ep_square is not None:
            return self._square_to_pos(self._board.ep_square)
        return None

    @property
    def position_history(self) -> List[str]:
        """Get position history for threefold repetition"""
        # Not directly exposed by python-chess, return empty for now
        return []

    def setup_initial_position(self) -> None:
        """Set up the standard chess starting position"""
        self._board = chess.Board()
        self._update_game_status()
        self.move_history = []
        self.last_move = None

    def reset_to_initial_position(self) -> None:
        """Reset the entire game state to the initial starting position"""
        self._board = chess.Board()
        self._update_game_status()
        self.move_history = []
        self.last_move = None
        self.undo_stack = []
        self.redo_stack = []

    def get_piece(self, row: int, col: int) -> Optional[Piece]:
        """Get piece at a specific position"""
        if not (0 <= row < 8 and 0 <= col < 8):
            return None

        square = self._pos_to_square(row, col)
        chess_piece = self._board.piece_at(square)
        if chess_piece is None:
            return None

        return self._chess_piece_to_ours(chess_piece)

    def set_piece(self, row: int, col: int, piece: Optional[Piece]) -> None:
        """Set piece at a specific position"""
        if not (0 <= row < 8 and 0 <= col < 8):
            return

        square = self._pos_to_square(row, col)
        if piece is None:
            self._board.remove_piece_at(square)
        else:
            chess_piece_type = self._piece_type_to_chess(piece.type)
            chess_color = self._color_to_chess(piece.color)
            chess_piece = chess.Piece(chess_piece_type, chess_color)
            self._board.set_piece_at(square, chess_piece)

    def get_king_position(self, color: Color) -> Optional[Tuple[int, int]]:
        """Find the king of a specific color"""
        chess_color = self._color_to_chess(color)
        king_square = self._board.king(chess_color)
        if king_square is None:
            return None
        return self._square_to_pos(king_square)

    def is_square_attacked(self, row: int, col: int, by_color: Color) -> bool:
        """Check if a square is attacked by pieces of a specific color."""
        square = self._pos_to_square(row, col)
        chess_color = self._color_to_chess(by_color)
        return self._board.is_attacked_by(chess_color, square)

    def is_king_in_check(self, color: Color) -> bool:
        """Check if the king of a specific color is in check"""
        # Temporarily set the turn to check if that color's king is in check
        original_turn = self._board.turn
        self._board.turn = self._color_to_chess(color)
        in_check = self._board.is_check()
        self._board.turn = original_turn
        return in_check

    def can_castle(self, color: Color, kingside: bool) -> bool:
        """Check if castling is possible"""
        chess_color = self._color_to_chess(color)

        # Check castling rights
        if kingside:
            if not self._board.has_kingside_castling_rights(chess_color):
                return False
        else:
            if not self._board.has_queenside_castling_rights(chess_color):
                return False

        # Generate legal moves and check if castling move exists
        for move in self._board.legal_moves:
            if self._board.is_castling(move):
                move_from = self._square_to_pos(move.from_square)
                move_to = self._square_to_pos(move.to_square)

                # Check if this is the castling we're looking for
                king_pos = self.get_king_position(color)
                if king_pos and move_from == king_pos:
                    # Kingside: king moves to g-file (col 6)
                    # Queenside: king moves to c-file (col 2)
                    if kingside and move_to[1] == 6:
                        return True
                    elif not kingside and move_to[1] == 2:
                        return True

        return False

    def get_hanging_pieces(self, color: Color) -> List[Tuple[int, int]]:
        """Get list of hanging pieces for the given color."""
        hanging_pieces = []

        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color:
                    if self._is_piece_hanging_simple(row, col):
                        hanging_pieces.append((row, col))

        return hanging_pieces

    def _is_piece_hanging_simple(self, row: int, col: int) -> bool:
        """Simple check: is piece attacked but not defended?"""
        piece = self.get_piece(row, col)
        if not piece:
            return False

        enemy_color = Color.BLACK if piece.color == Color.WHITE else Color.WHITE

        # Step 1: Is it attacked by an enemy?
        if not self.is_square_attacked(row, col, enemy_color):
            return False

        # Step 2: Is it defended by a friendly piece?
        if self.is_square_attacked(row, col, piece.color):
            return False  # It's defended, so not hanging

        return True  # Attacked but not defended = hanging

    def _get_attackers(self, target_row: int, target_col: int, attacker_color: Color) -> List[Tuple[int, int]]:
        """Get all pieces of the given color that attack the target square"""
        attackers = []
        square = self._pos_to_square(target_row, target_col)

        # Check all pieces of the attacker color
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == attacker_color:
                    from_square = self._pos_to_square(row, col)
                    # Check if this specific piece attacks the target square
                    piece_attacks = self._board.attacks(from_square)
                    if square in piece_attacks:
                        attackers.append((row, col))

        return attackers

    def get_tactically_interesting_squares(self) -> List[Tuple[int, int]]:
        """Get all squares that have tactical potential for exchange evaluation."""
        interesting_squares = []

        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece is not None:
                    # Check if this square is attacked
                    enemy_color = Color.BLACK if piece.color == Color.WHITE else Color.WHITE
                    if self.is_square_attacked(row, col, enemy_color):
                        interesting_squares.append((row, col))

        return interesting_squares

    def _compute_attackers_defenders(self, target_row: int, target_col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Compute attackers and defenders"""
        target_piece = self.get_piece(target_row, target_col)

        if target_piece is None:
            # Empty square - anyone can attack it, but no one defends it
            white_attackers = self._get_attackers(target_row, target_col, Color.WHITE)
            black_attackers = self._get_attackers(target_row, target_col, Color.BLACK)
            return (white_attackers + black_attackers, [])

        # Square contains a piece - figure out who attacks and who defends
        target_color = target_piece.color

        # Attackers are enemy pieces that can capture the target
        if target_color == Color.WHITE:
            attackers = self._get_attackers(target_row, target_col, Color.BLACK)
            # Defenders: friendly pieces that could recapture if this piece is taken
            defenders = self._get_attackers_if_empty(target_row, target_col, Color.WHITE)
        else:
            attackers = self._get_attackers(target_row, target_col, Color.WHITE)
            # Defenders: friendly pieces that could recapture if this piece is taken
            defenders = self._get_attackers_if_empty(target_row, target_col, Color.BLACK)

        # Remove the target piece itself from defenders (a piece can't defend itself)
        defenders = [pos for pos in defenders if pos != (target_row, target_col)]

        return (attackers, defenders)

    def _get_attackers_if_empty(self, target_row: int, target_col: int, attacker_color: Color) -> List[Tuple[int, int]]:
        """Get all pieces that could attack this square if it were empty (for defender calculation)"""
        # Save current board state
        fen = self._board.fen()

        # Temporarily remove the piece
        square = self._pos_to_square(target_row, target_col)
        original_piece = self._board.piece_at(square)
        self._board.remove_piece_at(square)

        # Get attackers
        attackers = self._get_attackers(target_row, target_col, attacker_color)

        # Restore board state
        if original_piece:
            self._board.set_piece_at(square, original_piece)

        return attackers

    def get_all_attackers_and_defenders(self, target_row: int, target_col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Get all pieces that can attack or defend a given square."""
        return self._compute_attackers_defenders(target_row, target_col)

    def _get_piece_attacks(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get all squares this piece attacks (not filtered by check legality)"""
        square = self._pos_to_square(row, col)
        attacks = self._board.attacks(square)

        result = []
        for attacked_square in attacks:
            attacked_pos = self._square_to_pos(attacked_square)
            result.append(attacked_pos)

        return result

    def get_fen_position(self) -> str:
        """Generate FEN (Forsyth-Edwards Notation) string for the current position"""
        return self._board.fen()

    def calculate_activity(self, color: Color) -> int:
        """Calculate total squares reachable by all pieces of a color (excluding pawns)"""
        reachable_squares = set()

        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color and piece.type != PieceType.PAWN:
                    # Get pseudo-legal moves (basic piece movement)
                    moves = self._get_piece_pseudo_moves(row, col, piece)
                    for move_row, move_col in moves:
                        reachable_squares.add((move_row, move_col))

        return len(reachable_squares)

    def _get_piece_pseudo_moves(self, row: int, col: int, piece: Piece) -> List[Tuple[int, int]]:
        """Get pseudo-legal moves for a piece (basic movement rules only)"""
        square = self._pos_to_square(row, col)
        attacks = self._board.attacks(square)

        result = []
        for attacked_square in attacks:
            attacked_pos = self._square_to_pos(attacked_square)
            result.append(attacked_pos)

        return result

    def get_activity_scores(self) -> Tuple[int, int]:
        """Get activity scores for both colors. Returns (white_activity, black_activity)"""
        white_activity = self.calculate_activity(Color.WHITE)
        black_activity = self.calculate_activity(Color.BLACK)
        return (white_activity, black_activity)

    def count_pawns(self, color: Color) -> int:
        """Count the number of pawns for a given color"""
        pawn_count = 0
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color and piece.type == PieceType.PAWN:
                    pawn_count += 1
        return pawn_count

    def get_pawn_counts(self) -> Tuple[int, int]:
        """Get pawn counts for both colors. Returns (white_pawns, black_pawns)"""
        white_pawns = self.count_pawns(Color.WHITE)
        black_pawns = self.count_pawns(Color.BLACK)
        return (white_pawns, black_pawns)

    def count_backward_pawns(self, color: Color) -> int:
        """Count backward pawns - pawns that cannot be defended by other pawns and cannot safely advance"""
        backward_count = 0
        enemy_color = Color.BLACK if color == Color.WHITE else Color.WHITE

        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color and piece.type == PieceType.PAWN:
                    # Direction pawns move (white up, black down)
                    pawn_direction = -1 if color == Color.WHITE else 1

                    # Check if this pawn can be defended by other pawns
                    can_be_defended = False

                    # Check diagonally behind for potential defending pawns
                    defend_row = row + pawn_direction
                    if 0 <= defend_row < 8:
                        # Check left diagonal
                        if col > 0:
                            defender = self.get_piece(defend_row, col - 1)
                            if defender and defender.color == color and defender.type == PieceType.PAWN:
                                can_be_defended = True
                        # Check right diagonal
                        if col < 7:
                            defender = self.get_piece(defend_row, col + 1)
                            if defender and defender.color == color and defender.type == PieceType.PAWN:
                                can_be_defended = True

                    # Also check if adjacent pawns could potentially advance to defend
                    if not can_be_defended:
                        # Check if pawns on adjacent files could advance to defend this pawn
                        for adjacent_col in [col - 1, col + 1]:
                            if 0 <= adjacent_col < 8:
                                # Look for friendly pawns on this adjacent file that could advance
                                for check_row in range(8):
                                    adjacent_piece = self.get_piece(check_row, adjacent_col)
                                    if adjacent_piece and adjacent_piece.color == color and adjacent_piece.type == PieceType.PAWN:
                                        # Check if this pawn could potentially advance to defend
                                        # (simplified: if it's behind our pawn, it could potentially advance)
                                        if (color == Color.WHITE and check_row > row) or (color == Color.BLACK and check_row < row):
                                            can_be_defended = True
                                            break
                                if can_be_defended:
                                    break

                    # Check if the pawn can safely advance
                    can_safely_advance = True
                    advance_row = row + pawn_direction
                    if 0 <= advance_row < 8:
                        # Check if the square in front is controlled by enemy pawns
                        for enemy_col in [col - 1, col + 1]:
                            if 0 <= enemy_col < 8:
                                enemy_attack_row = advance_row + pawn_direction  # Where enemy pawn would be to attack
                                if 0 <= enemy_attack_row < 8:
                                    enemy_piece = self.get_piece(enemy_attack_row, enemy_col)
                                    if enemy_piece and enemy_piece.color == enemy_color and enemy_piece.type == PieceType.PAWN:
                                        can_safely_advance = False
                                        break

                    # A pawn is backward if it cannot be defended and cannot safely advance
                    if not can_be_defended and not can_safely_advance:
                        backward_count += 1

        return backward_count

    def count_isolated_pawns(self, color: Color) -> int:
        """Count pawns with no friendly pawns on adjacent files (isolated pawns)"""
        isolated_count = 0
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color and piece.type == PieceType.PAWN:
                    # Check if there are friendly pawns on adjacent files
                    has_adjacent_pawn = False

                    # Check left file (col-1)
                    if col > 0:
                        for check_row in range(8):
                            adjacent_piece = self.get_piece(check_row, col - 1)
                            if adjacent_piece and adjacent_piece.color == color and adjacent_piece.type == PieceType.PAWN:
                                has_adjacent_pawn = True
                                break

                    # Check right file (col+1)
                    if col < 7 and not has_adjacent_pawn:
                        for check_row in range(8):
                            adjacent_piece = self.get_piece(check_row, col + 1)
                            if adjacent_piece and adjacent_piece.color == color and adjacent_piece.type == PieceType.PAWN:
                                has_adjacent_pawn = True
                                break

                    if not has_adjacent_pawn:
                        isolated_count += 1
        return isolated_count

    def count_doubled_pawns(self, color: Color) -> int:
        """Count pawns that are doubled (more than one pawn on the same file)"""
        doubled_count = 0

        # Count pawns per file
        for col in range(8):
            pawns_on_file = 0
            for row in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color and piece.type == PieceType.PAWN:
                    pawns_on_file += 1

            # If more than one pawn on this file, count the extras as doubled
            if pawns_on_file > 1:
                doubled_count += pawns_on_file - 1

        return doubled_count

    def count_passed_pawns(self, color: Color) -> int:
        """Count passed pawns - pawns with no opponent pawns blocking their path to promotion"""
        passed_count = 0
        enemy_color = Color.BLACK if color == Color.WHITE else Color.WHITE

        # Define the direction the pawn moves for promotion
        if color == Color.WHITE:
            promotion_direction = -1  # White pawns move toward row 0
            start_row_check = 6       # Don't count pawns on the 7th rank (about to promote anyway)
        else:
            promotion_direction = 1   # Black pawns move toward row 7
            start_row_check = 1       # Don't count pawns on the 2nd rank

        # Check each pawn
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color and piece.type == PieceType.PAWN:
                    # Skip pawns very close to promotion (they're obviously passed)
                    if (color == Color.WHITE and row <= start_row_check) or (color == Color.BLACK and row >= start_row_check):

                        # Check if this pawn is passed
                        is_passed = True

                        # Check the path to promotion on this file and adjacent files
                        for check_col in [col - 1, col, col + 1]:
                            if 0 <= check_col <= 7:  # Valid column
                                # Check all squares from current position to promotion rank
                                check_row = row + promotion_direction
                                while 0 <= check_row <= 7:
                                    enemy_piece = self.get_piece(check_row, check_col)
                                    if enemy_piece and enemy_piece.color == enemy_color and enemy_piece.type == PieceType.PAWN:
                                        is_passed = False
                                        break
                                    check_row += promotion_direction

                                if not is_passed:
                                    break

                        if is_passed:
                            passed_count += 1

        return passed_count

    def get_pawn_statistics(self) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
        """Get pawn statistics for both colors. Returns ((white_backward, white_isolated, white_doubled, white_passed), (black_backward, black_isolated, black_doubled, black_passed))"""
        white_stats = (
            self.count_backward_pawns(Color.WHITE),
            self.count_isolated_pawns(Color.WHITE),
            self.count_doubled_pawns(Color.WHITE),
            self.count_passed_pawns(Color.WHITE)
        )
        black_stats = (
            self.count_backward_pawns(Color.BLACK),
            self.count_isolated_pawns(Color.BLACK),
            self.count_doubled_pawns(Color.BLACK),
            self.count_passed_pawns(Color.BLACK)
        )
        return (white_stats, black_stats)

    def copy(self) -> 'BoardState':
        """Create a deep copy of the board state"""
        new_state = BoardState()
        new_state._board = self._board.copy()
        new_state.is_check = self.is_check
        new_state.is_in_checkmate = self.is_in_checkmate
        new_state.is_in_stalemate = self.is_in_stalemate
        new_state.game_phase = self.game_phase
        new_state.move_history = copy.deepcopy(self.move_history)
        new_state.last_move = self.last_move
        new_state.undo_stack = []  # Don't copy undo/redo stacks
        new_state.redo_stack = []
        return new_state

    def __str__(self) -> str:
        """String representation of the board"""
        result = "  a b c d e f g h\n"
        for row in range(8):
            result += f"{8-row} "
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece:
                    result += str(piece) + " "
                else:
                    result += ". "
            result += f"{8-row}\n"
        result += "  a b c d e f g h\n"
        return result

    def load_pgn_file(self, filename: str) -> bool:
        """Load a PGN file and apply the first game to the board"""
        try:
            from pgn_manager import PGNManager
            games = PGNManager.load_pgn_file(filename)
            if games:
                return PGNManager.apply_pgn_game_to_board(self, games[0])
            return False
        except ImportError:
            print("PGN functionality not available")
            return False
        except Exception as e:
            print(f"Failed to load PGN file: {e}")
            return False

    def save_pgn_file(self, filename: str, white_player: str = "Player", black_player: str = "Opponent", event: str = "Casual Game") -> bool:
        """Save current game state to a PGN file"""
        try:
            from pgn_manager import PGNManager, PGNGame
            game = PGNManager.create_game_from_board_state(self, white_player, black_player, event)
            PGNManager.save_pgn_file(filename, [game])
            return True
        except ImportError:
            print("PGN functionality not available")
            return False
        except Exception as e:
            print(f"Failed to save PGN file: {e}")
            return False

    def export_current_game_pgn(self, white_player: str = "Player", black_player: str = "Opponent", event: str = "Casual Game") -> str:
        """Export current game state as PGN string"""
        try:
            from pgn_manager import PGNManager
            game = PGNManager.create_game_from_board_state(self, white_player, black_player, event)
            return game.to_pgn()
        except ImportError:
            return "PGN functionality not available"
        except Exception as e:
            return f"Failed to export PGN: {e}"

    def get_possible_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get all legal moves for a piece at the given position"""
        piece = self.get_piece(row, col)
        if not piece:
            return []

        # Only get moves for pieces of the current turn
        if piece.color != self.current_turn:
            return []

        from_square = self._pos_to_square(row, col)
        legal_moves = []

        for move in self._board.legal_moves:
            if move.from_square == from_square:
                to_pos = self._square_to_pos(move.to_square)
                legal_moves.append(to_pos)

        return legal_moves

    def make_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Execute a move if it's legal. Returns True if move was successful."""
        # Get the piece to move
        piece = self.get_piece(from_row, from_col)
        if not piece:
            return False

        # Verify it's the correct player's turn
        if piece.color != self.current_turn:
            return False

        # Find the matching legal move
        from_square = self._pos_to_square(from_row, from_col)
        to_square = self._pos_to_square(to_row, to_col)

        chess_move = None
        for move in self._board.legal_moves:
            if move.from_square == from_square and move.to_square == to_square:
                # Handle pawn promotion - default to queen if not specified
                if move.promotion:
                    if move.promotion == chess.QUEEN:
                        chess_move = move
                        break
                else:
                    chess_move = move
                    break

        if chess_move is None:
            return False

        # Save state for undo before making the move
        self._save_state_for_undo()

        # Execute the move
        self._board.push(chess_move)

        # Update last move for highlighting
        self.last_move = ((from_row, from_col), (to_row, to_col))

        # Update game status
        self._update_game_status()

        # Store move in history
        captured_piece = None  # python-chess handles this internally
        move_obj = Move(
            from_square=(from_row, from_col),
            to_square=(to_row, to_col),
            piece=piece,
            captured_piece=captured_piece,
            move_number=self.fullmove_number
        )
        self.move_history.append(move_obj)

        return True

    def make_move_with_promotion(self, from_row: int, from_col: int, to_row: int, to_col: int,
                                promotion_piece: PieceType = PieceType.QUEEN) -> bool:
        """Execute a move with optional pawn promotion. Returns True if move was successful."""
        # Get the piece to move
        piece = self.get_piece(from_row, from_col)
        if not piece:
            return False

        # Verify it's the correct player's turn
        if piece.color != self.current_turn:
            return False

        # Find the matching legal move
        from_square = self._pos_to_square(from_row, from_col)
        to_square = self._pos_to_square(to_row, to_col)

        chess_promotion = self._piece_type_to_chess(promotion_piece) if promotion_piece else None

        chess_move = None
        for move in self._board.legal_moves:
            if move.from_square == from_square and move.to_square == to_square:
                if move.promotion:
                    if chess_promotion and move.promotion == chess_promotion:
                        chess_move = move
                        break
                else:
                    chess_move = move
                    break

        if chess_move is None:
            return False

        # Save state for undo before making the move
        self._save_state_for_undo()

        # Execute the move
        self._board.push(chess_move)

        # Update last move for highlighting
        self.last_move = ((from_row, from_col), (to_row, to_col))

        # Update game status
        self._update_game_status()

        # Store move in history
        captured_piece = None
        is_promotion = chess_move.promotion is not None
        move_obj = Move(
            from_square=(from_row, from_col),
            to_square=(to_row, to_col),
            piece=piece,
            captured_piece=captured_piece,
            promotion=promotion_piece if is_promotion else None,
            move_number=self.fullmove_number
        )
        self.move_history.append(move_obj)

        return True

    def is_pawn_promotion(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Check if a move would result in pawn promotion"""
        piece = self.get_piece(from_row, from_col)
        if not piece or piece.type != PieceType.PAWN:
            return False

        # Check if pawn reaches the final rank
        if piece.color == Color.WHITE and to_row == 0:
            return True
        elif piece.color == Color.BLACK and to_row == 7:
            return True

        return False

    def is_checkmate(self, color: Color) -> bool:
        """Check if the specified color is in checkmate"""
        # Set turn to the color we're checking
        original_turn = self._board.turn
        self._board.turn = self._color_to_chess(color)

        is_mate = self._board.is_checkmate()

        # Restore original turn
        self._board.turn = original_turn
        return is_mate

    def is_stalemate(self, color: Color) -> bool:
        """Check if the specified color is in stalemate (no legal moves but not in check)"""
        # Set turn to the color we're checking
        original_turn = self._board.turn
        self._board.turn = self._color_to_chess(color)

        is_stale = self._board.is_stalemate()

        # Restore original turn
        self._board.turn = original_turn
        return is_stale

    def _update_game_status(self) -> None:
        """Update is_check, is_in_checkmate, is_in_stalemate"""
        self.is_check = self._board.is_check()
        self.is_in_checkmate = self._board.is_checkmate()
        self.is_in_stalemate = self._board.is_stalemate()

    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return len(self.redo_stack) > 0

    def _save_state_for_undo(self) -> None:
        """Save current board state to undo stack and clear redo stack"""
        # Save board copy, move history, and last_move
        state_tuple = (self._board.copy(), copy.deepcopy(self.move_history), self.last_move)
        self.undo_stack.append(state_tuple)

        # Clear redo stack since we're making a new move
        self.redo_stack.clear()

    def undo_move(self) -> bool:
        """Undo the last move. Returns True if successful."""
        if not self.can_undo():
            return False

        # Save current state to redo stack
        current_state = (self._board.copy(), copy.deepcopy(self.move_history), self.last_move)
        self.redo_stack.append(current_state)

        # Restore previous state from undo stack
        previous_board, previous_history, previous_last_move = self.undo_stack.pop()

        self._board = previous_board.copy()
        self.move_history = previous_history
        self.last_move = previous_last_move

        # Update game status
        self._update_game_status()

        return True

    def redo_move(self) -> bool:
        """Redo the last undone move. Returns True if successful."""
        if not self.can_redo():
            return False

        # Save current state to undo stack
        current_state = (self._board.copy(), copy.deepcopy(self.move_history), self.last_move)
        self.undo_stack.append(current_state)

        # Restore next state from redo stack
        next_board, next_history, next_last_move = self.redo_stack.pop()

        self._board = next_board.copy()
        self.move_history = next_history
        self.last_move = next_last_move

        # Update game status
        self._update_game_status()

        return True

# Example usage and testing
if __name__ == "__main__":
    # Create a new board state
    board = BoardState()

    print("Initial Chess Position:")
    print(board)
    print(f"FEN: {board.get_fen_position()}")
    print(f"Current turn: {board.current_turn.value}")
    print(f"Castling rights - White: K={board.castling_rights.white_kingside}, Q={board.castling_rights.white_queenside}")
    print(f"Castling rights - Black: k={board.castling_rights.black_kingside}, q={board.castling_rights.black_queenside}")
    print(f"En passant target: {board.en_passant_target}")
    print(f"Halfmove clock: {board.halfmove_clock}")
    print(f"Fullmove number: {board.fullmove_number}")
