"""
PGN (Portable Game Notation) parser and writer for chess games.

This module provides functionality to load and save chess games in standard PGN format,
allowing import/export of games with full move history and metadata.
"""

import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from chess_board import BoardState, Color, PieceType

class PGNGame:
    """Represents a chess game with metadata and moves in PGN format"""

    def __init__(self):
        self.tags: Dict[str, str] = {}
        self.moves: List[str] = []
        self.result: str = "*"

    def set_tag(self, key: str, value: str):
        """Set a PGN tag"""
        self.tags[key] = value

    def get_tag(self, key: str, default: str = "") -> str:
        """Get a PGN tag value"""
        return self.tags.get(key, default)

    def add_move(self, move: str):
        """Add a move to the game"""
        self.moves.append(move)

    def to_pgn(self) -> str:
        """Convert game to PGN format string"""
        lines = []

        # Add tags
        required_tags = ["Event", "Site", "Date", "Round", "White", "Black", "Result"]
        for tag in required_tags:
            value = self.get_tag(tag, "?" if tag != "Result" else "*")
            lines.append(f'[{tag} "{value}"]')

        # Add any additional tags
        for key, value in self.tags.items():
            if key not in required_tags:
                lines.append(f'[{key} "{value}"]')

        lines.append("")  # Empty line after tags

        # Add moves
        if self.moves:
            move_text = ""
            for i, move in enumerate(self.moves):
                if i % 2 == 0:  # White's move
                    move_num = (i // 2) + 1
                    move_text += f"{move_num}. {move} "
                else:  # Black's move
                    move_text += f"{move} "

            # Add result
            move_text += self.result

            # Wrap lines at reasonable length
            lines.extend(self._wrap_text(move_text, 80))
        else:
            lines.append(self.result)

        return "\n".join(lines)

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to specified width while preserving move structure"""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line + word) + 1 <= width:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

class PGNParser:
    """Parser for PGN format chess games"""

    @staticmethod
    def parse_pgn(pgn_text: str) -> List[PGNGame]:
        """Parse PGN text and return list of games"""
        games = []
        lines = pgn_text.strip().split('\n')

        current_game = None
        in_moves = False
        move_text = ""

        for line in lines:
            line = line.strip()

            if not line:
                if in_moves and move_text.strip():
                    # End of current game
                    moves, result = PGNParser._parse_moves(move_text)
                    if current_game:
                        current_game.moves = moves
                        current_game.result = result
                        games.append(current_game)

                    current_game = None
                    in_moves = False
                    move_text = ""
                continue

            if line.startswith('[') and line.endswith(']'):
                # Tag line
                if not current_game:
                    current_game = PGNGame()
                    in_moves = False

                tag_match = re.match(r'\[(\w+)\s+"(.*)"\]', line)
                if tag_match:
                    key, value = tag_match.groups()
                    current_game.set_tag(key, value)
            else:
                # Move line
                if not current_game:
                    current_game = PGNGame()
                in_moves = True
                move_text += " " + line

        # Handle last game if file doesn't end with empty line
        if current_game and (in_moves and move_text.strip()):
            moves, result = PGNParser._parse_moves(move_text)
            current_game.moves = moves
            current_game.result = result
            games.append(current_game)

        return games

    @staticmethod
    def _parse_moves(move_text: str) -> Tuple[List[str], str]:
        """Parse move text and extract moves and result"""
        # Remove comments and variations (simplified)
        text = re.sub(r'\{[^}]*\}', '', move_text)  # Remove comments
        text = re.sub(r'\([^)]*\)', '', text)        # Remove variations

        # Split into tokens
        tokens = text.split()
        moves = []
        result = "*"

        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # Check for result
            if token in ["1-0", "0-1", "1/2-1/2", "*"]:
                result = token
                break

            # Skip move numbers
            if re.match(r'\d+\.', token):
                continue

            # Skip ellipsis for black moves
            if token == "...":
                continue

            # Clean up move notation
            move = re.sub(r'[?!+#]+$', '', token)  # Remove annotation symbols
            if move and not re.match(r'\d+\.', move):
                moves.append(move)

        return moves, result

class PGNManager:
    """High-level PGN management for chess board integration"""

    @staticmethod
    def load_pgn_file(filename: str) -> List[PGNGame]:
        """Load PGN games from file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            return PGNParser.parse_pgn(content)
        except Exception as e:
            raise Exception(f"Failed to load PGN file: {e}")

    @staticmethod
    def save_pgn_file(filename: str, games: List[PGNGame]):
        """Save PGN games to file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for i, game in enumerate(games):
                    if i > 0:
                        f.write("\n\n")  # Separate games with blank lines
                    f.write(game.to_pgn())
                f.write("\n")  # End with newline
        except Exception as e:
            raise Exception(f"Failed to save PGN file: {e}")

    @staticmethod
    def create_game_from_board_state(board_state: BoardState,
                                   white_player: str = "Player",
                                   black_player: str = "Opponent",
                                   event: str = "Casual Game") -> PGNGame:
        """Create a PGN game from current board state with move history"""
        game = PGNGame()

        # Set standard tags
        game.set_tag("Event", event)
        game.set_tag("Site", "Blundex Chess")
        game.set_tag("Date", datetime.now().strftime("%Y.%m.%d"))
        game.set_tag("Round", "1")
        game.set_tag("White", white_player)
        game.set_tag("Black", black_player)

        # Convert move history to algebraic notation
        game.moves = PGNManager._convert_moves_to_algebraic(board_state)

        # Determine result
        if board_state.is_in_checkmate:
            if board_state.current_turn == Color.WHITE:
                game.result = "0-1"  # Black wins
            else:
                game.result = "1-0"  # White wins
        elif board_state.is_in_stalemate:
            game.result = "1/2-1/2"  # Draw
        else:
            game.result = "*"  # Game in progress

        game.set_tag("Result", game.result)

        return game

    @staticmethod
    def _convert_moves_to_algebraic(board_state: BoardState) -> List[str]:
        """Convert internal move history to algebraic notation"""
        moves = []

        # This is a simplified conversion - full algebraic notation
        # would require reconstructing the game state at each move
        for move in board_state.move_history:
            from_row, from_col, to_row, to_col = move[:4]

            # Convert coordinates to algebraic
            from_square = chr(ord('a') + from_col) + str(8 - from_row)
            to_square = chr(ord('a') + to_col) + str(8 - to_row)

            # Simple format for now - could be enhanced with proper algebraic notation
            algebraic_move = f"{from_square}{to_square}"

            # Add promotion if present
            if len(move) > 4:
                promotion_piece = move[4]
                if promotion_piece:
                    piece_symbols = {
                        PieceType.QUEEN: 'Q',
                        PieceType.ROOK: 'R',
                        PieceType.BISHOP: 'B',
                        PieceType.KNIGHT: 'N'
                    }
                    if promotion_piece in piece_symbols:
                        algebraic_move += f"={piece_symbols[promotion_piece]}"

            moves.append(algebraic_move)

        return moves

    @staticmethod
    def apply_pgn_game_to_board(board_state: BoardState, game: PGNGame) -> bool:
        """Apply a PGN game's moves to the board state"""
        try:
            # Reset board to starting position
            board_state.reset_to_initial_position()

            # Apply each move
            for move_str in game.moves:
                if not PGNManager._apply_algebraic_move(board_state, move_str):
                    return False

            return True
        except Exception:
            return False

    @staticmethod
    def _apply_algebraic_move(board_state: BoardState, move_str: str) -> bool:
        """Apply a single algebraic move to the board"""
        try:
            # Clean the move string
            move = move_str.strip()
            if not move:
                return False

            # Handle castling
            if move in ["O-O", "0-0"]:  # Kingside castling
                return PGNManager._apply_castling(board_state, True)
            elif move in ["O-O-O", "0-0-0"]:  # Queenside castling
                return PGNManager._apply_castling(board_state, False)

            # Handle coordinate notation (e.g., e2e4, a7a8Q)
            if len(move) >= 4 and move[0].islower() and move[1].isdigit() and move[2].islower() and move[3].isdigit():
                return PGNManager._apply_coordinate_move(board_state, move)

            # Handle standard algebraic notation (e.g., e4, Nf3, Qxd5+)
            return PGNManager._apply_standard_algebraic_move(board_state, move)

        except Exception:
            return False

    @staticmethod
    def _apply_coordinate_move(board_state: BoardState, move_str: str) -> bool:
        """Apply coordinate notation move (e.g., e2e4, a7a8Q)"""
        try:
            from_square = move_str[:2]
            to_square = move_str[2:4]

            from_col = ord(from_square[0]) - ord('a')
            from_row = 8 - int(from_square[1])
            to_col = ord(to_square[0]) - ord('a')
            to_row = 8 - int(to_square[1])

            # Check for promotion
            promotion_piece = None
            if len(move_str) > 4 and move_str[4] == '=':
                promotion_char = move_str[5].upper()
                promotion_map = {
                    'Q': PieceType.QUEEN,
                    'R': PieceType.ROOK,
                    'B': PieceType.BISHOP,
                    'N': PieceType.KNIGHT
                }
                promotion_piece = promotion_map.get(promotion_char)

            # Apply the move
            if promotion_piece:
                return board_state.make_move_with_promotion(
                    from_row, from_col, to_row, to_col, promotion_piece
                )
            else:
                return board_state.make_move(from_row, from_col, to_row, to_col)

        except (ValueError, IndexError):
            return False

    @staticmethod
    def _apply_standard_algebraic_move(board_state: BoardState, move_str: str) -> bool:
        """Apply standard algebraic notation move (e.g., e4, Nf3, Qxd5+)"""
        move = move_str.strip()

        # Remove check/checkmate indicators
        move = re.sub(r'[+#]$', '', move)

        # Parse promotion
        promotion_piece = None
        promotion_match = re.search(r'=([QRBN])$', move)
        if promotion_match:
            promotion_char = promotion_match.group(1)
            promotion_map = {
                'Q': PieceType.QUEEN,
                'R': PieceType.ROOK,
                'B': PieceType.BISHOP,
                'N': PieceType.KNIGHT
            }
            promotion_piece = promotion_map.get(promotion_char)
            move = re.sub(r'=[QRBN]$', '', move)

        # Determine piece type
        piece_type = PieceType.PAWN  # Default to pawn
        piece_char = move[0] if move[0].isupper() else None

        if piece_char:
            piece_map = {
                'K': PieceType.KING,
                'Q': PieceType.QUEEN,
                'R': PieceType.ROOK,
                'B': PieceType.BISHOP,
                'N': PieceType.KNIGHT
            }
            piece_type = piece_map.get(piece_char, PieceType.PAWN)
            move = move[1:]  # Remove piece character

        # Parse capture indicator
        is_capture = 'x' in move
        if is_capture:
            move = move.replace('x', '')

        # Extract destination square
        dest_match = re.search(r'([a-h][1-8])$', move)
        if not dest_match:
            return False

        dest_square = dest_match.group(1)
        to_col = ord(dest_square[0]) - ord('a')
        to_row = 8 - int(dest_square[1])

        # Remove destination from move string
        move = move[:dest_match.start()]

        # Find the piece that can make this move
        current_turn = board_state.current_turn
        possible_pieces = []

        for row in range(8):
            for col in range(8):
                piece = board_state.get_piece(row, col)
                if piece and piece.color == current_turn and piece.type == piece_type:
                    # Check if this piece can move to the destination
                    legal_moves = board_state.get_possible_moves(row, col)
                    if (to_row, to_col) in legal_moves:
                        possible_pieces.append((row, col))

        if not possible_pieces:
            return False

        # If multiple pieces can make the move, use disambiguation
        if len(possible_pieces) > 1:
            # Parse disambiguation (file, rank, or both)
            from_piece = None

            if move:
                if move.isdigit():  # Rank disambiguation (e.g., "R1e4")
                    from_rank = 8 - int(move)
                    from_piece = next((p for p in possible_pieces if p[0] == from_rank), None)
                elif move.isalpha() and len(move) == 1:  # File disambiguation (e.g., "Rae4")
                    from_file = ord(move) - ord('a')
                    from_piece = next((p for p in possible_pieces if p[1] == from_file), None)
                elif len(move) == 2:  # Full square disambiguation (e.g., "Ra1e4")
                    from_file = ord(move[0]) - ord('a')
                    from_rank = 8 - int(move[1])
                    from_piece = next((p for p in possible_pieces if p[0] == from_rank and p[1] == from_file), None)

            if from_piece:
                possible_pieces = [from_piece]
            else:
                # If we can't disambiguate, just use the first one
                possible_pieces = possible_pieces[:1]

        if len(possible_pieces) != 1:
            return False

        from_row, from_col = possible_pieces[0]

        # Apply the move
        if promotion_piece:
            return board_state.make_move_with_promotion(
                from_row, from_col, to_row, to_col, promotion_piece
            )
        else:
            return board_state.make_move(from_row, from_col, to_row, to_col)

    @staticmethod
    def _apply_castling(board_state: BoardState, kingside: bool) -> bool:
        """Apply castling move"""
        current_turn = board_state.current_turn

        if current_turn == Color.WHITE:
            king_row = 7
            if kingside:
                # White kingside castling: e1g1
                return board_state.make_move(7, 4, 7, 6)
            else:
                # White queenside castling: e1c1
                return board_state.make_move(7, 4, 7, 2)
        else:
            king_row = 0
            if kingside:
                # Black kingside castling: e8g8
                return board_state.make_move(0, 4, 0, 6)
            else:
                # Black queenside castling: e8c8
                return board_state.make_move(0, 4, 0, 2)