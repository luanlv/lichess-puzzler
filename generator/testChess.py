#!/usr/bin/env python3
#
# This file is part of the python-chess library.
# Copyright (C) 2012-2020 Niklas Fiekas <niklas.fiekas@backscattering.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import copy
import logging
import os
import os.path
import platform
import sys
import tempfile
import textwrap
import unittest
import io

import chess
import chess.engine
import chess.pgn
import chess.polyglot
import chess.svg
import chess.syzygy
import chess.variant


class RaiseLogHandler(logging.StreamHandler):
    def handle(self, record):
        super().handle(record)
        raise RuntimeError("was expecting no log messages")


def catchAndSkip(signature, message=None):
    def _decorator(f):
        def _wrapper(self):
            try:
                return f(self)
            except signature as err:
                raise unittest.SkipTest(message or err)
        return _wrapper
    return _decorator


class SquareTestCase(unittest.TestCase):

    def test_square(self):
        for square in chess.SQUARES:
            file_index = chess.square_file(square)
            rank_index = chess.square_rank(square)
            self.assertEqual(chess.square(file_index, rank_index), square, chess.square_name(square))

    def test_shifts(self):
        shifts = [
            chess.shift_down,
            chess.shift_2_down,
            chess.shift_up,
            chess.shift_2_up,
            chess.shift_right,
            chess.shift_2_right,
            chess.shift_left,
            chess.shift_2_left,
            chess.shift_up_left,
            chess.shift_up_right,
            chess.shift_down_left,
            chess.shift_down_right,
        ]

        for shift in shifts:
            for bb_square in chess.BB_SQUARES:
                shifted = shift(bb_square)
                # print(shifted)
                c = chess.popcount(shifted)
                self.assertLessEqual(c, 1)
                self.assertEqual(c, chess.popcount(chess.bitwise_and(shifted, chess.BB_ALL)))

    def test_parse_square(self):
        self.assertEqual(chess.parse_square("a0"), 0)
        self.assertEqual(chess.parse_square("i0"), 8)
        self.assertEqual(chess.parse_square("a9"), 81)
        self.assertEqual(chess.parse_square("i9"), 89)

class MoveTestCase(unittest.TestCase):
#
    def test_equality(self):
        a = chess.Move(chess.A1, chess.A2)
        b = chess.Move(chess.A1, chess.A2)
        c = chess.Move(chess.H7, chess.H8, chess.BISHOP)
        d1 = chess.Move(chess.H7, chess.H8)
        d2 = chess.Move(chess.H7, chess.H8)

        self.assertEqual(a, b)
        self.assertEqual(b, a)
        self.assertEqual(d1, d2)

        self.assertNotEqual(a, c)
        self.assertNotEqual(c, d1)
        self.assertNotEqual(b, d1)
        self.assertFalse(d1 != d2)
#
    def test_uci_parsing(self):
        self.assertEqual(chess.Move.from_uci("b5c7").uci(), "b5c7")
        self.assertEqual(chess.Move.from_uci("e7e8q").uci(), "e7e8")
        self.assertEqual(chess.Move.from_uci("P@e4").uci(), "P@e4")
        self.assertEqual(chess.Move.from_uci("B@f4").uci(), "B@f4")
        self.assertEqual(chess.Move.from_uci("0000").uci(), "0000")
#
    def test_invalid_uci(self):
        with self.assertRaises(ValueError):
            chess.Move.from_uci("")

        with self.assertRaises(ValueError):
            chess.Move.from_uci("N")

        with self.assertRaises(ValueError):
            chess.Move.from_uci("z1g3")

        with self.assertRaises(ValueError):
            chess.Move.from_uci("Q@g9")
#
    # def test_xboard_move(self):
    #     print(chess.Move.from_uci("b5c7").xboard())
        # self.assertEqual(chess.Move.from_uci("b5c7").xboard(), "b5c7")
#         self.assertEqual(chess.Move.from_uci("e7e8q").xboard(), "e7e8q")
#         self.assertEqual(chess.Move.from_uci("P@e4").xboard(), "P@e4")
#         self.assertEqual(chess.Move.from_uci("B@f4").xboard(), "B@f4")
#         self.assertEqual(chess.Move.from_uci("0000").xboard(), "@@@@")
#
    def test_copy(self):
        a = chess.Move.from_uci("N@f3")
        b = chess.Move.from_uci("a1h8")
        c = chess.Move.from_uci("g7g8r")
        self.assertEqual(copy.copy(a), a)
        self.assertEqual(copy.copy(b), b)
        self.assertEqual(copy.copy(c), c)
#
#
class PieceTestCase(unittest.TestCase):

    def test_equality(self):
        a = chess.Piece(chess.BISHOP, chess.WHITE)
        b = chess.Piece(chess.KING, chess.BLACK)
        c = chess.Piece(chess.KING, chess.WHITE)
        d1 = chess.Piece(chess.BISHOP, chess.WHITE)
        d2 = chess.Piece(chess.BISHOP, chess.WHITE)

        self.assertEqual(len(set([a, b, c, d1, d2])), 3)
#
        self.assertEqual(a, d1)
        self.assertEqual(d1, a)
        self.assertEqual(d1, d2)
#
        self.assertEqual(repr(a), repr(d1))

        self.assertNotEqual(a, b)
        self.assertNotEqual(b, c)
        self.assertNotEqual(b, d1)
        self.assertNotEqual(a, c)
        self.assertFalse(d1 != d2)

        self.assertNotEqual(repr(a), repr(b))
        self.assertNotEqual(repr(b), repr(c))
        self.assertNotEqual(repr(b), repr(d1))
        self.assertNotEqual(repr(a), repr(c))
#
    def test_from_symbol(self):
        white_knight = chess.Piece.from_symbol("N")

        self.assertEqual(white_knight.color, chess.WHITE)
        self.assertEqual(white_knight.piece_type, chess.KNIGHT)
        self.assertEqual(white_knight.symbol(), "N")
        self.assertEqual(str(white_knight), "N")

        black_advisor = chess.Piece.from_symbol("a")

        self.assertEqual(black_advisor.color, chess.BLACK)
        self.assertEqual(black_advisor.piece_type, chess.ADVISOR)
        self.assertEqual(black_advisor.symbol(), "a")
        self.assertEqual(str(black_advisor), "a")

#
class BoardTestCase(unittest.TestCase):

    def test_default_position(self):
        board = chess.Board()
        self.assertEqual(board.piece_at(chess.A0), chess.Piece.from_symbol("R"))
        # self.assertEqual(board.piece_at(chess.B0), chess.Piece.from_symbol("R"))
        # print(board.fen())
        self.assertEqual(board.fen(), chess.STARTING_FEN)

        # self.assertEqual(board.turn, chess.WHITE)
#
    def test_empty(self):
        board = chess.Board.empty()
        self.assertEqual(board.fen(), "9/9/9/9/9/9/9/9/9/9 w 1")
        # print(board)
        # print(chess.Board(None))
        # self.assertEqual(board, chess.Board(None)) #need fix
#
    def test_ply(self):
        board = chess.Board()
        fen = "4kab2/4a4/4c4/p7p/2R1R4/P8/9/4p3r/9/3AKC1r1 b 37"
        board.set_fen(fen)
        # self.assertEqual(board.ply(), 0)
        board.push_san("Pe2f2")
        # self.assertEqual(board.ply(), 1)
        # board.push_san("a9a8")
        # self.assertEqual(board.ply(), 2)
        # board.clear_stack()
        # self.assertEqual(board.ply(), 2)
        # board.push_san("Ke0e1")
        # self.assertEqual(board.ply(), 3)
