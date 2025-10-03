"""
Test positions for tactical pattern detection.

Each position is crafted to demonstrate a specific tactical pattern
with minimal piece complexity for clear testing.
"""

import chess

# Test positions organized by tactical pattern
TACTICAL_TEST_POSITIONS = {

    # ========== HANGING PIECES ==========
    'hanging_pieces': {
        'undefended_knight': {
            'fen': 'rnbqkb1r/pppppppp/5n2/8/8/8/PPPPPPPP/RNBQKB1R w KQkq - 0 1',
            'description': 'Black knight on f6 is undefended',
            'expected_white_hanging': [],
            'expected_black_hanging': [chess.F6],  # f6 knight hanging
        },
        'defended_queen': {
            'fen': 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPPQPPP/RNB1KBNR b KQkq - 0 1',
            'description': 'White queen on e2 defended by king',
            'expected_white_hanging': [],
            'expected_black_hanging': [chess.E5],  # e5 pawn undefended
        },
        'multiple_hanging': {
            'fen': 'r1bqkb1r/pppp1ppp/2n5/4p3/2n1P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1',
            'description': 'Both black knights undefended',
            'expected_white_hanging': [],
            'expected_black_hanging': [chess.C6, chess.C4],  # Both knights
        },
    },

    # ========== PINS ==========
    'pins': {
        'absolute_pin_bishop': {
            'fen': 'r1bqk2r/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1',
            'description': 'Black bishop on c5 pinned by white bishop on c4',
            'expected_white_pinned': [],
            'expected_black_pinned': [chess.C5],  # c5 bishop pinned to king
        },
        'knight_pinned_to_queen': {
            'fen': 'r1bqkb1r/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1',
            'description': 'Black knight on c6 pinned by white bishop',
            'expected_white_pinned': [],
            'expected_black_pinned': [chess.C6],  # c6 knight pinned
        },
        'rook_file_pin': {
            'fen': '4k3/8/8/8/4r3/4N3/4R3/4K3 w - - 0 1',
            'description': 'White knight on e3 pinned by black rook',
            'expected_white_pinned': [chess.E3],  # e3 knight pinned to king
            'expected_black_pinned': [],
        },
    },

    # ========== SKEWERS ==========
    'skewers': {
        'rook_skewer_king_rook': {
            'fen': '4k3/8/8/8/8/8/4R3/4K2R w - - 0 1',
            'description': 'Black king skewered, rook behind',
            'expected_white_skewered': [],
            'expected_black_skewered': [chess.E8],  # King skewered (rook e2 attacks)
        },
        'bishop_skewer_queen_rook': {
            'fen': 'r3kb1r/ppppqppp/8/8/8/8/PPPP1PPP/RNBQKB1R w KQkq - 0 1',
            'description': 'Black queen skewered by potential Bf1-c4',
            'expected_white_skewered': [],
            'expected_black_skewered': [],  # Not yet skewered (needs move)
        },
        'queen_skewer_rook_bishop': {
            'fen': '4k3/8/8/r2b4/8/8/3Q4/4K3 w - - 0 1',
            'description': 'Black rook on a5 skewered to bishop on d5',
            'expected_white_skewered': [],
            'expected_black_skewered': [chess.A5],  # Rook skewered
        },
    },

    # ========== PAWN PATTERNS ==========
    'pawn_patterns': {
        'isolated_pawns': {
            'fen': 'rnbqkbnr/pp1p1ppp/8/2p1p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1',
            'description': 'Black c5 and e5 pawns are isolated',
            'expected_white_isolated': [],
            'expected_black_isolated': [chess.C5, chess.E5],
        },
        'doubled_pawns': {
            'fen': 'rnbqkbnr/ppp2ppp/3p4/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1',
            'description': 'Black has doubled pawns on d-file',
            'expected_white_doubled': [],
            'expected_black_doubled': [chess.D6, chess.E5],  # If e-pawn was on e6
        },
        'passed_pawns': {
            'fen': 'rnbqkbnr/ppp2ppp/8/3pp3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1',
            'description': 'White e4 pawn is passed',
            'expected_white_passed': [chess.E4],
            'expected_black_passed': [],
        },
        'backward_pawns': {
            'fen': 'rnbqkbnr/pp2pppp/2p5/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 1',
            'description': 'Black c6 pawn is backward',
            'expected_white_backward': [],
            'expected_black_backward': [chess.C6],
        },
    },

    # ========== ATTACKED PIECES ==========
    'attacked_pieces': {
        'queen_under_attack': {
            'fen': 'rnbqkb1r/pppppppp/5n2/8/8/5N2/PPPPQPPP/RNB1KB1R b KQkq - 0 1',
            'description': 'White queen attacked by black knight',
            'expected_white_attacked': [chess.E2],  # Queen attacked
            'expected_black_attacked': [],
        },
        'multiple_attacks': {
            'fen': 'r1bqkb1r/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1',
            'description': 'Black knight and f7 pawn attacked',
            'expected_white_attacked': [],
            'expected_black_attacked': [chess.C6, chess.F7],  # Knight and f7
        },
    },

    # ========== COMPLEX POSITIONS ==========
    'complex': {
        'typical_opening': {
            'fen': 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R b KQkq - 0 1',
            'description': 'Italian Game position with multiple tactical elements',
            'expected_white_hanging': [],
            'expected_black_hanging': [],
            'expected_white_pinned': [],
            'expected_black_pinned': [],
            'expected_white_attacked': [],
            'expected_black_attacked': [chess.F7],  # f7 pawn attacked
        },
        'endgame_pawn_structure': {
            'fen': '4k3/pp3pp1/2p2p2/3p4/3P4/2P2P2/PP3PP1/4K3 w - - 0 1',
            'description': 'Complex pawn structure with multiple patterns',
            'expected_white_isolated': [],
            'expected_black_isolated': [chess.D5],  # d5 isolated
            'expected_white_passed': [],
            'expected_black_passed': [],
        },
    },
}


def print_board(fen: str):
    """Pretty print a chess board from FEN."""
    board = chess.Board(fen)
    print(board)
    print(f"\nFEN: {fen}\n")


def test_position(category: str, name: str, position_data: dict):
    """Test a single position."""
    print(f"\n{'='*70}")
    print(f"Testing: {category} / {name}")
    print(f"Description: {position_data['description']}")
    print('='*70)

    fen = position_data['fen']
    print_board(fen)

    # Load position
    board = chess.Board(fen)

    # Print expected results
    print("Expected Results:")
    for key, value in position_data.items():
        if key.startswith('expected_'):
            pattern = key.replace('expected_', '')
            squares = [chess.square_name(sq) for sq in value] if value else []
            print(f"  {pattern}: {squares}")

    return board


if __name__ == "__main__":
    import sys

    # Test specific category or all
    if len(sys.argv) > 1:
        category = sys.argv[1]
        if category in TACTICAL_TEST_POSITIONS:
            for name, pos_data in TACTICAL_TEST_POSITIONS[category].items():
                test_position(category, name, pos_data)
    else:
        # Test all positions
        for category, positions in TACTICAL_TEST_POSITIONS.items():
            for name, pos_data in positions.items():
                test_position(category, name, pos_data)
                input("\nPress Enter to continue...")
