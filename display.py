"""
Chess Display Module

This module handles the visual representation of the chess board and game state.
It provides functionality to display the board, pieces, and game information.
"""

from typing import Optional, Tuple, List
import pygame
import json
import os
from chess_board import BoardState, Piece, Color, PieceType
from config import GameConfig, Colors, AnimationConfig, GameConstants

class ChessDisplay:
    """Handles the visual display of the chess game"""
    
    def __init__(self, window_width: int = 800, window_height: int = 600):
        """Initialize the display with window dimensions"""
        self.window_width = window_width
        self.window_height = window_height
        
        # Colors from config
        self.RGB_WHITE = Colors.RGB_WHITE
        self.RGB_BLACK = Colors.RGB_BLACK
        self.LIGHT_SQUARE = Colors.LIGHT_SQUARE
        self.DARK_SQUARE = Colors.DARK_SQUARE
        self.HIGHLIGHT = Colors.HIGHLIGHT
        self.SELECTED = Colors.SELECTED
        
        # Board dimensions using config values
        self.board_size = int(min(window_width, window_height * 0.9) * GameConfig.BOARD_SIZE_PERCENTAGE)
        self.square_size = self.board_size // GameConstants.BOARD_SIZE

        # Position board with config-based margins
        self.board_margin_x = int(window_width * GameConfig.BOARD_MARGIN_PERCENTAGE)
        self.board_margin_y = int(window_height * GameConfig.BOARD_MARGIN_PERCENTAGE)
        
        # Ensure pygame is initialized before creating fonts
        if not pygame.get_init():
            pygame.init()
        
        # Font setup using config values - using system fonts for better appearance
        try:
            # Try to use a modern system font (Arial, Segoe UI, or similar)
            self.font_large = pygame.font.SysFont('segoeui,arial,helvetica,sans-serif', int(self.board_size * GameConfig.FONT_LARGE_PERCENTAGE), bold=True)
            self.font_medium = pygame.font.SysFont('segoeui,arial,helvetica,sans-serif', int(self.board_size * GameConfig.FONT_MEDIUM_PERCENTAGE), bold=False)
            self.font_medium_bold = pygame.font.SysFont('segoeui,arial,helvetica,sans-serif', int(self.board_size * GameConfig.FONT_MEDIUM_PERCENTAGE), bold=True)
            self.font_small = pygame.font.SysFont('segoeui,arial,helvetica,sans-serif', int(self.board_size * GameConfig.FONT_SMALL_PERCENTAGE), bold=False)
        except:
            # Fallback to default if system fonts aren't available
            self.font_large = pygame.font.Font(None, int(self.board_size * GameConfig.FONT_LARGE_PERCENTAGE))
            self.font_medium = pygame.font.Font(None, int(self.board_size * GameConfig.FONT_MEDIUM_PERCENTAGE))
            self.font_medium_bold = pygame.font.Font(None, int(self.board_size * GameConfig.FONT_MEDIUM_PERCENTAGE))
            self.font_small = pygame.font.Font(None, int(self.board_size * GameConfig.FONT_SMALL_PERCENTAGE))
        
        # Load piece images (placeholder - you'd load actual piece images here)
        self.piece_images = self._load_piece_images()

        # Create move indicator circle surface once
        self.move_indicator = self._create_move_indicator()

        # Help panel dimensions and positioning
        self.help_panel_width = int(window_width * GameConfig.HELP_PANEL_WIDTH_PERCENTAGE)
        self.help_panel_x = self.board_margin_x + self.board_size + int(window_width * GameConfig.HELP_PANEL_MARGIN_PERCENTAGE)
        self.help_panel_y = self.board_margin_y

        # Checkbox dimensions
        self.checkbox_size = int(window_width * GameConfig.CHECKBOX_SIZE_PERCENTAGE)
        self.checkbox_spacing = int(window_height * GameConfig.CHECKBOX_SPACING_PERCENTAGE)

        # Help options - load from settings file if available
        self.settings_file = ".blundex"
        self.help_options = [
            {"name": "Hanging Pieces", "key": "hanging_pieces", "enabled": False},
            {"name": "Exchange Evaluation", "key": "exchange_evaluation", "enabled": False},
            {"name": "Flip Board", "key": "flip_board", "enabled": False}
        ]
        self._load_settings()

        # Checkmate animation variables
        self.checkmate_animation_start_time = None
        self.checkmate_king_position = None

        # Cache activity scores to avoid constant recalculation
        self.cached_activity_white = 0
        self.cached_activity_black = 0
        self.activity_cache_valid = False

    def invalidate_activity_cache(self):
        """Invalidate activity cache when board state changes"""
        self.activity_cache_valid = False
    
    def _load_piece_images(self) -> dict:
        """Load and scale piece images from PNG files"""
        images = {}

        for color in [Color.WHITE, Color.BLACK]:
            for piece_type in PieceType:
                # Calculate piece size based on type (pawns smaller than other pieces)
                if piece_type == PieceType.PAWN:
                    piece_size = int(self.square_size * 0.65)
                else:
                    piece_size = int(self.square_size * 0.75)

                # Create filename based on naming convention: {color}{piece}.png
                color_prefix = "w" if color == Color.WHITE else "b"
                filename = f"pngs/2x/{color_prefix}{piece_type.value}.png"

                try:
                    # Load the original image
                    original_image = pygame.image.load(filename)

                    # Scale once using smooth scaling and cache it
                    scaled_image = pygame.transform.smoothscale(original_image, (piece_size, piece_size))

                    # Store with the key format used elsewhere in the code
                    key = f"{color.value}{piece_type.value}"
                    images[key] = scaled_image

                except pygame.error as e:
                    print(f"Warning: Could not load {filename}: {e}")
                    # Create a fallback colored rectangle if image loading fails
                    surface = pygame.Surface((piece_size, piece_size))
                    if color == Color.WHITE:
                        surface.fill(self.RGB_WHITE)
                    else:
                        surface.fill(self.RGB_BLACK)
                    pygame.draw.rect(surface, Colors.PIECE_BORDER, surface.get_rect(), 2)

                    key = f"{color.value}{piece_type.value}"
                    images[key] = surface

        return images

    def _create_move_indicator(self) -> pygame.Surface:
        """Create a translucent circle surface for move indicators"""
        # Create a surface with per-pixel alpha
        circle_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)

        # Circle size is 1/4 of the square
        circle_radius = self.square_size // 4
        center_x = self.square_size // 2
        center_y = self.square_size // 2

        # Draw translucent circle (light grey with alpha for subtle visibility)
        circle_color = (*Colors.ANNOTATION_NEUTRAL, 100)  # Light grey with transparency
        pygame.draw.circle(circle_surface, circle_color, (center_x, center_y), circle_radius)

        return circle_surface

    def draw_help_panel(self, screen) -> None:
        """Draw the help panel with checkboxes on the right side of the board"""
        # Draw panel background (optional - subtle background)
        panel_rect = pygame.Rect(self.help_panel_x, self.help_panel_y,
                               self.help_panel_width, self.board_size)
        pygame.draw.rect(screen, Colors.HELP_PANEL_BACKGROUND, panel_rect)
        pygame.draw.rect(screen, Colors.RGB_BLACK, panel_rect, 1)

        # Draw checkboxes
        current_y = self.help_panel_y + 20
        for i, option in enumerate(self.help_options):
            self._draw_checkbox(screen, self.help_panel_x + 10, current_y, option)
            current_y += self.checkbox_spacing

    def _draw_checkbox(self, screen, x: int, y: int, option: dict) -> None:
        """Draw a single stylish checkbox with label"""
        # Create rounded rectangle effect with layered rectangles
        corner_radius = 4

        # Draw shadow (slightly offset)
        shadow_rect = pygame.Rect(x + 2, y + 2, self.checkbox_size, self.checkbox_size)
        pygame.draw.rect(screen, Colors.CHECKBOX_SHADOW, shadow_rect, border_radius=corner_radius)

        # Main checkbox background
        checkbox_rect = pygame.Rect(x, y, self.checkbox_size, self.checkbox_size)
        if option["enabled"]:
            # Filled background when checked
            pygame.draw.rect(screen, Colors.ANNOTATION_POSITIVE, checkbox_rect, border_radius=corner_radius)
        else:
            # Light background when unchecked
            pygame.draw.rect(screen, Colors.CHECKBOX_UNCHECKED_BG, checkbox_rect, border_radius=corner_radius)

        # Border
        border_color = Colors.ANNOTATION_POSITIVE if option["enabled"] else Colors.CHECKBOX_BORDER_UNCHECKED
        pygame.draw.rect(screen, border_color, checkbox_rect, width=2, border_radius=corner_radius)

        # Draw checkmark if enabled
        if option["enabled"]:
            # Draw a more refined checkmark
            check_color = Colors.RGB_WHITE
            check_thickness = 3
            # Smoother checkmark coordinates
            check_x1 = x + self.checkbox_size * 0.25
            check_y1 = y + self.checkbox_size * 0.55
            check_x2 = x + self.checkbox_size * 0.45
            check_y2 = y + self.checkbox_size * 0.7
            check_x3 = x + self.checkbox_size * 0.75
            check_y3 = y + self.checkbox_size * 0.35

            pygame.draw.line(screen, check_color, (check_x1, check_y1), (check_x2, check_y2), check_thickness)
            pygame.draw.line(screen, check_color, (check_x2, check_y2), (check_x3, check_y3), check_thickness)

        # Draw label with better styling
        label_text = self.font_small.render(option["name"], True, Colors.LABEL_TEXT_COLOR)
        label_x = x + self.checkbox_size + 12
        label_y = y + (self.checkbox_size - label_text.get_height()) // 2
        screen.blit(label_text, (label_x, label_y))

    def get_checkbox_at_pos(self, mouse_pos: Tuple[int, int]) -> Optional[str]:
        """Get the key of the checkbox at the given mouse position, if any"""
        mouse_x, mouse_y = mouse_pos

        current_y = self.help_panel_y + 20  # Starting y position for checkboxes (matches drawing)
        for option in self.help_options:
            # Create expanded clickable area that includes both checkbox and text label
            label_text = self.font_small.render(option["name"], True, Colors.LABEL_TEXT_COLOR)
            label_width = label_text.get_width()

            # Clickable area extends from checkbox to end of text label
            clickable_rect = pygame.Rect(self.help_panel_x + 10, current_y,
                                       self.checkbox_size + 12 + label_width, self.checkbox_size)
            if clickable_rect.collidepoint(mouse_x, mouse_y):
                return option["key"]
            current_y += self.checkbox_spacing

        return None

    def toggle_help_option(self, key: str) -> bool:
        """Toggle a help option and return its new state"""
        for option in self.help_options:
            if option["key"] == key:
                option["enabled"] = not option["enabled"]
                self._save_settings()  # Save settings when changed
                return option["enabled"]
        return False

    def is_help_option_enabled(self, key: str) -> bool:
        """Check if a help option is enabled"""
        for option in self.help_options:
            if option["key"] == key:
                return option["enabled"]
        return False

    def draw_move_indicator(self, screen, x: int, y: int) -> None:
        """Draw the pre-created move indicator at specified position"""
        screen.blit(self.move_indicator, (x, y))

    def draw_hanging_piece_indicator(self, screen, x: int, y: int, is_player_piece: bool) -> None:
        """Draw a hanging piece indicator with consistent border thickness"""

        # Simple, clear colors
        if is_player_piece:
            indicator_color = Colors.ANNOTATION_WARNING  # Red for player's hanging pieces (danger)
        else:
            indicator_color = Colors.ANNOTATION_POSITIVE  # Green for opponent's hanging pieces (opportunity)

        # Use same border thickness as orange highlights for consistency
        border_thickness = 4

        # Draw border on all four edges
        border_rect = pygame.Rect(x, y, self.square_size, self.square_size)
        pygame.draw.rect(screen, indicator_color, border_rect, border_thickness)

    def is_animation_active(self) -> bool:
        """Check if any animations are currently running"""
        return self.checkmate_animation_start_time is not None

    def start_checkmate_animation(self, board_state: BoardState) -> None:
        """Start the checkmate animation for the losing king"""
        import time
        self.checkmate_animation_start_time = time.time()

        # Find the checkmated king position
        losing_color = board_state.current_turn
        self.checkmate_king_position = board_state.get_king_position(losing_color)

    def draw_rotating_king(self, screen, piece: Piece, x: int, y: int, elapsed_time: float) -> None:
        """Draw a king rotating on its head"""
        # Animation duration is 0.5 seconds for 360 degree rotation
        animation_duration = 0.5

        if elapsed_time > animation_duration:
            # Animation finished, draw normally but upside down
            angle = 180
        else:
            # Calculate rotation angle (0 to 180 degrees over 0.5 seconds)
            progress = elapsed_time / animation_duration
            angle = progress * 180

        # Get the original piece image
        key = f"{piece.color.value}{piece.type.value}"
        if key in self.piece_images:
            original_surface = self.piece_images[key]

            # Rotate the image
            rotated_surface = pygame.transform.rotate(original_surface, angle)

            # Center the rotated image in the square
            rotated_rect = rotated_surface.get_rect()
            center_x = x + self.square_size // 2
            center_y = y + self.square_size // 2
            rotated_rect.center = (center_x, center_y)

            screen.blit(rotated_surface, rotated_rect)
        else:
            # Fallback to text
            piece_text = str(piece)
            text_surface = self.font_large.render(piece_text, True, self.RGB_BLACK)
            text_rect = text_surface.get_rect(center=(x + self.square_size//2, y + self.square_size//2))
            screen.blit(text_surface, text_rect)

    def draw_board(self, screen, board_state: BoardState, selected_square_coords: Optional[Tuple[int, int]] = None,
                   highlighted_moves: List[Tuple[int, int]] = None, is_board_flipped: bool = False,
                   preview_board_state: Optional[BoardState] = None, dragging_piece=None, drag_origin=None,
                   mouse_pos: Optional[Tuple[int, int]] = None) -> None:
        """Draw the chess board with pieces"""
        if highlighted_moves is None:
            highlighted_moves = []
        
        # Draw the board squares
        for row in range(8):
            for col in range(8):
                # Apply flipping transformation
                display_row = (7 - row) if is_board_flipped else row
                display_col = (7 - col) if is_board_flipped else col
                x = self.board_margin_x + display_col * self.square_size
                y = self.board_margin_y + display_row * self.square_size
                
                # Determine square color (use original coordinates for coloring)
                is_light = (row + col) % 2 == 0
                color = self.LIGHT_SQUARE if is_light else self.DARK_SQUARE

                # Apply last move highlighting (lichess-style green overlay)
                if board_state.last_move:
                    from_square, to_square = board_state.last_move
                    if (row, col) == from_square or (row, col) == to_square:
                        color = Colors.LIGHT_SQUARE_LAST_MOVE if is_light else Colors.DARK_SQUARE_LAST_MOVE

                # Highlight selected square only
                if selected_square_coords and selected_square_coords == (row, col):
                    color = self.SELECTED

                # Draw the square
                pygame.draw.rect(screen, color,
                               (x, y, self.square_size, self.square_size))

                # Draw piece if present (skip if being dragged)
                piece = board_state.get_piece(row, col)
                if piece and not (dragging_piece and drag_origin and (row, col) == drag_origin):
                    self.draw_piece(screen, piece, x, y, row, col)

                # Draw move indicator circle for possible moves
                if (row, col) in highlighted_moves:
                    self.draw_move_indicator(screen, x, y)

                # Draw hanging piece indicator if enabled
                if self.is_help_option_enabled("hanging_pieces"):
                    # Use preview board state for helper evaluation if available
                    evaluation_board = preview_board_state if preview_board_state else board_state

                    # Get the piece that would be at this position in the evaluation board
                    evaluation_piece = evaluation_board.get_piece(row, col)

                    if evaluation_piece:
                        hanging_pieces = evaluation_board.get_hanging_pieces(evaluation_piece.color)
                        if (row, col) in hanging_pieces:
                            # Determine player color based on board orientation
                            # Player = pieces on bottom (white when not flipped, black when flipped)
                            player_color = Color.BLACK if is_board_flipped else Color.WHITE
                            is_player_piece = (evaluation_piece.color == player_color)
                            self.draw_hanging_piece_indicator(screen, x, y, is_player_piece)

                # Draw exchange evaluation indicator if enabled
                if self.is_help_option_enabled("exchange_evaluation"):
                    # Use preview board state for helper evaluation if available
                    evaluation_board = preview_board_state if preview_board_state else board_state

                    # Get list of tactically interesting squares
                    interesting_squares = evaluation_board.get_tactically_interesting_squares()
                    if (row, col) in interesting_squares:
                        self.draw_exchange_indicator(screen, x, y)

        # Draw exchange evaluation piece highlights (orange borders) if hovering
        if mouse_pos:
            evaluation_board = preview_board_state if preview_board_state else board_state
            highlight_positions = self.get_exchange_highlights(mouse_pos, evaluation_board, is_board_flipped)

            for highlight_row, highlight_col in highlight_positions:
                # Convert board coordinates to display coordinates
                display_pos = self.get_square_display_position(highlight_row, highlight_col, is_board_flipped)
                if display_pos:
                    x, y = display_pos
                    self.draw_piece_highlight(screen, x, y)

        # Draw board border (use actual board size based on squares)
        actual_board_size = self.square_size * 8
        border_rect = pygame.Rect(self.board_margin_x - 2, self.board_margin_y - 2,
                                actual_board_size + 4, actual_board_size + 4)
        pygame.draw.rect(screen, self.RGB_BLACK, border_rect, 2)
        
        # Draw coordinates
        self.draw_coordinates(screen, is_board_flipped)

    def draw_dragged_piece(self, screen, piece, mouse_pos: Tuple[int, int], is_board_flipped: bool = False) -> None:
        """Draw a piece being dragged, snapped to center of square under mouse"""
        if piece:
            # Get the square under the mouse
            current_square = self.get_square_from_mouse(mouse_pos)

            if current_square:
                # Convert to board coordinates if needed
                if is_board_flipped:
                    board_square = (7 - current_square[0], 7 - current_square[1])
                else:
                    board_square = current_square

                # Get the display position of this square
                square_pos = self.get_square_display_position(board_square[0], board_square[1], is_board_flipped)
                if square_pos:
                    piece_x, piece_y = square_pos
                    # Draw the piece centered in the square
                    self.draw_piece(screen, piece, piece_x, piece_y, -1, -1)
            else:
                # If not over a square, draw at cursor position
                piece_x = mouse_pos[0] - self.square_size // 2
                piece_y = mouse_pos[1] - self.square_size // 2
                self.draw_piece(screen, piece, piece_x, piece_y, -1, -1)
    
    def draw_piece(self, screen, piece: Piece, x: int, y: int, board_row: int = -1, board_col: int = -1) -> None:
        """Draw a piece at the specified screen coordinates"""
        # Check if this is the checkmated king and animation is active
        if (self.checkmate_animation_start_time is not None and
            self.checkmate_king_position is not None and
            piece.type == PieceType.KING and
            (board_row, board_col) == self.checkmate_king_position):

            import time
            elapsed_time = time.time() - self.checkmate_animation_start_time
            self.draw_rotating_king(screen, piece, x, y, elapsed_time)
            return

        # Normal piece drawing
        key = f"{piece.color.value}{piece.type.value}"
        if key in self.piece_images:
            piece_surface = self.piece_images[key]
            # Center the piece in the square
            piece_x = x + (self.square_size - piece_surface.get_width()) // 2
            piece_y = y + (self.square_size - piece_surface.get_height()) // 2
            screen.blit(piece_surface, (piece_x, piece_y))
        else:
            # Fallback: draw piece as text
            piece_text = str(piece)
            text_surface = self.font_large.render(piece_text, True, self.RGB_BLACK)
            text_rect = text_surface.get_rect(center=(x + self.square_size//2, y + self.square_size//2))
            screen.blit(text_surface, text_rect)
    
    def draw_coordinates(self, screen, is_board_flipped: bool = False) -> None:
        """Draw board coordinates (a-h, 1-8)"""
        # Draw file letters (a-h)
        for col in range(8):
            letter = chr(ord('a') + (7 - col if is_board_flipped else col))
            x = self.board_margin_x + col * self.square_size + self.square_size // 2
            y = self.board_margin_y + self.board_size + 10
            
            text_surface = self.font_small.render(letter, True, self.RGB_BLACK)
            text_rect = text_surface.get_rect(center=(x, y))
            screen.blit(text_surface, text_rect)
        
        # Draw rank numbers (1-8)
        for row in range(8):
            number = str((row + 1) if is_board_flipped else (8 - row))
            x = self.board_margin_x - 20
            y = self.board_margin_y + row * self.square_size + self.square_size // 2
            
            text_surface = self.font_small.render(number, True, self.RGB_BLACK)
            text_rect = text_surface.get_rect(center=(x, y))
            screen.blit(text_surface, text_rect)

    def draw_activity_display(self, screen, board_state: BoardState, is_board_flipped: bool = False, force_recalculate: bool = False) -> None:
        """Draw activity scores underneath the board"""
        if force_recalculate or not self.activity_cache_valid:
            # Only recalculate when forced (preview) or cache invalid
            white_activity, black_activity = board_state.get_activity_scores()
            if not force_recalculate:
                # Update cache only if this is the main board state
                self.cached_activity_white = white_activity
                self.cached_activity_black = black_activity
                self.activity_cache_valid = True
        else:
            # Use cached values
            white_activity, black_activity = self.cached_activity_white, self.cached_activity_black

        # Determine player vs opponent based on board orientation
        if is_board_flipped:
            player_activity = black_activity
            opponent_activity = white_activity
        else:
            player_activity = white_activity
            opponent_activity = black_activity

        # Position below coordinates
        center_x = self.board_margin_x + self.board_size // 2
        activity_y = self.board_margin_y + self.board_size + 35

        # Create activity text: "Activity: XX YY"
        activity_text = f"Activity: {player_activity} {opponent_activity}"

        # Determine colors (bold black for winning score, medium grey for losing)
        if player_activity > opponent_activity:
            player_color = Colors.RGB_BLACK  # Bold black
            opponent_color = Colors.ANNOTATION_NEUTRAL  # Medium grey
        elif opponent_activity > player_activity:
            player_color = Colors.ANNOTATION_NEUTRAL  # Medium grey
            opponent_color = Colors.RGB_BLACK  # Bold black
        else:
            player_color = Colors.RGB_BLACK
            opponent_color = Colors.RGB_BLACK

        # Render text parts separately for color highlighting
        label_surface = self.font_medium.render("Activity: ", True, Colors.RGB_BLACK)
        # Use bold font for black (winning) scores, regular for grey (losing) scores
        player_font = self.font_medium_bold if player_color == Colors.RGB_BLACK else self.font_medium
        opponent_font = self.font_medium_bold if opponent_color == Colors.RGB_BLACK else self.font_medium
        player_surface = player_font.render(str(player_activity), True, player_color)
        space_surface = self.font_medium.render(" ", True, Colors.RGB_BLACK)
        opponent_surface = opponent_font.render(str(opponent_activity), True, opponent_color)

        # Calculate total width for centering
        total_width = (label_surface.get_width() + player_surface.get_width() +
                      space_surface.get_width() + opponent_surface.get_width())
        start_x = center_x - total_width // 2

        # Draw each part
        current_x = start_x
        screen.blit(label_surface, (current_x, activity_y))
        current_x += label_surface.get_width()
        screen.blit(player_surface, (current_x, activity_y))
        current_x += player_surface.get_width()
        screen.blit(space_surface, (current_x, activity_y))
        current_x += space_surface.get_width()
        screen.blit(opponent_surface, (current_x, activity_y))

    def draw_pawn_display(self, screen, board_state: BoardState, is_board_flipped: bool = False) -> None:
        """Draw pawn counts underneath the activity display in tabular format"""
        white_pawns, black_pawns = board_state.get_pawn_counts()

        # Determine player vs opponent based on board orientation
        if is_board_flipped:
            player_pawns = black_pawns
            opponent_pawns = white_pawns
        else:
            player_pawns = white_pawns
            opponent_pawns = black_pawns

        # Position below activity display
        center_x = self.board_margin_x + self.board_size // 2
        pawn_y = self.board_margin_y + self.board_size + 60  # Below activity line

        # Create pawn text: "Pawns: XX YY"
        pawn_text = f"Pawns: {player_pawns} {opponent_pawns}"

        # Determine colors (bold black for more pawns, medium grey for fewer)
        if player_pawns > opponent_pawns:
            player_color = Colors.RGB_BLACK  # Bold black
            opponent_color = Colors.ANNOTATION_NEUTRAL  # Medium grey
        elif opponent_pawns > player_pawns:
            player_color = Colors.ANNOTATION_NEUTRAL  # Medium grey
            opponent_color = Colors.RGB_BLACK  # Bold black
        else:
            player_color = Colors.RGB_BLACK
            opponent_color = Colors.RGB_BLACK

        # Render text parts separately for color highlighting
        label_surface = self.font_medium.render("Pawns: ", True, Colors.RGB_BLACK)
        # Use bold font for black (winning) scores, regular for grey (losing) scores
        player_font = self.font_medium_bold if player_color == Colors.RGB_BLACK else self.font_medium
        opponent_font = self.font_medium_bold if opponent_color == Colors.RGB_BLACK else self.font_medium
        player_surface = player_font.render(str(player_pawns), True, player_color)
        space_surface = self.font_medium.render(" ", True, Colors.RGB_BLACK)
        opponent_surface = opponent_font.render(str(opponent_pawns), True, opponent_color)

        # Calculate total width for centering
        total_width = (label_surface.get_width() + player_surface.get_width() +
                      space_surface.get_width() + opponent_surface.get_width())
        start_x = center_x - total_width // 2

        # Draw each part
        current_x = start_x
        screen.blit(label_surface, (current_x, pawn_y))
        current_x += label_surface.get_width()
        screen.blit(player_surface, (current_x, pawn_y))
        current_x += player_surface.get_width()
        screen.blit(space_surface, (current_x, pawn_y))
        current_x += space_surface.get_width()
        screen.blit(opponent_surface, (current_x, pawn_y))

    def draw_text(self, screen, text: str, x: int, y: int, font: pygame.font.Font,
                  color: Tuple[int, int, int] = None) -> None:
        """Draw text at the specified position"""
        if color is None:
            color = self.RGB_BLACK
        
        text_surface = font.render(text, True, color)
        screen.blit(text_surface, (x, y))

    def draw_exchange_indicator(self, screen, x: int, y: int) -> None:
        """Draw a subtle indicator for squares with exchange potential"""
        # Small colored corner indicators to mark tactical squares
        corner_size = 8
        indicator_color = Colors.ANNOTATION_CAUTION  # Yellow for tactical awareness

        # Draw small triangle in the top-right corner
        triangle_points = [
            (x + self.square_size - corner_size, y),
            (x + self.square_size, y),
            (x + self.square_size, y + corner_size)
        ]
        pygame.draw.polygon(screen, indicator_color, triangle_points)

    def draw_piece_highlight(self, screen, x: int, y: int) -> None:
        """Draw orange highlighting around a piece (for attacker/defender display)"""
        # Draw a thick orange border around the piece
        border_thickness = 4
        highlight_color = (255, 165, 0)  # Orange color

        # Draw border around the entire square
        border_rect = pygame.Rect(x, y, self.square_size, self.square_size)
        pygame.draw.rect(screen, highlight_color, border_rect, border_thickness)

    def get_exchange_highlights(self, mouse_pos: Tuple[int, int], board_state, is_board_flipped: bool = False) -> List[Tuple[int, int]]:
        """
        Get list of piece positions to highlight based on mouse hover over tactical squares.
        Returns list of (row, col) positions that should be highlighted in orange.
        """
        if not self.is_help_option_enabled("exchange_evaluation"):
            return []

        # Check if mouse is over a tactically interesting square
        hovered_square = self.get_square_from_mouse(mouse_pos)
        if not hovered_square:
            return []

        # Convert display coordinates to board coordinates if flipped
        if is_board_flipped:
            board_square = (7 - hovered_square[0], 7 - hovered_square[1])
        else:
            board_square = hovered_square

        # Check if this square is tactically interesting
        interesting_squares = board_state.get_tactically_interesting_squares()
        if board_square not in interesting_squares:
            return []

        # Get all attackers and defenders for this square
        attackers, defenders = board_state.get_all_attackers_and_defenders(board_square[0], board_square[1])

        # Return all positions that should be highlighted
        return attackers + defenders

    def get_square_display_position(self, row: int, col: int, is_board_flipped: bool = False) -> Optional[Tuple[int, int]]:
        """Get the display position (x, y) of a board square"""
        # Apply board flipping for display coordinates
        display_row = (7 - row) if is_board_flipped else row
        display_col = (7 - col) if is_board_flipped else col

        x = self.board_margin_x + display_col * self.square_size
        y = self.board_margin_y + display_row * self.square_size

        return (x, y)

    def get_square_from_mouse(self, mouse_pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Convert mouse position to board square coordinates"""
        mouse_x, mouse_y = mouse_pos
        
        # Check if mouse is within board bounds
        if (self.board_margin_x <= mouse_x <= self.board_margin_x + self.board_size and
            self.board_margin_y <= mouse_y <= self.board_margin_y + self.board_size):
            
            col = (mouse_x - self.board_margin_x) // self.square_size
            row = (mouse_y - self.board_margin_y) // self.square_size
            
            if 0 <= row < 8 and 0 <= col < 8:
                return (row, col)
        
        return None
    
    def update_display(self, screen, board_state: BoardState, selected_square_coords: Optional[Tuple[int, int]] = None,
                      highlighted_moves: List[Tuple[int, int]] = None, is_board_flipped: bool = False,
                      preview_board_state: Optional[BoardState] = None, dragging_piece=None, drag_origin=None,
                      mouse_pos: Optional[Tuple[int, int]] = None) -> None:
        """Update the entire display"""
        # Check for checkmate and start animation if needed
        if board_state.is_in_checkmate and self.checkmate_animation_start_time is None:
            self.start_checkmate_animation(board_state)
        elif not board_state.is_in_checkmate and self.checkmate_animation_start_time is not None:
            # Reset animation state if we're no longer in checkmate (e.g., after undo)
            self.checkmate_animation_start_time = None
            self.checkmate_king_position = None

        # Clear screen
        screen.fill(self.RGB_WHITE)

        # Draw all components
        self.draw_board(screen, board_state, selected_square_coords, highlighted_moves, is_board_flipped, preview_board_state, dragging_piece, drag_origin, mouse_pos)

        # Only calculate activity when dragging to a legal move (like hanging pieces helper)
        if preview_board_state:
            # Only recalculate when there's a preview (dragging to legal square)
            self.draw_activity_display(screen, preview_board_state, is_board_flipped, force_recalculate=True)
            self.draw_pawn_display(screen, preview_board_state, is_board_flipped)
        else:
            # Show cached activity scores without recalculating
            self.draw_activity_display(screen, board_state, is_board_flipped, force_recalculate=False)
            self.draw_pawn_display(screen, board_state, is_board_flipped)

        self.draw_help_panel(screen)

        # Draw stalemate overlay if needed
        if board_state.is_in_stalemate:
            self.draw_stalemate_overlay(screen)

        # Note: pygame.display.flip() is called in the main loop, not here

    def draw_stalemate_overlay(self, screen) -> None:
        """Draw a semi-transparent stalemate message overlay with rubber stamp effect"""
        # Create semi-transparent overlay
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))  # Semi-transparent black
        screen.blit(overlay, (0, 0))

        # Calculate board width for text sizing
        board_width = self.square_size * 8

        # Create a large font to make text span the board width
        font_size = int(board_width * 0.2)  # 20% of board width for bigger text
        stamp_font = pygame.font.Font(None, font_size)

        # Draw stalemate message in bright red
        stalemate_text = "STALEMATE"
        text_surface = stamp_font.render(stalemate_text, True, Colors.STALEMATE_TEXT)

        # Scale text to exactly match board width
        text_width = text_surface.get_width()
        scale_factor = board_width / text_width
        new_width = int(text_width * scale_factor)
        new_height = int(text_surface.get_height() * scale_factor)
        text_surface = pygame.transform.smoothscale(text_surface, (new_width, new_height))

        # Rotate the text 30 degrees for rubber stamp effect
        rotated_surface = pygame.transform.rotate(text_surface, 30)

        # Create black outline for the rotated text
        outline_surface = stamp_font.render(stalemate_text, True, Colors.STALEMATE_OUTLINE)
        outline_surface = pygame.transform.smoothscale(outline_surface, (new_width, new_height))
        rotated_outline = pygame.transform.rotate(outline_surface, 30)

        # Center the rotated text on the board (not the whole window)
        board_center_x = self.board_margin_x + (self.square_size * 8) // 2
        board_center_y = self.board_margin_y + (self.square_size * 8) // 2

        rotated_rect = rotated_surface.get_rect(center=(board_center_x, board_center_y))
        outline_rect = rotated_outline.get_rect(center=(board_center_x, board_center_y))

        # Draw thick black outline for better visibility
        for dx in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:
            for dy in [-4, -3, -2, -1, 0, 1, 2, 3, 4]:
                if dx != 0 or dy != 0:
                    screen.blit(rotated_outline, (outline_rect.x + dx, outline_rect.y + dy))

        # Draw main red text
        screen.blit(rotated_surface, rotated_rect)

    def draw_keyboard_shortcuts_panel(self, screen) -> None:
        """Draw a centered panel showing all keyboard shortcuts with dynamic sizing"""
        # Define shortcuts
        shortcuts = [
            ("B", "Flip board"),
            ("U", "Undo move"),
            ("R", "Redo move"),
            ("H", "Toggle hanging pieces"),
            ("E", "Toggle exchange evaluation"),
            ("~", "Reset game"),
            ("/", "Show/hide this help"),
            ("Esc", "Exit game")
        ]

        # Calculate text dimensions
        title_text = "Keyboard Shortcuts"
        title_surface = self.font_large.render(title_text, True, Colors.BLACK_TEXT)
        title_width, title_height = title_surface.get_size()

        instruction_text = "Press / again to close"
        instruction_surface = self.font_small.render(instruction_text, True, Colors.LABEL_TEXT_COLOR)
        instruction_width, instruction_height = instruction_surface.get_size()

        # Calculate maximum width needed for shortcuts
        max_shortcut_width = 0
        shortcut_heights = []
        for key, description in shortcuts:
            key_surface = self.font_medium.render(f"{key}:", True, Colors.RGB_BLACK)
            desc_surface = self.font_small.render(description, True, Colors.LABEL_TEXT_COLOR)

            # Calculate combined width (key + gap + description)
            combined_width = key_surface.get_width() + 20 + desc_surface.get_width()  # 20px gap
            max_shortcut_width = max(max_shortcut_width, combined_width)

            # Use the taller of the two fonts for line height
            line_height = max(key_surface.get_height(), desc_surface.get_height())
            shortcut_heights.append(line_height)

        # Calculate panel dimensions with padding
        padding = 40
        internal_padding = 20

        panel_content_width = max(title_width, max_shortcut_width, instruction_width)
        panel_width = panel_content_width + 2 * padding

        # Calculate height: title + gap + shortcuts + gap + instruction + padding
        shortcuts_total_height = sum(shortcut_heights) + (len(shortcuts) - 1) * 5  # 5px between lines
        panel_height = title_height + internal_padding + shortcuts_total_height + internal_padding + instruction_height + 2 * padding

        # Center the panel
        panel_x = (self.window_width - panel_width) // 2
        panel_y = (self.window_height - panel_height) // 2

        # Create semi-transparent background overlay
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))  # Semi-transparent black
        screen.blit(overlay, (0, 0))

        # Draw panel background
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(screen, Colors.HELP_PANEL_BACKGROUND, panel_rect)
        pygame.draw.rect(screen, Colors.RGB_BLACK, panel_rect, 3)  # Thicker border

        # Draw title (centered)
        title_rect = title_surface.get_rect(center=(panel_x + panel_width // 2, panel_y + padding + title_height // 2))
        screen.blit(title_surface, title_rect)

        # Draw shortcuts
        current_y = panel_y + padding + title_height + internal_padding

        for i, (key, description) in enumerate(shortcuts):
            # Render text
            key_surface = self.font_medium.render(f"{key}:", True, Colors.RGB_BLACK)
            desc_surface = self.font_small.render(description, True, Colors.LABEL_TEXT_COLOR)

            # Position key text
            key_x = panel_x + padding
            key_y = current_y
            screen.blit(key_surface, (key_x, key_y))

            # Position description text (aligned to baseline of key text)
            desc_x = key_x + key_surface.get_width() + 20  # 20px gap
            desc_y = key_y + (key_surface.get_height() - desc_surface.get_height()) // 2  # Center vertically
            screen.blit(desc_surface, (desc_x, desc_y))

            # Move to next line
            current_y += shortcut_heights[i] + 5  # 5px spacing between lines

        # Draw instructions at bottom (centered)
        instruction_rect = instruction_surface.get_rect(center=(panel_x + panel_width // 2, panel_y + panel_height - padding - instruction_height // 2))
        screen.blit(instruction_surface, instruction_rect)

    def show_promotion_dialog(self, screen, color: Color) -> PieceType:
        """Show promotion dialog and return selected piece type"""
        # Define promotion pieces (Queen, Rook, Bishop, Knight)
        promotion_pieces = [PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT]

        # Dialog dimensions
        dialog_width = 400
        dialog_height = 150
        dialog_x = (self.window_width - dialog_width) // 2
        dialog_y = (self.window_height - dialog_height) // 2

        # Create semi-transparent overlay
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))  # Semi-transparent black
        screen.blit(overlay, (0, 0))

        # Draw dialog box
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, self.RGB_WHITE, dialog_rect)
        pygame.draw.rect(screen, self.RGB_BLACK, dialog_rect, 3)

        # Draw title
        title_text = "Choose promotion piece:"
        title_surface = self.font_medium.render(title_text, True, self.RGB_BLACK)
        title_rect = title_surface.get_rect(center=(dialog_x + dialog_width//2, dialog_y + 30))
        screen.blit(title_surface, title_rect)

        # Draw piece options
        piece_size = 60
        piece_spacing = (dialog_width - 4 * piece_size) // 5
        piece_rects = []

        for i, piece_type in enumerate(promotion_pieces):
            piece_x = dialog_x + piece_spacing + i * (piece_size + piece_spacing)
            piece_y = dialog_y + 70
            piece_rect = pygame.Rect(piece_x, piece_y, piece_size, piece_size)
            piece_rects.append((piece_rect, piece_type))

            # Draw piece background
            pygame.draw.rect(screen, self.LIGHT_SQUARE, piece_rect)
            pygame.draw.rect(screen, self.RGB_BLACK, piece_rect, 2)

            # Draw piece image or text
            key = f"{color.value}{piece_type.value}"
            if key in self.piece_images:
                # Scale the piece image to fit
                piece_surface = pygame.transform.smoothscale(self.piece_images[key], (piece_size - 10, piece_size - 10))
                piece_x_centered = piece_x + (piece_size - piece_surface.get_width()) // 2
                piece_y_centered = piece_y + (piece_size - piece_surface.get_height()) // 2
                screen.blit(piece_surface, (piece_x_centered, piece_y_centered))
            else:
                # Fallback to text
                piece_text = piece_type.value
                text_surface = self.font_large.render(piece_text, True, self.RGB_BLACK)
                text_rect = text_surface.get_rect(center=piece_rect.center)
                screen.blit(text_surface, text_rect)

        pygame.display.flip()

        # Wait for user selection
        while True:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    for piece_rect, piece_type in piece_rects:
                        if piece_rect.collidepoint(mouse_pos):
                            return piece_type
                elif event.type == pygame.KEYDOWN:
                    # Keyboard shortcuts
                    if event.key == pygame.K_q:
                        return PieceType.QUEEN
                    elif event.key == pygame.K_r:
                        return PieceType.ROOK
                    elif event.key == pygame.K_b:
                        return PieceType.BISHOP
                    elif event.key == pygame.K_n:
                        return PieceType.KNIGHT
                    elif event.key == pygame.K_ESCAPE:
                        return PieceType.QUEEN  # Default to queen

    def _load_settings(self) -> None:
        """Load checkbox states from settings file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)

                # Update help options with saved states
                for option in self.help_options:
                    key = option["key"]
                    if key in settings:
                        option["enabled"] = settings[key]
        except (json.JSONDecodeError, IOError):
            # If settings file is corrupted or unreadable, continue with defaults
            pass

    def _save_settings(self) -> None:
        """Save checkbox states to settings file"""
        try:
            settings = {}
            for option in self.help_options:
                settings[option["key"]] = option["enabled"]

            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except IOError:
            # If we can't save settings, continue silently (don't crash the game)
            pass

    def quit(self) -> None:
        """Clean up Pygame resources"""
        pygame.quit()

# Example usage
if __name__ == "__main__":
    from chess_board import BoardState
    
    # Initialize pygame and create screen
    pygame.init()
    screen = pygame.display.set_mode((1000, 700))
    pygame.display.set_caption("Chess Game - Example")
    
    # Create display and board
    display = ChessDisplay(1000, 700)
    board = BoardState()
    
    # Simple display loop
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Update display
        display.update_display(screen, board)
        pygame.display.flip()
        clock.tick(60)
    
    display.quit()