#
    # def test_from_epd(self):
        base_epd = "rnbqkb1r/ppp1pppp/5n2/3P4/8/8/PPPP1PPP/RNBQKBNR w KQkq -"
#         board, ops = chess.Board.from_epd(base_epd + " ce 55;")
#         self.assertEqual(ops["ce"], 55)
#         self.assertEqual(board.fen(), base_epd + " 0 1")
#
    def test_move_making(self):
        board = chess.Board()
        move = chess.Move(chess.B2, chess.B9)
        board.push(move)
        self.assertEqual(board.peek(), move)
#
    def test_fen(self):
        board = chess.Board()
        self.assertEqual(board.fen(), chess.STARTING_FEN)
#
        fen = "rnbakabnr/9/1c4c2/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/4K4/RNBA1ABNR w 1"
        board.set_fen(fen)
        self.assertEqual(board.fen(), fen)
#
        board.push(chess.Move.from_uci("b2e2"))
        self.assertEqual(board.fen(), "rnbakabnr/9/1c4c2/p1p1p1p1p/9/9/P1P1P1P1P/4C2C1/4K4/RNBA1ABNR b 1")

    def test_get_set(self):
        board = chess.Board()
        self.assertEqual(board.piece_at(chess.B0), chess.Piece.from_symbol("N"))
#
        board.remove_piece_at(chess.B0)
        self.assertEqual(board.piece_at(chess.B0), None)
#
        board.set_piece_at(chess.B1, chess.Piece.from_symbol("r"))
        self.assertEqual(board.piece_type_at(chess.B1), chess.ROOK)
#
        board.set_piece_at(chess.A0, None)
        self.assertEqual(board.piece_at(chess.A0), None)
#
#         board.set_piece_at(chess.H7, chess.Piece.from_symbol("Q"), promoted=True)
#         self.assertEqual(board.promoted, chess.BB_H7)
#
#         board.set_piece_at(chess.H7, None)
#         self.assertEqual(board.promoted, chess.BB_EMPTY)


    def test_color_at(self):
        board = chess.Board()
        print(board.fen())
        print(board.color_at(chess.E0))
        self.assertEqual(board.color_at(chess.E0), chess.WHITE)
        self.assertEqual(board.color_at(chess.E9), chess.BLACK)
        self.assertEqual(board.color_at(chess.E8), None)

    def test_find_move(self):
        board = chess.Board("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1")
        self.assertEqual(board.find_move(chess.A0, chess.A2), chess.Move.from_uci("a0a2"))
        board.push(chess.Move.from_uci("a0a2"))
        self.assertEqual(board.find_move(chess.E9, chess.E8), chess.Move.from_uci("e9e8"))
        board.push(chess.Move.from_uci("e9e8"))
        self.assertEqual(board.find_move(chess.B0, chess.C2), chess.Move.from_uci("b0c2"))
#
        # Illegal moves.
        with self.assertRaises(ValueError):
            board.find_move(chess.D2, chess.D8)
        with self.assertRaises(ValueError):
            board.find_move(chess.E1, chess.A1)



#     def test_insufficient_material(self):
#         def _check(board, white, black):
#             self.assertEqual(board.has_insufficient_material(chess.WHITE), white)
#             self.assertEqual(board.has_insufficient_material(chess.BLACK), black)
#             self.assertEqual(board.is_insufficient_material(), white and black)
#
#         # Imperfect implementation.
#         false_negative = False
#
#         _check(chess.Board(), False, False)
#         _check(chess.Board("k1K1B1B1/8/8/8/8/8/8/8 w - - 7 32"), True, True)
#         _check(chess.Board("kbK1B1B1/8/8/8/8/8/8/8 w - - 7 32"), False, False)
#         _check(chess.Board("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), True, True)
#         _check(chess.Board("8/3k4/8/8/2N5/8/3K4/8 b - - 0 1"), True, True)
#         _check(chess.Board("8/4rk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
#         _check(chess.Board("8/4qk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
#         _check(chess.Board("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
#         _check(chess.Board("8/8/3Q4/2bK4/B7/8/1k6/8 w - - 1 68"), False, False)
#         _check(chess.Board("8/5k2/8/8/8/4B3/3K1B2/8 w - - 0 1"), True, True)
#         _check(chess.Board("5K2/8/8/1B6/8/k7/6b1/8 w - - 0 39"), True, True)
#         _check(chess.Board("8/8/8/4k3/5b2/3K4/8/2B5 w - - 0 33"), True, True)
#         _check(chess.Board("3b4/8/8/6b1/8/8/R7/K1k5 w - - 0 1"), False, True)
#
#         _check(chess.variant.AtomicBoard("8/3k4/8/8/2N5/8/3K4/8 b - - 0 1"), True, True)
#         _check(chess.variant.AtomicBoard("8/4rk2/8/8/8/8/3K4/8 w - - 0 1"), True, True)
#         _check(chess.variant.AtomicBoard("8/4qk2/8/8/8/8/3K4/8 w - - 0 1"), True, False)
#         _check(chess.variant.AtomicBoard("8/1k6/8/2n5/8/3NK3/8/8 b - - 0 1"), False, False)
#         _check(chess.variant.AtomicBoard("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), True, True)
#         _check(chess.variant.AtomicBoard("4b3/5k2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
#         _check(chess.variant.AtomicBoard("3Q4/5kKB/8/8/8/8/8/8 b - - 0 1"), False, True)
#         _check(chess.variant.AtomicBoard("8/5k2/8/8/8/8/5K2/4bb2 w - - 0 1"), True, False)
#         _check(chess.variant.AtomicBoard("8/5k2/8/8/8/8/5K2/4nb2 w - - 0 1"), True, False)
#
#         _check(chess.variant.GiveawayBoard("8/4bk2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
#         _check(chess.variant.GiveawayBoard("4b3/5k2/8/8/8/8/3KB3/8 w - - 0 1"), False, False)
#         _check(chess.variant.GiveawayBoard("8/8/8/6b1/8/3B4/4B3/5B2 w - - 0 1"), True, True)
#         _check(chess.variant.GiveawayBoard("8/8/5b2/8/8/3B4/3B4/8 w - - 0 1"), True, False)
#         _check(chess.variant.SuicideBoard("8/5p2/5P2/8/3B4/1bB5/8/8 b - - 0 1"), false_negative, false_negative)
#
#         _check(chess.variant.KingOfTheHillBoard("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), False, False)
#
#         _check(chess.variant.RacingKingsBoard("8/5k2/8/8/8/8/3K4/8 w - - 0 1"), False, False)
#
#         _check(chess.variant.ThreeCheckBoard("8/5k2/8/8/8/8/3K4/8 w - - 3+3 0 1"), True, True)
#         _check(chess.variant.ThreeCheckBoard("8/5k2/8/8/8/8/3K2N1/8 w - - 3+3 0 1"), False, True)
#
#         _check(chess.variant.CrazyhouseBoard("8/5k2/8/8/8/8/3K2N1/8[] w - - 0 1"), True, True)
#         _check(chess.variant.CrazyhouseBoard("8/5k2/8/8/8/5B2/3KB3/8[] w - - 0 1"), False, False)
#         _check(chess.variant.CrazyhouseBoard("8/8/8/8/3k4/3N~4/3K4/8 w - - 0 1"), False, False)
#
#         _check(chess.variant.HordeBoard("8/5k2/8/8/8/4NN2/8/8 w - - 0 1"), false_negative, False)
#


    # def test_result(self):
#         # Undetermined.
#         board = chess.Board()
        # self.assertEqual(board.result(claim_draw=True), "*")
