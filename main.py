import pygame
import sys
from chess_board import BoardState
from display import ChessDisplay
from config import GameConfig, Colors
from sound_manager import get_sound_manager

# Set window behavior before pygame init (removed problematic positioning)

# Initialize Pygame
pygame.init()

# Get screen dimensions and calculate window size
screen_info = pygame.display.Info()
SCREEN_WIDTH = screen_info.current_w
SCREEN_HEIGHT = screen_info.current_h

# Calculate window size using config values
WINDOW_HEIGHT = int(min(SCREEN_WIDTH * GameConfig.SCREEN_SIZE_PERCENTAGE,
                       SCREEN_HEIGHT * GameConfig.SCREEN_SIZE_PERCENTAGE))
WINDOW_WIDTH = int(WINDOW_HEIGHT * GameConfig.WINDOW_ASPECT_RATIO)

# Create display
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Blundex")


# Initialize sound system
sound_manager = get_sound_manager()

# Create global board state in starting position
board_state = BoardState()

# Create display object
display = ChessDisplay(WINDOW_WIDTH, WINDOW_HEIGHT)

# Font setup using config values - modern system font (for any UI text if needed)
font_size = int(WINDOW_WIDTH * GameConfig.FONT_BUTTON_PERCENTAGE)
try:
    font = pygame.font.SysFont('segoeui,arial,helvetica,sans-serif', font_size, bold=False)
except:
    font = pygame.font.Font(None, font_size)

# Game state
selected_square_coords = None
highlighted_moves = []


# Drag state
dragging_piece = None  # The piece being dragged
drag_origin = None     # Original square coordinates

# Rendering optimization
needs_redraw = True  # Initially need to draw
last_hovered_square = None  # Track which board square mouse is over
last_hover_was_legal = False  # Was the last hovered square a legal move?

# Help panel state
show_help_panel = False


# Main game loop
is_running = True
clock = pygame.time.Clock()

