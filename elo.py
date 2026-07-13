import math, csv, os

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

FIGHTS_CSV = os.path.join(os.path.dirname(__file__), "data", "fights.csv")
RATINGS_CSV = os.path.join(os.path.dirname(__file__), "data", "ratings.csv")

def compute_ratings():
    with open(FIGHTS_CSV, "r", newline="", encoding="utf-8") as f:
        fights = list(csv.DictReader(f))
    fights.sort(key=lambda r: r["date"])

    ratings = {}

    for fight in fights:
        a, b, winner = fight["fighter_a"], fight["fighter_b"], fight["winner"]
        if winner == "nc":
            continue
        elif winner == "draw":
            score_a = 0.5
        elif winner == a:
            score_a = 1.0
        else:
            score_a = 0.0

        ra, rda, peak_ra = ratings.setdefault(a, [BASE_RATING, DEFAULT_RD, BASE_RATING])
        rb, rdb, peak_rb = ratings.setdefault(b, [BASE_RATING, DEFAULT_RD, BASE_RATING])

        new_ra, new_rda = update_rating(ra, rda, rb, rdb, score_a)
        new_rb, new_rdb = update_rating(rb, rdb, ra, rda, 1 - score_a)
        ratings[a] = [new_ra, new_rda, max(peak_ra, new_ra)]
        ratings[b] = [new_rb, new_rdb, max(peak_rb, new_rb)]

    return ratings

def main():
    ratings = compute_ratings()
    rows = sorted(ratings.items(), key=lambda kv: kv[1][2], reverse=True)
    with open(RATINGS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["fighter", "peak_elo"])
        for name, (_rating, _rd, peak) in rows:
            writer.writerow([name, round(peak, 1)])

    print(f"Rated {len(ratings)} fighters")

if __name__ == "__main__":
    main()