#
#         # White checkmated.
#         board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        # self.assertEqual(board.result(claim_draw=True), "0-1")
#
#         # Stalemate.
#         board = chess.Board("7K/7P/7k/8/6q1/8/8/8 w - - 0 1")
#         self.assertEqual(board.result(), "1/2-1/2")
#
#         # Insufficient material.
#         board = chess.Board("4k3/8/8/8/8/5B2/8/4K3 w - - 0 1")
#         self.assertEqual(board.result(), "1/2-1/2")
#
#         # Fiftyseven-move rule.
#         board = chess.Board("4k3/8/6r1/8/8/8/2R5/4K3 w - - 369 1")
#         self.assertEqual(board.result(), "1/2-1/2")
#
#         # Fifty-move rule.
#         board = chess.Board("4k3/8/6r1/8/8/8/2R5/4K3 w - - 120 1")
#         self.assertEqual(board.result(), "*")
#         self.assertEqual(board.result(claim_draw=True), "1/2-1/2")
#
#     def test_san(self):
# #         # Castling with check.
#         fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1"
#         board = chess.Board(fen)
        # long_castle_check = chess.Move.from_uci("e1a1")
#         self.assertEqual(board.san(long_castle_check), "O-O-O+")
#         self.assertEqual(board.fen(), fen)
#
#         # En passant mate.
#         fen = "6bk/7b/8/3pP3/8/8/8/Q3K3 w - d6 0 2"
#         board = chess.Board(fen)
#         fxe6_mate_ep = chess.Move.from_uci("e5d6")
#         self.assertEqual(board.san(fxe6_mate_ep), "exd6#")
#         self.assertEqual(board.fen(), fen)
#
#         # Test disambiguation.
#         fen = "N3k2N/8/8/3N4/N4N1N/2R5/1R6/4K3 w - - 0 1"
#         board = chess.Board(fen)
#         self.assertEqual(board.san(chess.Move.from_uci("e1f1")), "Kf1")
#         self.assertEqual(board.san(chess.Move.from_uci("c3c2")), "Rcc2")
#         self.assertEqual(board.san(chess.Move.from_uci("b2c2")), "Rbc2")
#         self.assertEqual(board.san(chess.Move.from_uci("a4b6")), "N4b6")
#         self.assertEqual(board.san(chess.Move.from_uci("h8g6")), "N8g6")
#         self.assertEqual(board.san(chess.Move.from_uci("h4g6")), "Nh4g6")
#         self.assertEqual(board.fen(), fen)
#
#         # Do not disambiguate illegal alternatives.
#         fen = "8/8/8/R2nkn2/8/8/2K5/8 b - - 0 1"
#         board = chess.Board(fen)
#         self.assertEqual(board.san(chess.Move.from_uci("f5e3")), "Ne3+")
#         self.assertEqual(board.fen(), fen)
#
#
#     def test_lan(self):
#         # Normal moves always with origin square.
#         fen = "N3k2N/8/8/3N4/N4N1N/2R5/1R6/4K3 w - - 0 1"
#         board = chess.Board(fen)
#         self.assertEqual(board.lan(chess.Move.from_uci("e1f1")), "Ke1-f1")
#         self.assertEqual(board.lan(chess.Move.from_uci("c3c2")), "Rc3-c2")
#         self.assertEqual(board.lan(chess.Move.from_uci("a4c5")), "Na4-c5")
#         self.assertEqual(board.fen(), fen)
#
#         # Normal capture.
#         fen = "rnbq1rk1/ppp1bpp1/4pn1p/3p2B1/2PP4/2N1PN2/PP3PPP/R2QKB1R w KQ - 0 7"
#         board = chess.Board(fen)
#         self.assertEqual(board.lan(chess.Move.from_uci("g5f6")), "Bg5xf6")
#         self.assertEqual(board.fen(), fen)
#
#         # Pawn captures and moves.
#         fen = "6bk/7b/8/3pP3/8/8/8/Q3K3 w - d6 0 2"
#         board = chess.Board(fen)
#         self.assertEqual(board.lan(chess.Move.from_uci("e5d6")), "e5xd6#")
#         self.assertEqual(board.lan(chess.Move.from_uci("e5e6")), "e5-e6+")
#         self.assertEqual(board.fen(), fen)
#
#     def test_san_newline(self):
#         fen = "rnbqk2r/ppppppbp/5np1/8/8/5NP1/PPPPPPBP/RNBQK2R w KQkq - 2 4"
#         board = chess.Board(fen)
#
#         with self.assertRaises(ValueError):
#             board.parse_san("O-O\n")
#
#         with self.assertRaises(ValueError):
#             board.parse_san("Nc3\n")
#
#     def test_variation_san(self):
#         board = chess.Board()
#         self.assertEqual('1. e4 e5 2. Nf3',
#                          board.variation_san([chess.Move.from_uci(m) for m in
#                                               ['e2e4', 'e7e5', 'g1f3']]))
#         self.assertEqual('1. e4 e5 2. Nf3 Nc6 3. Bb5 a6',
#                          board.variation_san([chess.Move.from_uci(m) for m in
#                                               ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6']]))
#
#         fen = "rn1qr1k1/1p2bppp/p3p3/3pP3/P2P1B2/2RB1Q1P/1P3PP1/R5K1 w - - 0 19"
#         board = chess.Board(fen)
#         variation = ['d3h7', 'g8h7', 'f3h5', 'h7g8', 'c3g3', 'e7f8', 'f4g5',
#                      'e8e7', 'g5f6', 'b8d7', 'h5h6', 'd7f6', 'e5f6', 'g7g6',
#                      'f6e7', 'f8e7']
#         var_w = board.variation_san([chess.Move.from_uci(m) for m in variation])
#         self.assertEqual(("19. Bxh7+ Kxh7 20. Qh5+ Kg8 21. Rg3 Bf8 22. Bg5 Re7 "
#                           "23. Bf6 Nd7 24. Qh6 Nxf6 25. exf6 g6 26. fxe7 Bxe7"),
#                          var_w)
#         self.assertEqual(fen, board.fen(), msg="Board unchanged by variation_san")
#         board.push(chess.Move.from_uci(variation.pop(0)))
#         var_b = board.variation_san([chess.Move.from_uci(m) for m in variation])
#         self.assertEqual(("19...Kxh7 20. Qh5+ Kg8 21. Rg3 Bf8 22. Bg5 Re7 "
#                           "23. Bf6 Nd7 24. Qh6 Nxf6 25. exf6 g6 26. fxe7 Bxe7"),
#                          var_b)
#
#         illegal_variation = ['d3h7', 'g8h7', 'f3h6', 'h7g8']
#         board = chess.Board(fen)
#         with self.assertRaises(ValueError) as err:
#             board.variation_san([chess.Move.from_uci(m) for m in illegal_variation])
#         message = str(err.exception)
#         self.assertIn('illegal move', message.lower(),
#                       msg=f"Error [{message}] mentions illegal move")
#         self.assertIn('f3h6', message,
#                       msg=f"Illegal move f3h6 appears in message [{message}]")
#
    def test_move_stack_usage(self):
        board = chess.Board()
        board.push_uci("a0a1")
        board.push_uci("e9e8")
        board.push_uci("b0c2")
        board.push_uci("a9a8")
        board.push_uci("e0e1")
        board.push_uci("e8e7")
        san = chess.Board().variation_san(board.move_stack)
        self.assertEqual(san, "1. Ra0a1 Ke9e8 2. Nb0c2 Ra9a8 3. Ke0e1 Ke8e7")
#
    def test_is_legal_move(self):
        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1"
        board = chess.Board(fen)
