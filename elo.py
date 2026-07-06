import math

BASE_RATING = 1000.0
DEFAULT_RD = 350.0
Q = math.log(10) / 400

def g(rd):
    g = 1 / math.sqrt(1 + 3 * Q ** 2 * rd ** 2 / math.pi ** 2)
    return g

def calculate_win_prob(ri, rj, rd_j=DEFAULT_RD):
    e = 1 / (1 + 10 ** (-g(rd_j) * (ri - rj) / 400))
    return e

def update_rating(rating, rd, opponent_rating, opponent_rd, score):
    g_opp = g(opponent_rd)
    e = calculate_win_prob(rating, opponent_rating, opponent_rd)

    d2 = 1 / (Q ** 2 * g_opp ** 2 * e * (1 - e))
    new_rd = math.sqrt(1 / (1 / rd ** 2 + 1 / d2))
    new_rating = rating + Q * new_rd ** 2 * g_opp * (score - e)
    return new_rating, new_rd