while is_running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if show_help_panel:
                    show_help_panel = False
                    needs_redraw = True
                else:
                    is_running = False
            elif event.key == pygame.K_b:  # B key to toggle flip board
                display.toggle_help_option("flip_board")
                needs_redraw = True
            elif event.key == pygame.K_u:  # U key to undo
                if board_state.can_undo():
                    success = board_state.undo_move()
                    if success:
                        # Clear any current selection
                        selected_square_coords = None
                        highlighted_moves = []
                        needs_redraw = True
                    else:
                        sound_manager.play_error_sound()
                else:
                    sound_manager.play_error_sound()
            elif event.key == pygame.K_r:  # R key to redo
                if board_state.can_redo():
                    success = board_state.redo_move()
                    if success:
                        # Clear any current selection
                        selected_square_coords = None
                        highlighted_moves = []
                        needs_redraw = True
                    else:
                        sound_manager.play_error_sound()
                else:
                    sound_manager.play_error_sound()
            elif event.key == pygame.K_h:  # H key to toggle hanging pieces
                display.toggle_help_option("hanging_pieces")
                needs_redraw = True
            elif event.key == pygame.K_e:  # E key to toggle exchange evaluation
                display.toggle_help_option("exchange_evaluation")
                needs_redraw = True
            elif event.key == pygame.K_SLASH:  # Slash (/) key to show help
                show_help_panel = not show_help_panel
                needs_redraw = True
            elif event.key == pygame.K_BACKQUOTE:  # Tilde key (~) to reset game
                board_state.reset_to_initial_position()
                # Clear any current selection and highlights
                selected_square_coords = None
                highlighted_moves = []
                dragging_piece = None
                drag_origin = None
                # Reset hover states
                last_hovered_square = None
                last_hover_was_legal = False
                needs_redraw = True
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Check if a help checkbox was clicked
            checkbox_key = display.get_checkbox_at_pos(mouse_pos)
            if checkbox_key:
                display.toggle_help_option(checkbox_key)
                needs_redraw = True
            else:
                # Handle board clicks for piece selection/movement
                square = display.get_square_from_mouse(mouse_pos)
                if square:
                    # Convert square coordinates if board is flipped
                    if display.is_help_option_enabled("flip_board"):
                        square = (7 - square[0], 7 - square[1])

                    if selected_square_coords is None:
                        # Start dragging a piece
                        piece = board_state.get_piece(square[0], square[1])
                        if piece and piece.color == board_state.current_turn:
                            # Set up drag state
                            dragging_piece = piece
                            drag_origin = square
                            selected_square_coords = square

                            # Calculate possible moves for the selected piece
                            highlighted_moves = board_state.get_possible_moves(square[0], square[1])
                            # Reset hover state since highlighted_moves changed
                            last_hovered_square = None
                            last_hover_was_legal = False
                            needs_redraw = True
                    else:
                            # Try to move the piece
                            if square in highlighted_moves:
                                # Check if this is a pawn promotion
                                if board_state.is_pawn_promotion(selected_square_coords[0], selected_square_coords[1], square[0], square[1]):
                                    # Show promotion dialog
                                    current_piece = board_state.get_piece(selected_square_coords[0], selected_square_coords[1])
                                    promotion_piece = display.show_promotion_dialog(screen, current_piece.color)

                                    # Execute the move with promotion
                                    move_successful = board_state.make_move_with_promotion(
                                        selected_square_coords[0], selected_square_coords[1],
                                        square[0], square[1], promotion_piece
                                    )
                                    if not move_successful:
                                        sound_manager.play_error_sound()
                                else:
                                    # Execute regular move
                                    move_successful = board_state.make_move(
                                        selected_square_coords[0], selected_square_coords[1],
                                        square[0], square[1]
                                    )
                                    if not move_successful:
                                        sound_manager.play_error_sound()

                                # Clear selection regardless
                                selected_square_coords = None
                                highlighted_moves = []
                                display.invalidate_activity_cache()  # Invalidate cache when move is made
                                # Reset hover state since highlighted_moves changed
                                last_hovered_square = None
                                last_hover_was_legal = False
                                needs_redraw = True
                            elif square == selected_square_coords:
                                # Deselect
                                selected_square_coords = None
                                highlighted_moves = []
                                # Reset hover state since highlighted_moves changed
                                last_hovered_square = None
                                last_hover_was_legal = False
                                needs_redraw = True
                            else:
                                # Select different piece
                                piece = board_state.get_piece(square[0], square[1])
                                if piece and piece.color == board_state.current_turn:
                                    selected_square_coords = square
                                    highlighted_moves = board_state.get_possible_moves(square[0], square[1])
                                    # Reset hover state since highlighted_moves changed
                                    last_hovered_square = None
                                    last_hover_was_legal = False
                                    needs_redraw = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if dragging_piece and drag_origin:
                # Complete the drag operation
                mouse_pos = pygame.mouse.get_pos()
                target_square = display.get_square_from_mouse(mouse_pos)

                if target_square:
                    # Convert square coordinates if board is flipped
                    if display.is_help_option_enabled("flip_board"):
                        target_square = (7 - target_square[0], 7 - target_square[1])

                    # Try to complete the move
                    if target_square in highlighted_moves:
                        # Check if this is a pawn promotion
                        if board_state.is_pawn_promotion(drag_origin[0], drag_origin[1], target_square[0], target_square[1]):
                            # Show promotion dialog
                            promotion_piece = display.show_promotion_dialog(screen, dragging_piece.color)
                            # Execute the move with promotion
                            move_successful = board_state.make_move_with_promotion(
                                drag_origin[0], drag_origin[1],
                                target_square[0], target_square[1], promotion_piece
                            )
                        else:
                            # Execute regular move
                            move_successful = board_state.make_move(
                                drag_origin[0], drag_origin[1],
                                target_square[0], target_square[1]
                            )

                # Reset drag state regardless of whether move was successful
                dragging_piece = None
                drag_origin = None
                selected_square_coords = None
                highlighted_moves = []
                display.invalidate_activity_cache()  # Invalidate cache when move is made
                last_hovered_square = None
                last_hover_was_legal = False
                needs_redraw = True

    # Check for smart hover detection (only redraw when entering/leaving legal move squares)
    current_mouse_pos = pygame.mouse.get_pos()

    # Get current square under mouse
    current_hovered_square = display.get_square_from_mouse(current_mouse_pos)
    if current_hovered_square and display.is_help_option_enabled("flip_board"):
        current_hovered_square = (7 - current_hovered_square[0], 7 - current_hovered_square[1])

    # Check if current hover is over a legal move square
    current_hover_is_legal = (current_hovered_square in highlighted_moves) if current_hovered_square else False

    # Create preview board state if hovering over a legal move
    preview_board_state = None
    if current_hover_is_legal and selected_square_coords:
        # Create a copy of the board state for preview
        preview_board_state = board_state.copy()

        # Execute the candidate move on the preview board
        from_row, from_col = selected_square_coords
        to_row, to_col = current_hovered_square
        preview_board_state.make_move(from_row, from_col, to_row, to_col)

    # Only redraw if hover state changed in a meaningful way
    hover_state_changed = (
        current_hovered_square != last_hovered_square or  # Different square
        current_hover_is_legal != last_hover_was_legal    # Legal status changed
    )

    if hover_state_changed:
        last_hovered_square = current_hovered_square
        last_hover_was_legal = current_hover_is_legal
        needs_redraw = True


    # Force redraws during animations (temporarily return to continuous rendering)
    if display.is_animation_active():
        needs_redraw = True

    # Only redraw if something changed
    if needs_redraw:
        # Draw the chess board (with flip consideration)
        current_mouse_pos = pygame.mouse.get_pos()
        display.update_display(screen, board_state, selected_square_coords, highlighted_moves, display.is_help_option_enabled("flip_board"), preview_board_state, dragging_piece, drag_origin, current_mouse_pos)

        # Draw dragged piece snapped to square center
        if dragging_piece:
            display.draw_dragged_piece(screen, dragging_piece, current_mouse_pos, display.is_help_option_enabled("flip_board"))


        # Draw help panel if requested
        if show_help_panel:
            display.draw_keyboard_shortcuts_panel(screen)

        # Update the display
        pygame.display.flip()
        needs_redraw = False

    # Much lower CPU usage - only check for events frequently
    clock.tick(30)  # Reduced from 60 FPS to 30 FPS

# Quit Pygame
pygame.quit()
sys.exit()