#
#         # Legal moves: Rg1, g8=R+.
        self.assertIn(chess.Move.from_uci("e0e1"), board.legal_moves)
        self.assertIn(chess.Move.from_uci("b2e2"), board.legal_moves)

#
    # def test_move_count(self):
        board = chess.Board("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1")
        # self.assertEqual(board.pseudo_legal_moves.count(), 8 + 4 + 3 + 2 + 1 + 6 + 9)


#     def test_move_generation_bug(self):
# #         # Specific problematic position.
#         fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1"
#         board = chess.Board(fen)
#
#         # Make a move.
#         board.push_san("Ke0e1")
#
#         # Check for the illegal move.
#         illegal_move = chess.Move.from_uci("e9e7")
#         self.assertNotIn(illegal_move, board.pseudo_legal_moves)
#         self.assertNotIn(illegal_move, board.generate_pseudo_legal_moves())
#         self.assertNotIn(illegal_move, board.legal_moves)
#         self.assertNotIn(illegal_move, board.generate_legal_moves())
#
#         # Generate all pseudo-legal moves.
#         for a in board.pseudo_legal_moves:
#             board.push(a)
#             board.pop()
#
#         # Unmake the move.
#         board.pop()
#
#         # Check that board is still consistent.
#         self.assertEqual(board.fen(), fen)
#
#     def test_stateful_move_generation_bug(self):
#         board = chess.Board("r1b1k3/p2p1Nr1/n2b3p/3pp1pP/2BB1p2/P3P2R/Q1P3P1/R3K1N1 b Qq - 0 1")
#         count = 0
#         for move in board.legal_moves:
#             board.push(move)
#             list(board.generate_legal_moves())
#             count += 1
#             board.pop()
#
#         self.assertEqual(count, 26)
#


    def test_equality(self):
        self.assertEqual(chess.Board(), chess.Board())
        self.assertFalse(chess.Board() != chess.Board())

        a = chess.Board()
        a.push_san("b0c2")
        b = chess.Board()
        b.push_san("a0a2")
        self.assertNotEqual(a, b)
        self.assertFalse(a == b)

    def test_status(self):
        board = chess.Board()
        # print(board.status())
        self.assertEqual(board.status(), chess.STATUS_VALID)
        self.assertTrue(board.is_valid())
#

        board.remove_piece_at(chess.E9)
        self.assertTrue(board.status() & chess.STATUS_NO_BLACK_KING)
#
        # Opposite check.
        board = chess.Board("rnbakabnr/9/9/9/9/9/9/9/4R4/1NBAKABNR w 1")
        self.assertEqual(board.status(), chess.STATUS_OPPOSITE_CHECK)
#
        # Empty board.
        board = chess.Board(None)
        self.assertEqual(board.status(), chess.STATUS_EMPTY | chess.STATUS_NO_WHITE_KING | chess.STATUS_NO_BLACK_KING)
#
        # Too many kings.
        board = chess.Board("rnbakabnr/4k4/9/9/9/9/9/9/4R4/1NBAKABNR w 1")
        self.assertEqual(board.status(), chess.STATUS_TOO_MANY_KINGS)
#
#         # Triple check.
#         board = chess.Board("4k3/5P2/3N4/8/8/8/4R3/4K3 b - - 0 1")
#         self.assertEqual(board.status(), chess.STATUS_TOO_MANY_CHECKERS)
#
#     def test_one_king_movegen(self):
#         board = chess.Board.empty()
#         board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
#         self.assertFalse(board.is_valid())
#         self.assertEqual(board.legal_moves.count(), 3)
#         self.assertEqual(board.pseudo_legal_moves.count(), 3)
#         board.push_san("Kb1")
#         self.assertEqual(board.legal_moves.count(), 0)
#         self.assertEqual(board.pseudo_legal_moves.count(), 0)
#         board.push_san("--")
#         self.assertEqual(board.legal_moves.count(), 5)
#         self.assertEqual(board.pseudo_legal_moves.count(), 5)
#
    # def test_epd(self):
        # Create an EPD with a move and a string.
        # board = chess.Board("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - 0 1")
        # epd = board.epd(bm=chess.Move(chess.D6, chess.D1), id="BK.01")
