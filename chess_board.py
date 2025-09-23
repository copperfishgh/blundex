"""
Chess Board State Data Structure

This module defines a comprehensive chess board state that tracks:
- Current piece positions
- Castling rights (kingside/queenside for both colors)
- En passant target square
- Move history and counters
- Game state information (turn, check status, etc.)
"""

from typing import Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
import copy

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
    Comprehensive chess board state that tracks all game information
    """
    # Current board position (8x8 grid)
    board: List[List[Optional[Piece]]] = field(default_factory=lambda: [[None for _ in range(8)] for _ in range(8)])
    
    # Game state
    current_turn: Color = Color.WHITE
    move_number: int = 1
    halfmove_clock: int = 0  # For 50-move rule
    fullmove_number: int = 1
    
    # Castling rights
    castling_rights: CastlingRights = field(default_factory=CastlingRights)
    
    # En passant target square (None if no en passant possible)
    en_passant_target: Optional[Tuple[int, int]] = None
    
    # Game status
    is_check: bool = False
    is_in_checkmate: bool = False
    is_in_stalemate: bool = False
    game_phase: GamePhase = GamePhase.OPENING
    
    # Move history
    move_history: List[Move] = field(default_factory=list)

    # Last move for highlighting (None if no moves made yet)
    last_move: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None  # ((from_row, from_col), (to_row, to_col))

    # Position repetition tracking (for threefold repetition rule)
    position_history: List[str] = field(default_factory=list)

    # Undo/Redo functionality
    undo_stack: List['BoardState'] = field(default_factory=list)
    redo_stack: List['BoardState'] = field(default_factory=list)

    # Cached hanging pieces (updated only when board changes)
    _cached_hanging_pieces_white: List[Tuple[int, int]] = field(default_factory=list)
    _cached_hanging_pieces_black: List[Tuple[int, int]] = field(default_factory=list)
    _hanging_pieces_cache_valid: bool = False

    # Cached exchange evaluation data (updated only when board changes)
    _cached_interesting_squares: List[Tuple[int, int]] = field(default_factory=list)
    _cached_attackers_defenders: dict = field(default_factory=dict)  # {(row,col): (attackers, defenders)}
    _exchange_cache_valid: bool = False
    
    def __post_init__(self):
        """Initialize the board with starting position"""
        if not any(any(row) for row in self.board):  # If board is empty
            self.setup_initial_position()
    
    def setup_initial_position(self) -> None:
        """Set up the standard chess starting position"""
        # Clear the board
        self.board = [[None for _ in range(8)] for _ in range(8)]
        
        # Place black pieces (rows 0-1)
        piece_order = [PieceType.ROOK, PieceType.KNIGHT, PieceType.BISHOP, PieceType.QUEEN,
                      PieceType.KING, PieceType.BISHOP, PieceType.KNIGHT, PieceType.ROOK]
        
        # Black back rank
        for col, piece_type in enumerate(piece_order):
            self.board[0][col] = Piece(piece_type, Color.BLACK)
        
        # Black pawns
        for col in range(8):
            self.board[1][col] = Piece(PieceType.PAWN, Color.BLACK)
        
        # Place white pieces (rows 6-7)
        # White pawns
        for col in range(8):
            self.board[6][col] = Piece(PieceType.PAWN, Color.WHITE)
        
        # White back rank
        for col, piece_type in enumerate(piece_order):
            self.board[7][col] = Piece(piece_type, Color.WHITE)

    def reset_to_initial_position(self) -> None:
        """Reset the entire game state to the initial starting position"""
        # Reset board to starting position
        self.setup_initial_position()

        # Reset all game state variables
        self.current_turn = Color.WHITE
        self.move_number = 1
        self.halfmove_clock = 0
        self.fullmove_number = 1

        # Reset castling rights
        self.castling_rights = CastlingRights()

        # Reset en passant
        self.en_passant_target = None

        # Reset game status
        self.is_check = False
        self.is_in_checkmate = False
        self.is_in_stalemate = False
        self.game_phase = GamePhase.OPENING

        # Clear move history
        self.move_history = []
        self.last_move = None
        self.position_history = []

        # Clear undo/redo stacks
        self.undo_stack = []
        self.redo_stack = []

        # Invalidate hanging pieces cache
        self._cached_hanging_pieces_white = []
        self._cached_hanging_pieces_black = []
        self._hanging_pieces_cache_valid = False

        # Invalidate exchange evaluation cache
        self._cached_interesting_squares = []
        self._cached_attackers_defenders = {}
        self._exchange_cache_valid = False

    def get_piece(self, row: int, col: int) -> Optional[Piece]:
        """Get piece at a specific position"""
        if 0 <= row < 8 and 0 <= col < 8:
            return self.board[row][col]
        return None
    
    def set_piece(self, row: int, col: int, piece: Optional[Piece]) -> None:
        """Set piece at a specific position"""
        if 0 <= row < 8 and 0 <= col < 8:
            self.board[row][col] = piece
    
    def get_king_position(self, color: Color) -> Optional[Tuple[int, int]]:
        """Find the king of a specific color"""
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.type == PieceType.KING and piece.color == color:
                    return (row, col)
        return None
    
    def is_square_attacked(self, row: int, col: int, by_color: Color) -> bool:
        """Check if a square is attacked by pieces of a specific color."""

        # Check for pawn attacks
        # White pawns attack from row+1 (lower rank), black pawns attack from row-1 (higher rank)
        if by_color == Color.WHITE:
            attack_row = row + 1  # White pawns attack from below
        else:
            attack_row = row - 1  # Black pawns attack from above

        for dc in [-1, 1]:
            attack_col = col + dc
            if self._is_valid_square(attack_row, attack_col):
                piece = self.get_piece(attack_row, attack_col)
                if piece and piece.type == PieceType.PAWN and piece.color == by_color:
                    return True

        # Check for king attacks
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                attack_row, attack_col = row + dr, col + dc
                if self._is_valid_square(attack_row, attack_col):
                    piece = self.get_piece(attack_row, attack_col)
                    if piece and piece.type == PieceType.KING and piece.color == by_color:
                        return True

        # Check for knight attacks
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, dc in knight_moves:
            attack_row, attack_col = row + dr, col + dc
            if self._is_valid_square(attack_row, attack_col):
                piece = self.get_piece(attack_row, attack_col)
                if piece and piece.type == PieceType.KNIGHT and piece.color == by_color:
                    return True

        # Check for rook/queen attacks (horizontal and vertical)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for dr, dc in directions:
            for i in range(1, 8):
                attack_row, attack_col = row + i * dr, col + i * dc
                if not self._is_valid_square(attack_row, attack_col):
                    break
                piece = self.get_piece(attack_row, attack_col)
                if piece:
                    if piece.color == by_color and (piece.type == PieceType.ROOK or piece.type == PieceType.QUEEN):
                        return True
                    break  # Piece blocks further attacks in this direction

        # Check for bishop/queen attacks (diagonal)
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dr, dc in directions:
            for i in range(1, 8):
                attack_row, attack_col = row + i * dr, col + i * dc
                if not self._is_valid_square(attack_row, attack_col):
                    break
                piece = self.get_piece(attack_row, attack_col)
                if piece:
                    if piece.color == by_color and (piece.type == PieceType.BISHOP or piece.type == PieceType.QUEEN):
                        return True
                    break  # Piece blocks further attacks in this direction

        return False
    
    def is_king_in_check(self, color: Color) -> bool:
        """Check if the king of a specific color is in check"""
        king_pos = self.get_king_position(color)
        if not king_pos:
            return False
        return self.is_square_attacked(king_pos[0], king_pos[1], Color.BLACK if color == Color.WHITE else Color.WHITE)
    
    def can_castle(self, color: Color, kingside: bool) -> bool:
        """Check if castling is possible"""
        if not self.castling_rights.can_castle(color, kingside):
            return False
        
        if self.is_king_in_check(color):
            return False
        
        # Check if squares between king and rook are empty and not attacked
        king_row = 0 if color == Color.BLACK else 7
        if kingside:
            # Check squares f1/g1 for white, f8/g8 for black
            for col in [5, 6]:
                if self.board[king_row][col] is not None:
                    return False
                if self.is_square_attacked(king_row, col, Color.BLACK if color == Color.WHITE else Color.WHITE):
                    return False
        else:
            # Check squares b1/c1/d1 for white, b8/c8/d8 for black
            for col in [1, 2, 3]:
                if self.board[king_row][col] is not None:
                    return False
                if self.is_square_attacked(king_row, col, Color.BLACK if color == Color.WHITE else Color.WHITE):
                    return False
        
        return True

    def get_hanging_pieces(self, color: Color) -> List[Tuple[int, int]]:
        """Get list of hanging pieces for the given color. Uses caching for performance."""
        if not self._hanging_pieces_cache_valid:
            self._update_hanging_pieces_cache()

        if color == Color.WHITE:
            return self._cached_hanging_pieces_white.copy()
        else:
            return self._cached_hanging_pieces_black.copy()

    def _update_hanging_pieces_cache(self) -> None:
        """Update the cached hanging pieces for both colors"""
        self._cached_hanging_pieces_white = []
        self._cached_hanging_pieces_black = []

        # Check all pieces on the board
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece:
                    if self._is_piece_hanging_simple(row, col):
                        if piece.color == Color.WHITE:
                            self._cached_hanging_pieces_white.append((row, col))
                        else:
                            self._cached_hanging_pieces_black.append((row, col))

        self._hanging_pieces_cache_valid = True

    def _invalidate_hanging_pieces_cache(self) -> None:
        """Invalidate the hanging pieces cache (call when board changes)"""
        self._hanging_pieces_cache_valid = False
        # Also invalidate exchange evaluation cache since they depend on similar data
        self._exchange_cache_valid = False

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

        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == attacker_color:
                    # Check if this piece can attack the target square
                    possible_moves = self._get_piece_attacks(row, col)
                    if (target_row, target_col) in possible_moves:
                        attackers.append((row, col))

        return attackers


    def get_tactically_interesting_squares(self) -> List[Tuple[int, int]]:
        """
        Get all squares that have tactical potential for exchange evaluation.
        Returns cached results for performance.
        """
        if not self._exchange_cache_valid:
            self._update_exchange_cache()
        return self._cached_interesting_squares.copy()

    def _update_exchange_cache(self) -> None:
        """Update the cached exchange evaluation data"""
        self._cached_interesting_squares = []
        self._cached_attackers_defenders = {}

        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece is not None:
                    # Only compute for squares that have pieces
                    attackers, defenders = self._compute_attackers_defenders(row, col)
                    self._cached_attackers_defenders[(row, col)] = (attackers, defenders)

                    # Check if this square is tactically interesting
                    if len(attackers) > 0:
                        self._cached_interesting_squares.append((row, col))

        self._exchange_cache_valid = True

    def _compute_attackers_defenders(self, target_row: int, target_col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Compute attackers and defenders without caching (internal use)"""
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
        # Temporarily remove the piece, find attackers, then restore
        original_piece = self.get_piece(target_row, target_col)
        self.set_piece(target_row, target_col, None)  # Temporarily empty the square

        attackers = self._get_attackers(target_row, target_col, attacker_color)

        self.set_piece(target_row, target_col, original_piece)  # Restore original piece
        return attackers

    def get_all_attackers_and_defenders(self, target_row: int, target_col: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Get all pieces that can attack or defend a given square.
        Returns cached results for performance.
        """
        if not self._exchange_cache_valid:
            self._update_exchange_cache()

        return self._cached_attackers_defenders.get((target_row, target_col), ([], []))

    def _get_piece_attacks(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get all squares this piece attacks (not filtered by check legality)"""
        piece = self.get_piece(row, col)
        if not piece:
            return []

        if piece.type == PieceType.PAWN:
            return self._get_pawn_attacks(row, col, piece.color)
        elif piece.type == PieceType.ROOK:
            return self._get_rook_moves(row, col, piece.color)
        elif piece.type == PieceType.KNIGHT:
            return self._get_knight_moves(row, col, piece.color)
        elif piece.type == PieceType.BISHOP:
            return self._get_bishop_moves(row, col, piece.color)
        elif piece.type == PieceType.QUEEN:
            return self._get_queen_moves(row, col, piece.color)
        elif piece.type == PieceType.KING:
            return self._get_king_attacks(row, col, piece.color)

        return []

    def _get_pawn_attacks(self, row: int, col: int, color: Color) -> List[Tuple[int, int]]:
        """Get squares a pawn attacks (diagonal captures only)"""
        attacks = []
        direction = -1 if color == Color.WHITE else 1

        # Check diagonal attacks
        for dc in [-1, 1]:
            attack_row = row + direction
            attack_col = col + dc
            if self._is_valid_square(attack_row, attack_col):
                attacks.append((attack_row, attack_col))

        return attacks

    def _get_king_attacks(self, row: int, col: int, color: Color) -> List[Tuple[int, int]]:
        """Get squares a king attacks (excludes castling)"""
        attacks = []
        king_moves = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in king_moves:
            new_row, new_col = row + dr, col + dc
            if self._is_valid_square(new_row, new_col):
                attacks.append((new_row, new_col))

        return attacks

    def _get_piece_value(self, row: int, col: int) -> int:
        """Get the standard chess piece value"""
        piece = self.get_piece(row, col)
        if not piece:
            return 0

        values = {
            PieceType.PAWN: 1,
            PieceType.KNIGHT: 3,
            PieceType.BISHOP: 3,
            PieceType.ROOK: 5,
            PieceType.QUEEN: 9,
            PieceType.KING: 100  # King is invaluable
        }

        return values.get(piece.type, 0)

    def get_fen_position(self) -> str:
        """Generate FEN (Forsyth-Edwards Notation) string for the current position"""
        fen_parts = []
        
        # Board position
        for row in self.board:
            empty_count = 0
            row_str = ""
            for piece in row:
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    row_str += str(piece)
            if empty_count > 0:
                row_str += str(empty_count)
            fen_parts.append(row_str)
        
        board_fen = "/".join(fen_parts)
        
        # Active color
        active_color = "w" if self.current_turn == Color.WHITE else "b"
        
        # Castling rights
        castling = ""
        if self.castling_rights.white_kingside:
            castling += "K"
        if self.castling_rights.white_queenside:
            castling += "Q"
        if self.castling_rights.black_kingside:
            castling += "k"
        if self.castling_rights.black_queenside:
            castling += "q"
        if not castling:
            castling = "-"
        
        # En passant target
        if self.en_passant_target:
            col_letter = chr(ord('a') + self.en_passant_target[1])
            row_number = 8 - self.en_passant_target[0]
            ep_target = f"{col_letter}{row_number}"
        else:
            ep_target = "-"
        
        # Halfmove and fullmove clocks
        halfmove = str(self.halfmove_clock)
        fullmove = str(self.fullmove_number)
        
        return f"{board_fen} {active_color} {castling} {ep_target} {halfmove} {fullmove}"

    def calculate_activity(self, color: Color) -> int:
        """Calculate total squares reachable by all pieces of a color (excluding pawns)"""
        reachable_squares = set()

        # Find all pieces of the specified color (excluding pawns)
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color and piece.type != PieceType.PAWN:
                    # Get pseudo-legal moves (basic piece movement, ignore king safety)
                    moves = self._get_piece_pseudo_moves(row, col, piece)
                    for move_row, move_col in moves:
                        reachable_squares.add((move_row, move_col))

        return len(reachable_squares)

    def _get_piece_pseudo_moves(self, row: int, col: int, piece: Piece) -> List[Tuple[int, int]]:
        """Get pseudo-legal moves for a piece (basic movement rules only)"""
        if piece.type == PieceType.ROOK:
            return self._get_rook_moves(row, col, piece.color)
        elif piece.type == PieceType.KNIGHT:
            return self._get_knight_moves(row, col, piece.color)
        elif piece.type == PieceType.BISHOP:
            return self._get_bishop_moves(row, col, piece.color)
        elif piece.type == PieceType.QUEEN:
            return self._get_queen_moves(row, col, piece.color)
        elif piece.type == PieceType.KING:
            return self._get_king_moves(row, col, piece.color)
        else:
            return []

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

    def get_pawn_statistics(self) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
        """Get pawn statistics for both colors. Returns ((white_backward, white_isolated, white_doubled), (black_backward, black_isolated, black_doubled))"""
        white_stats = (
            self.count_backward_pawns(Color.WHITE),
            self.count_isolated_pawns(Color.WHITE),
            self.count_doubled_pawns(Color.WHITE)
        )
        black_stats = (
            self.count_backward_pawns(Color.BLACK),
            self.count_isolated_pawns(Color.BLACK),
            self.count_doubled_pawns(Color.BLACK)
        )
        return (white_stats, black_stats)

    def copy(self) -> 'BoardState':
        """Create a deep copy of the board state"""
        return copy.deepcopy(self)
    
    def __str__(self) -> str:
        """String representation of the board"""
        result = "  a b c d e f g h\n"
        for row in range(8):
            result += f"{8-row} "
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    result += str(piece) + " "
                else:
                    result += ". "
            result += f"{8-row}\n"
        result += "  a b c d e f g h\n"
        return result

    def get_possible_moves(self, row: int, col: int) -> List[Tuple[int, int]]:
        """Get all legal moves for a piece at the given position (filters out moves that leave king in check)"""
        piece = self.get_piece(row, col)
        if not piece:
            return []

        # Get all pseudo-legal moves first
        if piece.type == PieceType.PAWN:
            pseudo_moves = self._get_pawn_moves(row, col, piece.color)
        elif piece.type == PieceType.ROOK:
            pseudo_moves = self._get_rook_moves(row, col, piece.color)
        elif piece.type == PieceType.KNIGHT:
            pseudo_moves = self._get_knight_moves(row, col, piece.color)
        elif piece.type == PieceType.BISHOP:
            pseudo_moves = self._get_bishop_moves(row, col, piece.color)
        elif piece.type == PieceType.QUEEN:
            pseudo_moves = self._get_queen_moves(row, col, piece.color)
        elif piece.type == PieceType.KING:
            pseudo_moves = self._get_king_moves(row, col, piece.color)
        else:
            return []

        # Filter out moves that would leave the king in check
        legal_moves = []
        for move_row, move_col in pseudo_moves:
            if self._is_move_legal(row, col, move_row, move_col):
                legal_moves.append((move_row, move_col))

        return legal_moves

    def _is_move_legal(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Check if a move is legal (doesn't leave own king in check)"""
        # Save current state
        piece = self.get_piece(from_row, from_col)
        captured_piece = self.get_piece(to_row, to_col)

        # Make temporary move
        self.set_piece(to_row, to_col, piece)
        self.set_piece(from_row, from_col, None)

        # Check if our king is in check after this move
        is_legal = not self.is_king_in_check(piece.color)

        # Restore original state
        self.set_piece(from_row, from_col, piece)
        self.set_piece(to_row, to_col, captured_piece)

        return is_legal

    def _is_valid_square(self, row: int, col: int) -> bool:
        """Check if a square is within board bounds"""
        return 0 <= row < 8 and 0 <= col < 8

    def _is_square_empty_or_enemy(self, row: int, col: int, color: Color) -> bool:
        """Check if a square is empty or contains an enemy piece"""
        if not self._is_valid_square(row, col):
            return False
        piece = self.get_piece(row, col)
        return piece is None or piece.color != color

    def _get_pawn_moves(self, row: int, col: int, color: Color) -> List[Tuple[int, int]]:
        """Get possible moves for a pawn"""
        moves = []
        direction = -1 if color == Color.WHITE else 1  # White moves up (-1), Black moves down (+1)
        start_row = 6 if color == Color.WHITE else 1

        # Forward move
        new_row = row + direction
        if self._is_valid_square(new_row, col) and self.get_piece(new_row, col) is None:
            moves.append((new_row, col))

            # Double forward move from starting position
            if row == start_row:
                new_row = row + 2 * direction
                if self._is_valid_square(new_row, col) and self.get_piece(new_row, col) is None:
                    moves.append((new_row, col))

        # Diagonal captures
        for dc in [-1, 1]:
            new_row, new_col = row + direction, col + dc
            if self._is_valid_square(new_row, new_col):
                piece = self.get_piece(new_row, new_col)
                if piece and piece.color != color:
                    moves.append((new_row, new_col))

        # En passant capture
        if self.en_passant_target:
            ep_row, ep_col = self.en_passant_target
            if row + direction == ep_row and abs(col - ep_col) == 1:
                moves.append((ep_row, ep_col))

        return moves

    def _get_rook_moves(self, row: int, col: int, color: Color) -> List[Tuple[int, int]]:
        """Get possible moves for a rook"""
        moves = []
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # Right, Left, Down, Up

        for dr, dc in directions:
            for i in range(1, 8):
                new_row, new_col = row + i * dr, col + i * dc
                if not self._is_valid_square(new_row, new_col):
                    break

                piece = self.get_piece(new_row, new_col)
                if piece is None:
                    moves.append((new_row, new_col))
                elif piece.color != color:
                    moves.append((new_row, new_col))
                    break
                else:
                    break

        return moves

    def _get_knight_moves(self, row: int, col: int, color: Color) -> List[Tuple[int, int]]:
        """Get possible moves for a knight"""
        moves = []
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]

        for dr, dc in knight_moves:
            new_row, new_col = row + dr, col + dc
            if self._is_square_empty_or_enemy(new_row, new_col, color):
                moves.append((new_row, new_col))

        return moves

    def _get_bishop_moves(self, row: int, col: int, color: Color) -> List[Tuple[int, int]]:
        """Get possible moves for a bishop"""
        moves = []
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]  # Diagonal directions

        for dr, dc in directions:
            for i in range(1, 8):
                new_row, new_col = row + i * dr, col + i * dc
                if not self._is_valid_square(new_row, new_col):
                    break

                piece = self.get_piece(new_row, new_col)
                if piece is None:
                    moves.append((new_row, new_col))
                elif piece.color != color:
                    moves.append((new_row, new_col))
                    break
                else:
                    break

        return moves

    def _get_queen_moves(self, row: int, col: int, color: Color) -> List[Tuple[int, int]]:
        """Get possible moves for a queen (combination of rook and bishop)"""
        return self._get_rook_moves(row, col, color) + self._get_bishop_moves(row, col, color)

    def _get_king_moves(self, row: int, col: int, color: Color) -> List[Tuple[int, int]]:
        """Get possible moves for a king"""
        moves = []
        king_moves = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

        for dr, dc in king_moves:
            new_row, new_col = row + dr, col + dc
            if self._is_square_empty_or_enemy(new_row, new_col, color):
                moves.append((new_row, new_col))

        # Add castling moves
        if self.can_castle(color, True):  # Kingside
            moves.append((row, 6))  # King moves to g-file
        if self.can_castle(color, False):  # Queenside
            moves.append((row, 2))  # King moves to c-file

        return moves

    def _is_castling_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Check if a move is a castling move"""
        piece = self.get_piece(from_row, from_col)
        if not piece or piece.type != PieceType.KING:
            return False

        # King must move exactly 2 squares horizontally
        if from_row != to_row or abs(to_col - from_col) != 2:
            return False

        return True

    def _execute_castling(self, from_row: int, from_col: int, to_row: int, to_col: int) -> None:
        """Execute castling by moving both king and rook"""
        # Determine if kingside or queenside
        is_kingside = to_col > from_col

        # Move the king
        king = self.get_piece(from_row, from_col)
        self.set_piece(to_row, to_col, king)
        self.set_piece(from_row, from_col, None)

        # Move the rook
        if is_kingside:
            # Kingside castling: rook moves from h-file to f-file
            rook = self.get_piece(from_row, 7)
            self.set_piece(from_row, 5, rook)
            self.set_piece(from_row, 7, None)
            if rook:
                rook.has_moved = True
        else:
            # Queenside castling: rook moves from a-file to d-file
            rook = self.get_piece(from_row, 0)
            self.set_piece(from_row, 3, rook)
            self.set_piece(from_row, 0, None)
            if rook:
                rook.has_moved = True

        # Mark king as moved and update castling rights
        if king:
            king.has_moved = True
            self.castling_rights.lose_all_castling_rights(king.color)

    def _save_state_for_undo(self) -> None:
        """Save current board state to undo stack and clear redo stack"""
        # Create a deep copy of the current state for undo
        state_copy = self.copy()
        state_copy.undo_stack = []  # Don't copy the undo/redo stacks
        state_copy.redo_stack = []

        # Add to undo stack (limit to 50 moves to prevent memory issues)
        self.undo_stack.append(state_copy)
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)

        # Clear redo stack since we're making a new move
        self.redo_stack.clear()

    def make_move(self, from_row: int, from_col: int, to_row: int, to_col: int) -> bool:
        """Execute a move if it's legal. Returns True if move was successful."""
        # Validate the move is in the list of possible moves
        possible_moves = self.get_possible_moves(from_row, from_col)
        if (to_row, to_col) not in possible_moves:
            return False

        # Get the piece to move
        piece = self.get_piece(from_row, from_col)
        if not piece:
            return False

        # Verify it's the correct player's turn
        if piece.color != self.current_turn:
            return False

        # Save state for undo before making the move
        self._save_state_for_undo()

        # Invalidate hanging pieces cache since board will change
        self._invalidate_hanging_pieces_cache()

        # Store captured piece for move history
        captured_piece = self.get_piece(to_row, to_col)

        # Check if this is a castling move
        if self._is_castling_move(from_row, from_col, to_row, to_col):
            # Execute castling (moves both king and rook)
            self._execute_castling(from_row, from_col, to_row, to_col)
        else:
            # Execute regular move
            self.set_piece(to_row, to_col, piece)
            self.set_piece(from_row, from_col, None)

            # Mark piece as moved (important for castling and pawn double moves)
            piece.has_moved = True

            # Update castling rights based on piece moves
            if piece.type == PieceType.KING:
                # King moved - lose all castling rights for this color
                self.castling_rights.lose_all_castling_rights(piece.color)
            elif piece.type == PieceType.ROOK:
                # Rook moved - lose castling rights for the specific side
                if from_col == 0:  # Queenside rook
                    self.castling_rights.lose_castling_right(piece.color, False)
                elif from_col == 7:  # Kingside rook
                    self.castling_rights.lose_castling_right(piece.color, True)

            # Also check if a rook was captured that would affect castling rights
            if captured_piece and captured_piece.type == PieceType.ROOK:
                if to_col == 0:  # Queenside rook captured
                    self.castling_rights.lose_castling_right(captured_piece.color, False)
                elif to_col == 7:  # Kingside rook captured
                    self.castling_rights.lose_castling_right(captured_piece.color, True)

        # Handle special pawn moves
        if piece.type == PieceType.PAWN:
            # Check for double move to set en passant target
            if abs(to_row - from_row) == 2:
                self.en_passant_target = (from_row + (to_row - from_row) // 2, to_col)
            else:
                self.en_passant_target = None

            # Handle en passant capture
            if captured_piece is None and abs(to_col - from_col) == 1:
                # This is an en passant capture, remove the captured pawn
                captured_pawn_row = from_row
                self.set_piece(captured_pawn_row, to_col, None)
        else:
            self.en_passant_target = None

        # Update move counters
        if captured_piece or piece.type == PieceType.PAWN:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # Switch turns
        self.current_turn = Color.BLACK if self.current_turn == Color.WHITE else Color.WHITE

        if self.current_turn == Color.WHITE:
            self.fullmove_number += 1

        # Update check status for the new player to move
        self.is_check = self.is_king_in_check(self.current_turn)

        # Update checkmate and stalemate status
        if self.is_check:
            self.is_in_checkmate =self.is_checkmate(self.current_turn)
        else:
            self.is_in_checkmate =False
            self.is_in_stalemate =self.is_stalemate(self.current_turn)

        # Create and store move in history
        move = Move(
            from_square=(from_row, from_col),
            to_square=(to_row, to_col),
            piece=piece,
            captured_piece=captured_piece,
            move_number=self.fullmove_number
        )
        self.move_history.append(move)

        # Update last move for highlighting
        self.last_move = ((from_row, from_col), (to_row, to_col))

        return True

    def make_move_with_promotion(self, from_row: int, from_col: int, to_row: int, to_col: int,
                                promotion_piece: PieceType = PieceType.QUEEN) -> bool:
        """Execute a move with optional pawn promotion. Returns True if move was successful."""
        # Validate the move is in the list of possible moves
        possible_moves = self.get_possible_moves(from_row, from_col)
        if (to_row, to_col) not in possible_moves:
            return False

        # Get the piece to move
        piece = self.get_piece(from_row, from_col)
        if not piece:
            return False

        # Verify it's the correct player's turn
        if piece.color != self.current_turn:
            return False

        # Save state for undo before making the move
        self._save_state_for_undo()

        # Store captured piece for move history
        captured_piece = self.get_piece(to_row, to_col)

        # Check for pawn promotion
        is_promotion = False
        if piece.type == PieceType.PAWN:
            if (piece.color == Color.WHITE and to_row == 0) or (piece.color == Color.BLACK and to_row == 7):
                is_promotion = True
                # Create the promoted piece
                piece = Piece(promotion_piece, piece.color, True)

        # Execute the move
        self.set_piece(to_row, to_col, piece)
        self.set_piece(from_row, from_col, None)

        # Mark piece as moved (important for castling and pawn double moves)
        piece.has_moved = True

        # Handle special pawn moves (only if not promoting)
        if piece.type == PieceType.PAWN and not is_promotion:
            # Check for double move to set en passant target
            if abs(to_row - from_row) == 2:
                self.en_passant_target = (from_row + (to_row - from_row) // 2, to_col)
            else:
                self.en_passant_target = None

            # Handle en passant capture
            if captured_piece is None and abs(to_col - from_col) == 1:
                # This is an en passant capture, remove the captured pawn
                captured_pawn_row = from_row
                self.set_piece(captured_pawn_row, to_col, None)
        else:
            self.en_passant_target = None

        # Update move counters
        if captured_piece or piece.type == PieceType.PAWN:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # Switch turns
        self.current_turn = Color.BLACK if self.current_turn == Color.WHITE else Color.WHITE

        if self.current_turn == Color.WHITE:
            self.fullmove_number += 1

        # Update check status for the new player to move
        self.is_check = self.is_king_in_check(self.current_turn)

        # Update checkmate and stalemate status
        if self.is_check:
            self.is_in_checkmate =self.is_checkmate(self.current_turn)
        else:
            self.is_in_checkmate =False
            self.is_in_stalemate =self.is_stalemate(self.current_turn)

        # Create and store move in history
        move = Move(
            from_square=(from_row, from_col),
            to_square=(to_row, to_col),
            piece=piece,
            captured_piece=captured_piece,
            promotion=promotion_piece if is_promotion else None,
            move_number=self.fullmove_number
        )
        self.move_history.append(move)

        # Update last move for highlighting
        self.last_move = ((from_row, from_col), (to_row, to_col))

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
        # Must be in check first
        if not self.is_king_in_check(color):
            return False

        # Check if any piece of this color has legal moves
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color:
                    legal_moves = self.get_possible_moves(row, col)
                    if legal_moves:  # If any piece has legal moves, not checkmate
                        return False

        return True

    def is_stalemate(self, color: Color) -> bool:
        """Check if the specified color is in stalemate (no legal moves but not in check)"""
        # Must NOT be in check
        if self.is_king_in_check(color):
            return False

        # Check if any piece of this color has legal moves
        for row in range(8):
            for col in range(8):
                piece = self.get_piece(row, col)
                if piece and piece.color == color:
                    legal_moves = self.get_possible_moves(row, col)
                    if legal_moves:  # If any piece has legal moves, not stalemate
                        return False

        return True

    def can_undo(self) -> bool:
        """Check if undo is possible"""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is possible"""
        return len(self.redo_stack) > 0

    def undo_move(self) -> bool:
        """Undo the last move. Returns True if successful."""
        if not self.can_undo():
            return False

        # Save current state to redo stack
        current_state = self.copy()
        current_state.undo_stack = []
        current_state.redo_stack = []
        self.redo_stack.append(current_state)

        # Restore previous state from undo stack
        previous_state = self.undo_stack.pop()

        # Invalidate hanging pieces cache since board state will change
        self._invalidate_hanging_pieces_cache()

        # Copy all fields from previous state (except undo/redo stacks)
        self.board = previous_state.board
        self.current_turn = previous_state.current_turn
        self.move_number = previous_state.move_number
        self.halfmove_clock = previous_state.halfmove_clock
        self.fullmove_number = previous_state.fullmove_number
        self.castling_rights = previous_state.castling_rights
        self.en_passant_target = previous_state.en_passant_target
        self.is_check = previous_state.is_check
        self.is_in_checkmate = previous_state.is_in_checkmate
        self.is_in_stalemate = previous_state.is_in_stalemate
        self.game_phase = previous_state.game_phase
        self.move_history = previous_state.move_history
        self.last_move = previous_state.last_move
        self.position_history = previous_state.position_history

        return True

    def redo_move(self) -> bool:
        """Redo the last undone move. Returns True if successful."""
        if not self.can_redo():
            return False

        # Save current state to undo stack
        current_state = self.copy()
        current_state.undo_stack = []
        current_state.redo_stack = []
        self.undo_stack.append(current_state)

        # Restore next state from redo stack
        next_state = self.redo_stack.pop()

        # Invalidate hanging pieces cache since board state will change
        self._invalidate_hanging_pieces_cache()

        # Copy all fields from next state (except undo/redo stacks)
        self.board = next_state.board
        self.current_turn = next_state.current_turn
        self.move_number = next_state.move_number
        self.halfmove_clock = next_state.halfmove_clock
        self.fullmove_number = next_state.fullmove_number
        self.castling_rights = next_state.castling_rights
        self.en_passant_target = next_state.en_passant_target
        self.is_check = next_state.is_check
        self.is_in_checkmate = next_state.is_in_checkmate
        self.is_in_stalemate = next_state.is_in_stalemate
        self.game_phase = next_state.game_phase
        self.move_history = next_state.move_history
        self.last_move = next_state.last_move
        self.position_history = next_state.position_history

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
