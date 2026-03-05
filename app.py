from flask import Flask, render_template, jsonify, request
import random

app = Flask(__name__)

# --- Symbols ---
NORMALS = ["🍒", "🍋", "🔔", "⭐", "💎"]
WILD = "🃏"
SCATTER = "🌟"   # free spins
BONUS = "🎁"     # bonus game trigger

# Weighted RNG (common -> rare)
weights = {
    "🍒": 42,
    "🍋": 32,
    "🔔": 16,
    "⭐": 12,
    "💎": 3,
    "🃏": 3,
    "🌟": 2,
    "🎁": 2,
}

weighted_bag = []
for s, w in weights.items():
    weighted_bag += [s] * w

# 25 paylines (row index per column)
PAYLINES_25 = [
    [0,0,0,0,0],
    [1,1,1,1,1],
    [2,2,2,2,2],
    [0,1,2,1,0],
    [2,1,0,1,2],
    [0,0,1,0,0],
    [2,2,1,2,2],
    [1,0,0,0,1],
    [1,2,2,2,1],
    [0,1,1,1,0],
    [2,1,1,1,2],
    [0,1,0,1,0],
    [2,1,2,1,2],
    [1,0,1,0,1],
    [1,2,1,2,1],
    [0,2,0,2,0],
    [2,0,2,0,2],
    [0,2,1,2,0],
    [2,0,1,0,2],
    [1,1,0,1,1],
    [1,1,2,1,1],
    [0,1,2,2,2],
    [2,1,0,0,0],
    [0,0,0,1,2],
    [2,2,2,1,0],
]

# Line payouts (per line), multiplied by bet_per_line
PAYS = {
    "🍒": {3: 5, 4: 15, 5: 40},
    "🍋": {3: 6, 4: 18, 5: 45},
    "🔔": {3: 10, 4: 30, 5: 80},
    "⭐": {3: 12, 4: 40, 5: 120},
    "💎": {3: 25, 4: 90, 5: 250},
}

SCATTER_PAYS = {3: 10, 4: 40, 5: 120}  # multiplied by bet_per_line

# --- State (dev/local) ---
coins = 1000
free_spins = 0

stats = {"spins": 0, "wins": 0, "biggest": 0}

jackpot = 1000
JACKPOT_BASE = 1000


def rng_symbol() -> str:
    return random.choice(weighted_bag)


def build_grid():
    return [[rng_symbol() for _ in range(5)] for _ in range(3)]


def count_specials(grid):
    flat = [grid[r][c] for r in range(3) for c in range(5)]
    return flat.count(SCATTER), flat.count(BONUS)


def evaluate_line(line_symbols):
    """
    Left-to-right match with wilds.
    Wild substitutes for NORMALS only (not scatter/bonus).
    Returns (base_symbol, count) or (None,0)
    """
    base = None
    count = 0
    for s in line_symbols:
        if s in (SCATTER, BONUS):
            break
        if base is None:
            if s == WILD:
                count += 1
                continue
            base = s
            count += 1
        else:
            if s == base or s == WILD:
                count += 1
            else:
                break

    if base is None and count > 0:
        base = "🍒"

    if base in PAYS and count >= 3:
        return base, count
    return None, 0


def paylines_wins(grid, bet_per_line):
    total = 0
    wins = []
    for i, line in enumerate(PAYLINES_25):
        syms = [grid[line[col]][col] for col in range(5)]
        base, cnt = evaluate_line(syms)
        if base and cnt >= 3:
            amount = PAYS[base][cnt] * bet_per_line
            total += amount
            cells = [[line[col], col] for col in range(cnt)]
            wins.append({"lineIndex": i, "cells": cells, "amount": amount, "symbol": base, "count": cnt})
    return total, wins


def scatter_reward(sc_count, bet_per_line):
    if sc_count >= 3:
        return SCATTER_PAYS.get(sc_count, SCATTER_PAYS[5]) * bet_per_line
    return 0


def bonus_game_reward(bet_per_line):
    roll = random.random()
    if roll < 0.60:
        return 0
    if roll < 0.85:
        return 20 * bet_per_line
    if roll < 0.95:
        return 60 * bet_per_line
    if roll < 0.99:
        return 150 * bet_per_line
    return 400 * bet_per_line


@app.route("/")
def index():
    return render_template("index.html", coins=coins, free_spins=free_spins, jackpot=jackpot, stats=stats)


@app.route("/spin")
def spin():
    global coins, free_spins, jackpot, stats

    bet_per_line = int(request.args.get("bet", "1"))
    bet_per_line = bet_per_line if bet_per_line in (1, 5, 10) else 1

    lines = 25
    cost = bet_per_line * lines

    is_free = False
    if free_spins > 0:
        free_spins -= 1
        cost = 0
        is_free = True

    if coins < cost:
        return jsonify({
            "error": True,
            "coins": coins,
            "free_spins": free_spins,
            "jackpot": jackpot,
            "stats": stats
        })

    stats["spins"] += 1

    coins -= cost
    if cost > 0:
        jackpot += max(1, int(cost * 0.05))  # 5% in jackpot

    grid = build_grid()

    line_win, winning_lines = paylines_wins(grid, bet_per_line)

    sc_count, bonus_count = count_specials(grid)
    sc_win = scatter_reward(sc_count, bet_per_line)

    if sc_count >= 3:
        if sc_count == 3:
            free_spins += 10
        elif sc_count == 4:
            free_spins += 15
        else:
            free_spins += 25

    bonus_trigger = bonus_count >= 3
    bonus_win = bonus_game_reward(bet_per_line) if bonus_trigger else 0

    # Jackpot trigger: any winning line that is 5 diamonds (very rare), gated
    jackpot_won = False
    jackpot_amount = 0
    for w in winning_lines:
        if w["symbol"] == "💎" and w["count"] == 5:
            if random.random() < 0.15:
                jackpot_won = True
                jackpot_amount = jackpot
                jackpot = JACKPOT_BASE
            break

    total_reward = line_win + sc_win + bonus_win + jackpot_amount
    coins += total_reward

    if total_reward > 0:
        stats["wins"] += 1
    if total_reward > stats["biggest"]:
        stats["biggest"] = total_reward

    return jsonify({
        "grid": grid,
        "bet_per_line": bet_per_line,
        "lines": lines,
        "cost": cost,
        "is_free": is_free,

        "win": total_reward > 0,
        "reward": total_reward,

        "line_win": line_win,
        "scatter_count": sc_count,
        "scatter_win": sc_win,

        "bonus_trigger": bonus_trigger,
        "bonus_win": bonus_win,

        "jackpot": jackpot,
        "jackpot_won": jackpot_won,
        "jackpot_amount": jackpot_amount,

        "winning_lines": winning_lines,

        "coins": coins,
        "free_spins": free_spins,
        "stats": stats
    })


if __name__ == "__main__":
    # no debug => no PIN
    app.run(host="0.0.0.0", port=5000)