#         self.assertIn(epd, [
#             "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"BK.01\";",
#             "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - id \"BK.01\"; bm Qd1+;"])
#
#         # Create an EPD with a noop.
#         board = chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
#         self.assertEqual(board.epd(noop=None), "4k3/8/8/8/8/8/8/4K3 w - - noop;")
#
#         # Create an EPD with numbers.
#         self.assertEqual(board.epd(pi=3.14), "4k3/8/8/8/8/8/8/4K3 w - - pi 3.14;")
#
#         # Create an EPD with a variation.
#         board = chess.Board("k7/8/8/8/8/8/4PPPP/4K1NR w K - 0 1")
#         epd = board.epd(pv=[
#             chess.Move.from_uci("g1f3"),  # Nf3
#             chess.Move.from_uci("a8a7"),  # Ka7
#             chess.Move.from_uci("e1h1"),  # O-O
#         ])
#         self.assertEqual(epd, "k7/8/8/8/8/8/4PPPP/4K1NR w K - pv Nf3 Ka7 O-O;")
#
#         # Create an EPD with a set of moves.
#         board = chess.Board("8/8/8/4k3/8/1K6/8/8 b - - 0 1")
#         epd = board.epd(bm=[
#             chess.Move.from_uci("e5e6"),  # Ke6
#             chess.Move.from_uci("e5e4"),  # Ke4
#         ])
#         self.assertEqual(epd, "8/8/8/4k3/8/1K6/8/8 b - - bm Ke4 Ke6;")
#
#         # Test loading an EPD.
#         board = chess.Board()
#         operations = board.set_epd("r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - bm f4; id \"BK.24\";")
#         self.assertEqual(board.fen(), "r2qnrnk/p2b2b1/1p1p2pp/2pPpp2/1PP1P3/PRNBB3/3QNPPP/5RK1 w - - 0 1")
#         self.assertIn(chess.Move(chess.F2, chess.F4), operations["bm"])
#         self.assertEqual(operations["id"], "BK.24")
#
#         # Test loading an EPD with half-move counter operations.
#         board = chess.Board()
#         operations = board.set_epd("4k3/8/8/8/8/8/8/4K3 b - - fmvn 17; hmvc 13")
#         self.assertEqual(board.fen(), "4k3/8/8/8/8/8/8/4K3 b - - 13 17")
#         self.assertEqual(operations["fmvn"], 17)
#         self.assertEqual(operations["hmvc"], 13)
#
#         # Test context of parsed SANs.
#         board = chess.Board()
#         operations = board.set_epd("4k3/8/8/2N5/8/8/8/4K3 w - - test Ne4")
#         self.assertEqual(operations["test"], chess.Move(chess.C5, chess.E4))
#
#         # Test parsing EPD with a set of moves.
#         board = chess.Board()
#         operations = board.set_epd("4k3/8/3QK3/8/8/8/8/8 w - - bm Qe7# Qb8#;")
#         self.assertEqual(board.fen(), "4k3/8/3QK3/8/8/8/8/8 w - - 0 1")
#         self.assertEqual(len(operations["bm"]), 2)
#         self.assertIn(chess.Move.from_uci("d6b8"), operations["bm"])
#         self.assertIn(chess.Move.from_uci("d6e7"), operations["bm"])
#
#         # Test parsing EPD with a stack of moves.
#         board = chess.Board()
#         operations = board.set_epd("6k1/1p6/6K1/8/8/8/8/7Q w - - pv Qh7+ Kf8 Qf7#;")
#         self.assertEqual(len(operations["pv"]), 3)
#         self.assertEqual(operations["pv"][0], chess.Move.from_uci("h1h7"))
#         self.assertEqual(operations["pv"][1], chess.Move.from_uci("g8f8"))
#         self.assertEqual(operations["pv"][2], chess.Move.from_uci("h7f7"))
#
#         # Test EPD with semicolon.
#         board = chess.Board()
#         operations = board.set_epd("r2qk2r/ppp1b1pp/2n1p3/3pP1n1/3P2b1/2PB1NN1/PP4PP/R1BQK2R w KQkq - bm Nxg5; c0 \"ERET.095; Queen sacrifice\";")
#         self.assertEqual(operations["bm"], [chess.Move.from_uci("f3g5")])
#         self.assertEqual(operations["c0"], "ERET.095; Queen sacrifice")
#
#         # Test EPD with string escaping.
#         board = chess.Board()
#         operations = board.set_epd(r"""4k3/8/8/8/8/8/8/4K3 w - - a "foo\"bar";; ; b "foo\\\\";""")
#         self.assertEqual(operations["a"], "foo\"bar")
#         self.assertEqual(operations["b"], "foo\\\\")
#
#         # Test EPD with unmatched trailing quotes.
#         board = chess.Board()
#         operations = board.set_epd("1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"")
#         self.assertEqual(operations["bm"], [chess.Move.from_uci("d6d1")])
#         self.assertEqual(operations["id"], "")
#         self.assertEqual(board.epd(**operations), "1k1r4/pp1b1R2/3q2pp/4p3/2B5/4Q3/PPP2B2/2K5 b - - bm Qd1+; id \"\";")
#
#     def test_eret_epd(self):
#         # Too many dashes.
#         epd = """r1bqk1r1/1p1p1n2/p1n2pN1/2p1b2Q/2P1Pp2/1PN5/PB4PP/R4RK1 w q - - bm Rxf4; id "ERET 001 - Entlastung";"""
#         board, ops = chess.Board.from_epd(epd)
#         self.assertEqual(ops["id"], "ERET 001 - Entlastung")
#         self.assertEqual(ops["bm"], [chess.Move.from_uci("f1f4")])
#
#     def test_null_moves(self):
#         self.assertEqual(str(chess.Move.null()), "0000")
#         self.assertEqual(chess.Move.null().uci(), "0000")
#         self.assertFalse(chess.Move.null())
#
#         fen = "rnbqkbnr/ppp1pppp/8/2Pp4/8/8/PP1PPPPP/RNBQKBNR w KQkq d6 0 2"
#         board = chess.Board(fen)
#
#         self.assertEqual(chess.Move.from_uci("0000"), board.push_san("--"))
#         self.assertEqual(board.fen(), "rnbqkbnr/ppp1pppp/8/2Pp4/8/8/PP1PPPPP/RNBQKBNR b KQkq - 1 2")
#
#         self.assertEqual(chess.Move.null(), board.pop())
#         self.assertEqual(board.fen(), fen)
#
#     def test_attackers(self):
#         board = chess.Board("r1b1k2r/pp1n1ppp/2p1p3/q5B1/1b1P4/P1n1PN2/1P1Q1PPP/2R1KB1R b Kkq - 3 10")
#
#         attackers = board.attackers(chess.WHITE, chess.C3)
#         self.assertEqual(len(attackers), 3)
#         self.assertIn(chess.C1, attackers)
#         self.assertIn(chess.D2, attackers)
#         self.assertIn(chess.B2, attackers)
#         self.assertNotIn(chess.D4, attackers)
#         self.assertNotIn(chess.E1, attackers)
#
#
#     def test_attacks(self):
#         board = chess.Board("5rk1/p5pp/2p3p1/1p1pR3/3P2P1/2N5/PP3n2/2KB4 w - - 1 26")
#
#         attacks = board.attacks(chess.E5)
#         self.assertEqual(len(attacks), 11)
#         self.assertIn(chess.D5, attacks)
#         self.assertIn(chess.E1, attacks)
#         self.assertIn(chess.F5, attacks)
#         self.assertNotIn(chess.E5, attacks)
#         self.assertNotIn(chess.C5, attacks)
#         self.assertNotIn(chess.F4, attacks)
#
#         pawn_attacks = board.attacks(chess.B2)
#         self.assertIn(chess.A3, pawn_attacks)
#         self.assertNotIn(chess.B3, pawn_attacks)
#
#         self.assertFalse(board.attacks(chess.G1))
#
#     def test_clear(self):
#         board = chess.Board()
#         board.clear()
#
#         self.assertEqual(board.turn, chess.WHITE)
#         self.assertEqual(board.fullmove_number, 1)
#         self.assertEqual(board.halfmove_clock, 0)
#         self.assertEqual(board.castling_rights, chess.BB_EMPTY)
#         self.assertFalse(board.ep_square)
#
#         self.assertFalse(board.piece_at(chess.E1))
#         self.assertEqual(chess.popcount(board.occupied), 0)
#
#     def test_threefold_repetition(self):
#         board = chess.Board()
#
#         # Go back and forth with the knights to reach the starting position
#         # for a second time.
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#         board.push_san("Nf3")
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#         board.push_san("Nf6")
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#         board.push_san("Ng1")
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#         board.push_san("Ng8")
#
#         # Once more.
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#         board.push_san("Nf3")
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#         board.push_san("Nf6")
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#         board.push_san("Ng1")
#
#         # Now black can go back to the starting position (thus reaching it a
#         # third time).
#         self.assertTrue(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#         board.push_san("Ng8")
#
#         # They indeed do it. Also, white can now claim.
#         self.assertTrue(board.can_claim_threefold_repetition())
#         self.assertTrue(board.is_repetition())
#
#         # But not after a different move.
#         board.push_san("e4")
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_repetition())
#
#         # Undo moves and check if everything works backwards.
#         board.pop()  # e4
#         self.assertTrue(board.can_claim_threefold_repetition())
#         board.pop()  # Ng8
#         self.assertTrue(board.can_claim_threefold_repetition())
#         while board.move_stack:
#             board.pop()
#             self.assertFalse(board.can_claim_threefold_repetition())
#
#     def test_fivefold_repetition(self):
#         fen = "rnbq1rk1/ppp3pp/3bpn2/3p1p2/2PP4/2NBPN2/PP3PPP/R1BQK2R w KQ - 3 7"
#         board = chess.Board(fen)
#
#         # Repeat the position up to the fourth time.
#         for i in range(3):
#             board.push_san("Be2")
#             self.assertFalse(board.is_fivefold_repetition())
#             board.push_san("Ne4")
#             self.assertFalse(board.is_fivefold_repetition())
#             board.push_san("Bd3")
#             self.assertFalse(board.is_fivefold_repetition())
#             board.push_san("Nf6")
#             self.assertEqual(board.fen().split()[0], fen.split()[0])
#             self.assertFalse(board.is_fivefold_repetition())
#             self.assertFalse(board.is_game_over())
#
#         # Repeat it once more. Now it is a fivefold repetition.
#         board.push_san("Be2")
#         self.assertFalse(board.is_fivefold_repetition())
#         board.push_san("Ne4")
#         self.assertFalse(board.is_fivefold_repetition())
#         board.push_san("Bd3")
#         self.assertFalse(board.is_fivefold_repetition())
#         board.push_san("Nf6")
#         self.assertEqual(board.fen().split()[0], fen.split()[0])
#         self.assertTrue(board.is_fivefold_repetition())
#         self.assertTrue(board.is_game_over())
#
#         # It is also a threefold repetition.
#         self.assertTrue(board.can_claim_threefold_repetition())
#
#         # Now no longer.
#         board.push_san("Qc2")
#         board.push_san("Qd7")
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_fivefold_repetition())
#         board.push_san("Qd2")
#         board.push_san("Qe7")
#         self.assertFalse(board.can_claim_threefold_repetition())
#         self.assertFalse(board.is_fivefold_repetition())
#
#         # Give the possibility to repeat.
#         board.push_san("Qd1")
#         self.assertFalse(board.is_fivefold_repetition())
#         self.assertFalse(board.is_game_over())
#         self.assertTrue(board.can_claim_threefold_repetition())
#         self.assertTrue(board.is_game_over(claim_draw=True))
#
#         # Do, in fact, repeat.
#         self.assertFalse(board.is_fivefold_repetition())
#         board.push_san("Qd8")
#
#         # This is a threefold repetition, and also a fivefold repetition since
#         # it no longer has to occur on consecutive moves.
#         self.assertTrue(board.can_claim_threefold_repetition())
#         self.assertTrue(board.is_fivefold_repetition())
#         self.assertEqual(board.fen().split()[0], fen.split()[0])
#
#     def test_trivial_is_repetition(self):
#         self.assertTrue(chess.Board().is_repetition(1))

#
#     def test_pseudo_legality(self):
#         sample_moves = [
#             chess.Move(chess.A2, chess.A4),
#             chess.Move(chess.C1, chess.E3),
#             chess.Move(chess.G8, chess.F6),
#             chess.Move(chess.D7, chess.D8, chess.QUEEN),
#             chess.Move(chess.E5, chess.E4),
#         ]
#
#         sample_fens = [
#             chess.STARTING_FEN,
#             "rnbqkbnr/pp1ppppp/2p5/8/6P1/2P5/PP1PPP1P/RNBQKBNR b KQkq - 0 1",
#             "rnb1kbnr/ppq1pppp/2pp4/8/6P1/2P5/PP1PPPBP/RNBQK1NR w KQkq - 0 1",
#             "rn2kbnr/p1q1ppp1/1ppp3p/8/4B1b1/2P4P/PPQPPP2/RNB1K1NR w KQkq - 0 1",
#             "rnkq1bnr/p3ppp1/1ppp3p/3B4/6b1/2PQ3P/PP1PPP2/RNB1K1NR w KQ - 0 1",
#             "rn1q1bnr/3kppp1/2pp3p/pp6/1P2b3/2PQ1N1P/P2PPPB1/RNB1K2R w KQ - 0 1",
#             "rnkq1bnr/4pp2/2pQ2pp/pp6/1P5N/2P4P/P2PPP2/RNB1KB1b w Q - 0 1",
#             "rn3b1r/1kq1p3/2pQ1npp/Pp6/4b3/2PPP2P/P4P2/RNB1KB2 w Q - 0 1",
#             "r4br1/8/k1p2npp/Ppn1p3/P7/2PPP1qP/4bPQ1/RNB1KB2 w Q - 0 1",
#             "rnbqk1nr/p2p3p/1p5b/2pPppp1/8/P7/1PPQPPPP/RNB1KBNR w KQkq c6 0 1",
#             "rnb1k2r/pp1p1p1p/1q1P4/2pnpPp1/6P1/2N5/PP1BP2P/R2QKBNR w KQkq e6 0 1",
#             "1n4kr/2B4p/2nb2b1/ppp5/P1PpP3/3P4/5K2/1N1R4 b - c3 0 1",
#             "r2n3r/1bNk2pp/6P1/pP3p2/3pPqnP/1P1P1p1R/2P3B1/Q1B1bKN1 b - e3 0 1",
#         ]
#
#         for sample_fen in sample_fens:
#             board = chess.Board(sample_fen)
#
#             pseudo_legal_moves = list(board.generate_pseudo_legal_moves())
#
#             # Ensure that all moves generated as pseudo-legal pass the
#             # pseudo-legality check.
#             for move in pseudo_legal_moves:
#                 self.assertTrue(board.is_pseudo_legal(move))
#
#             # Check that moves not generated as pseudo-legal do not pass the
#             # pseudo-legality check.
#             for move in sample_moves:
#                 if move not in pseudo_legal_moves:
#                     self.assertFalse(board.is_pseudo_legal(move))
#
#
    def test_pieces(self):
        board = chess.Board()
        king = board.pieces(chess.KING, chess.WHITE)
        self.assertIn(chess.E0, king)
        self.assertEqual(len(king), 1)
#
#     def test_string_conversion(self):
#         board = chess.Board("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1")
# #
#         self.assertEqual(str(board), textwrap.dedent("""\
#             . . . . . . . k
#             . p . q n . b .
#             p B . p . n . .
#             . . . P p . . .
#             . . . . P p . p
#             . . Q N . B . .
#             P P . . . . P P
#             . . . . . . K ."""))
#
#         self.assertEqual(board.unicode(empty_square="·"), textwrap.dedent("""\
#             · · · · · · · ♚
#             · ♟ · ♛ ♞ · ♝ ·
#             ♟ ♗ · ♟ · ♞ · ·
#             · · · ♙ ♟ · · ·
#             · · · · ♙ ♟ · ♟
#             · · ♕ ♘ · ♗ · ·
#             ♙ ♙ · · · · ♙ ♙
#             · · · · · · ♔ ·"""))
#
#         self.assertEqual(board.unicode(invert_color=True, borders=True, empty_square="·"), textwrap.dedent("""\
#               -----------------
#             8 |·|·|·|·|·|·|·|♔|
#               -----------------
#             7 |·|♙|·|♕|♘|·|♗|·|
#               -----------------
#             6 |♙|♝|·|♙|·|♘|·|·|
#               -----------------
#             5 |·|·|·|♟|♙|·|·|·|
#               -----------------
#             4 |·|·|·|·|♟|♙|·|♙|
#               -----------------
#             3 |·|·|♛|♞|·|♝|·|·|
#               -----------------
#             2 |♟|♟|·|·|·|·|♟|♟|
#               -----------------
#             1 |·|·|·|·|·|·|♚|·|
#               -----------------
#                a b c d e f g h"""))
#
    def test_move_info(self):
        board = chess.Board("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1")

        self.assertTrue(board.is_capture(board.parse_xboard("Cb2xb9")))
        self.assertTrue(board.is_capture(board.parse_xboard("Ch2xh9")))
#         self.assertFalse(board.is_en_passant(board.parse_xboard("Qxf7+")))
#         self.assertFalse(board.is_castling(board.parse_xboard("Qxf7+")))
#
#         self.assertTrue(board.is_capture(board.parse_xboard("hxg6")))
#         self.assertTrue(board.is_en_passant(board.parse_xboard("hxg6")))
#         self.assertFalse(board.is_castling(board.parse_xboard("hxg6")))
#
#         self.assertFalse(board.is_capture(board.parse_xboard("b3")))
#         self.assertFalse(board.is_en_passant(board.parse_xboard("b3")))
#         self.assertFalse(board.is_castling(board.parse_xboard("b3")))
#
#         self.assertFalse(board.is_capture(board.parse_xboard("Ra6")))
#         self.assertFalse(board.is_en_passant(board.parse_xboard("Ra6")))
#         self.assertFalse(board.is_castling(board.parse_xboard("Ra6")))
#
#         self.assertFalse(board.is_capture(board.parse_xboard("O-O")))
#         self.assertFalse(board.is_en_passant(board.parse_xboard("O-O")))
#         self.assertTrue(board.is_castling(board.parse_xboard("O-O")))
#
    # def test_pin(self):
    #     board = chess.Board(self.assertTrue(board.is_capture(board.parse_xboard("Cb2xb9"))))
    #     self.assertTrue(board.is_pinned(chess.WHITE, chess.F2))
#         self.assertTrue(board.is_pinned(chess.WHITE, chess.D2))
#         self.assertFalse(board.is_pinned(chess.WHITE, chess.E1))
#         self.assertFalse(board.is_pinned(chess.BLACK, chess.H4))
#         self.assertFalse(board.is_pinned(chess.BLACK, chess.E8))
#
#         self.assertEqual(board.pin(chess.WHITE, chess.B1), chess.BB_ALL)
#
#         self.assertEqual(board.pin(chess.WHITE, chess.F2), chess.BB_E1 | chess.BB_F2 | chess.BB_G3 | chess.BB_H4)
#
#         self.assertEqual(board.pin(chess.WHITE, chess.D2), chess.BB_E1 | chess.BB_D2 | chess.BB_C3 | chess.BB_B4 | chess.BB_A5)
#
#         self.assertEqual(chess.Board(None).pin(chess.WHITE, chess.F7), chess.BB_ALL)
#
#     def test_pin_in_check(self):
#         # The knight on the eighth rank is on the outer side of the rank attack.
#         board = chess.Board("1n1R2k1/2b1qpp1/p3p2p/1p6/1P2Q2P/4PNP1/P4PB1/6K1 b - - 0 1")
#         self.assertFalse(board.is_pinned(chess.BLACK, chess.B8))
#
#         # The empty square e8 would be considered pinned.
#         self.assertTrue(board.is_pinned(chess.BLACK, chess.E8))
#
#
    def test_capture_generation(self):
        board = chess.Board("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1")
#
        # Fully legal captures.
        lc = list(board.generate_legal_captures())
        self.assertIn(board.parse_san("Cb2xb9"), lc)
        self.assertIn(board.parse_san("Ch2xh9"), lc)
#         self.assertIn(board.parse_san("exf6"), lc)  # En passant
#         self.assertIn(board.parse_san("Bxd3"), lc)
#         self.assertEqual(len(lc), 3)
#
#         plc = list(board.generate_pseudo_legal_captures())
#         self.assertIn(board.parse_san("Qxd1"), plc)
#         self.assertIn(board.parse_san("exf6"), plc)  # En passant
#         self.assertIn(board.parse_san("Bxd3"), plc)
#         self.assertIn(chess.Move.from_uci("c2c7"), plc)
#         self.assertIn(chess.Move.from_uci("c2d3"), plc)
#         self.assertEqual(len(plc), 5)
#
#

#
    # def test_mirror(self):
    #     board = chess.Board("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1")
    #     mirrored = chess.Board("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w 1")
        # print(board.mirror())
        # self.assertEqual(board.mirror(), mirrored)
        # board.apply_mirror()
        # self.assertEqual(board, mirrored)
#

#     def test_is_irreversible(self):
#         board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1")
#         self.assertTrue(board.is_irreversible(board.parse_san("Ra2")))
#         self.assertTrue(board.is_irreversible(board.parse_san("O-O-O")))
#         self.assertTrue(board.is_irreversible(board.parse_san("Kd1")))
#         self.assertTrue(board.is_irreversible(board.parse_san("Rxa8")))
#         self.assertTrue(board.is_irreversible(board.parse_san("Rxh8")))
#         self.assertFalse(board.is_irreversible(board.parse_san("Rf1")))
#         self.assertFalse(board.is_irreversible(chess.Move.null()))
#
#         board.set_castling_fen("kq")
#         self.assertFalse(board.is_irreversible(board.parse_san("Ra2")))
#         self.assertFalse(board.is_irreversible(board.parse_san("Kd1")))
#         self.assertTrue(board.is_irreversible(board.parse_san("Rxa8")))
#         self.assertTrue(board.is_irreversible(board.parse_san("Rxh8")))
#         self.assertFalse(board.is_irreversible(board.parse_san("Rf1")))
#         self.assertFalse(board.is_irreversible(chess.Move.null()))
#
#
# class LegalMoveGeneratorTestCase(unittest.TestCase):
#
#     def test_list_conversion(self):
#         self.assertEqual(len(list(chess.Board().legal_moves)), 20)
#
#     def test_nonzero(self):
#         self.assertTrue(chess.Board().legal_moves)
#         self.assertTrue(chess.Board().pseudo_legal_moves)
#
#         caro_kann_mate = chess.Board("r1bqkb1r/pp1npppp/2pN1n2/8/3P4/8/PPP1QPPP/R1B1KBNR b KQkq - 4 6")
#         self.assertFalse(caro_kann_mate.legal_moves)
#         self.assertTrue(chess.Board().pseudo_legal_moves)
#
#     def test_string_conversion(self):
#         board = chess.Board("r3k1nr/ppq1pp1p/2p3p1/8/1PPR4/2N5/P3QPPP/5RK1 b kq b3 0 16")
#
#         self.assertIn("Qxh2+", str(board.legal_moves))
#         self.assertIn("Qxh2+", repr(board.legal_moves))
#
#         self.assertIn("Qxh2+", str(board.pseudo_legal_moves))
#         self.assertIn("Qxh2+", repr(board.pseudo_legal_moves))
#         self.assertIn("e8d7", str(board.pseudo_legal_moves))
#         self.assertIn("e8d7", repr(board.pseudo_legal_moves))
#
#     def test_traverse_once(self):
#         class MockBoard:
#             def __init__(self):
#                 self.traversals = 0
#
#             def generate_legal_moves(self):
#                 self.traversals += 1
#                 return
#                 yield
#
#         board = MockBoard()
#         gen = chess.LegalMoveGenerator(board)
#         list(gen)
#         self.assertEqual(board.traversals, 1)
#
#
class BaseBoardTestCase(unittest.TestCase):

    def test_set_piece_map(self):
        a = chess.BaseBoard.empty()
        b = chess.BaseBoard()
        a.set_piece_map(b.piece_map())
        self.assertEqual(a, b)
        a.set_piece_map({})
        self.assertNotEqual(a, b)
#
#
class SquareSetTestCase(unittest.TestCase):

    def test_equality(self):
        a1 = chess.SquareSet(chess.BB_RANK_4)
        a2 = chess.SquareSet(chess.BB_RANK_4)
        b1 = chess.SquareSet(chess.bitwise_or(chess.BB_RANK_5, chess.BB_RANK_6))
        b2 = chess.SquareSet(chess.bitwise_or(chess.BB_RANK_5, chess.BB_RANK_6))

        self.assertEqual(a1, a2)
        self.assertEqual(b1, b2)
        self.assertFalse(a1 != a2)
        self.assertFalse(b1 != b2)

        self.assertNotEqual(a1, b1)
        self.assertNotEqual(a2, b2)
        self.assertFalse(a1 == b1)
        self.assertFalse(a2 == b2)

        self.assertEqual(chess.SquareSet(chess.BB_ALL), chess.BB_ALL)
        self.assertEqual(chess.BB_ALL, chess.SquareSet(chess.BB_ALL))

        # self.assertEqual(int(chess.SquareSet(chess.SquareSet(999))), 999)
        # self.assertEqual(chess.SquareSet(chess.B8), chess.BB_B8)
#
#     def test_string_conversion(self):
#         expected = textwrap.dedent("""\
#             . . . . . . . 1
#             . 1 . . . . . .
#             . . . . . . . .
#             . . . . . . . .
#             . . . . . . . .
#             . . . . . . . .
#             . . . . . . . .
#             1 1 1 1 1 1 1 1""")
#
#         bb = chess.SquareSet(chess.BB_H8 | chess.BB_B7 | chess.BB_RANK_1)
#         self.assertEqual(str(bb), expected)
#
#     def test_iter(self):
#         bb = chess.SquareSet(chess.BB_G7 | chess.BB_G8)
#         self.assertEqual(list(bb), [chess.G7, chess.G8])
#
#     def test_reversed(self):
#         bb = chess.SquareSet(chess.BB_A1 | chess.BB_B1 | chess.BB_A7 | chess.BB_E1)
#         self.assertEqual(list(reversed(bb)), [chess.A7, chess.E1, chess.B1, chess.A1])
#
#     def test_arithmetic(self):
#         self.assertEqual(chess.SquareSet(chess.BB_RANK_2) & chess.BB_FILE_D, chess.BB_D2)
#         self.assertEqual(chess.SquareSet(chess.BB_ALL) ^ chess.BB_EMPTY, chess.BB_ALL)
#         self.assertEqual(chess.SquareSet(chess.BB_C1) | chess.BB_FILE_C, chess.BB_FILE_C)
#
#         bb = chess.SquareSet(chess.BB_EMPTY)
#         bb ^= chess.BB_ALL
#         self.assertEqual(bb, chess.BB_ALL)
#         bb &= chess.BB_E4
#         self.assertEqual(bb, chess.BB_E4)
#         bb |= chess.BB_RANK_4
#         self.assertEqual(bb, chess.BB_RANK_4)
#
#         self.assertEqual(chess.SquareSet(chess.BB_F3) << 1, chess.BB_G3)
#         self.assertEqual(chess.SquareSet(chess.BB_C8) >> 2, chess.BB_A8)
#
#         bb = chess.SquareSet(chess.BB_D1)
#         bb <<= 1
#         self.assertEqual(bb, chess.BB_E1)
#         bb >>= 2
#         self.assertEqual(bb, chess.BB_C1)
#
#     def test_immutable_set_operations(self):
#         self.assertTrue(chess.SquareSet(chess.BB_RANK_1).isdisjoint(chess.BB_RANK_2))
#         self.assertFalse(chess.SquareSet(chess.BB_RANK_2).isdisjoint(chess.BB_FILE_E))
#
#         self.assertFalse(chess.SquareSet(chess.BB_A1).issubset(chess.BB_RANK_1))
#         self.assertTrue(chess.SquareSet(chess.BB_RANK_1).issubset(chess.BB_A1))
#
#         self.assertTrue(chess.SquareSet(chess.BB_A1).issuperset(chess.BB_RANK_1))
#         self.assertFalse(chess.SquareSet(chess.BB_RANK_1).issuperset(chess.BB_A1))
#
#         self.assertEqual(chess.SquareSet(chess.BB_A1).union(chess.BB_FILE_A), chess.BB_FILE_A)
#
#         self.assertEqual(chess.SquareSet(chess.BB_A1).intersection(chess.BB_A2), chess.BB_EMPTY)
#
#         self.assertEqual(chess.SquareSet(chess.BB_A1).difference(chess.BB_A2), chess.BB_A1)
#
#         self.assertEqual(chess.SquareSet(chess.BB_A1).symmetric_difference(chess.BB_A2), chess.BB_A1 | chess.BB_A2)
#
#         self.assertEqual(chess.SquareSet(chess.BB_C5).copy(), chess.BB_C5)
#
#     def test_mutable_set_operations(self):
#         squares = chess.SquareSet(chess.BB_A1)
#         squares.update(chess.BB_FILE_H)
#         self.assertEqual(squares, chess.BB_A1 | chess.BB_FILE_H)
#
#         squares.intersection_update(chess.BB_RANK_8)
#         self.assertEqual(squares, chess.BB_H8)
#
#         squares.difference_update(chess.BB_A1)
#         self.assertEqual(squares, chess.BB_H8)
#
#         squares.symmetric_difference_update(chess.BB_A1)
#         self.assertEqual(squares, chess.BB_A1 | chess.BB_H8)
#
#         squares.add(chess.A3)
#         self.assertEqual(squares, chess.BB_A1 | chess.BB_A3 | chess.BB_H8)
#
#         squares.remove(chess.H8)
#         self.assertEqual(squares, chess.BB_A1 | chess.BB_A3)
#
#         with self.assertRaises(KeyError):
#             squares.remove(chess.H8)
#
#         squares.discard(chess.H8)
#
#         squares.discard(chess.A1)
#         self.assertEqual(squares, chess.BB_A3)
#
#         squares.clear()
#         self.assertEqual(squares, chess.BB_EMPTY)
#
#         with self.assertRaises(KeyError):
#             squares.pop()
#
#         squares.add(chess.C7)
#         self.assertEqual(squares.pop(), chess.C7)
#         self.assertEqual(squares, chess.BB_EMPTY)
#
#     def test_from_square(self):
#         self.assertEqual(chess.SquareSet.from_square(chess.H5), chess.BB_H5)
#         self.assertEqual(chess.SquareSet.from_square(chess.C2), chess.BB_C2)
#
#     def test_carry_rippler(self):
#         self.assertEqual(sum(1 for _ in chess.SquareSet(chess.BB_D1).carry_rippler()), 2 ** 1)
#         self.assertEqual(sum(1 for _ in chess.SquareSet(chess.BB_FILE_B).carry_rippler()), 2 ** 8)
#
#     def test_mirror(self):
#         self.assertEqual(chess.SquareSet(0x00a2_0900_0004_a600).mirror(), 0x00a6_0400_0009_a200)
#         self.assertEqual(chess.SquareSet(0x1e22_2212_0e0a_1222).mirror(), 0x2212_0a0e_1222_221e)
#
#     def test_flip(self):
#         self.assertEqual(chess.flip_vertical(chess.BB_ALL), chess.BB_ALL)
#         self.assertEqual(chess.flip_horizontal(chess.BB_ALL), chess.BB_ALL)
#         self.assertEqual(chess.flip_diagonal(chess.BB_ALL), chess.BB_ALL)
#         self.assertEqual(chess.flip_anti_diagonal(chess.BB_ALL), chess.BB_ALL)
#
#         s = chess.SquareSet(0x1e22_2212_0e0a_1222)  # Letter R
#         self.assertEqual(chess.flip_vertical(s), 0x2212_0a0e_1222_221e)
#         self.assertEqual(chess.flip_horizontal(s), 0x7844_4448_7050_4844)
#         self.assertEqual(chess.flip_diagonal(s), 0x0000_6192_8c88_ff00)
#         self.assertEqual(chess.flip_anti_diagonal(s), 0x00ff_1131_4986_0000)
#
#     def test_len_of_complenent(self):
#         squares = chess.SquareSet(~chess.BB_ALL)
#         self.assertEqual(len(squares), 0)
#
#         squares = ~chess.SquareSet(chess.BB_BACKRANKS)
#         self.assertEqual(len(squares), 48)
#
#     def test_int_conversion(self):
#         self.assertEqual(int(chess.SquareSet(chess.BB_CENTER)), 0x0000_0018_1800_0000)
#         self.assertEqual(hex(chess.SquareSet(chess.BB_CENTER)), "0x1818000000")
#         self.assertEqual(bin(chess.SquareSet(chess.BB_CENTER)), "0b1100000011000000000000000000000000000")
#
#     def test_tolist(self):
#         self.assertEqual(chess.SquareSet(chess.BB_LIGHT_SQUARES).tolist().count(True), 32)




if __name__ == "__main__":
    verbosity = sum(arg.count("v") for arg in sys.argv if all(c == "v" for c in arg.lstrip("-")))
    verbosity += sys.argv.count("--verbose")

    if verbosity >= 2:
        logging.basicConfig(level=logging.DEBUG)

    raise_log_handler = RaiseLogHandler()
    raise_log_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(raise_log_handler)

    unittest.main()
