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

def main():
    with open(FIGHTS_CSV, newline="", encoding="utf-8") as f:
        fights = list(csv.DictReader(f))
    fights.sort(key=lambda r: r["date"])

    ratings = {}
    processed = 0

    for fight in fights:
        a, b, winner = fight["fighter_a"], fight["fighter_b"], fight["winner"]
        if winner == "nc":
            continue
        score_a = 0.5 if winner == "draw" else (1.0 if winner == a else 0.0)

        ra, rda = ratings.setdefault(a, [BASE_RATING, DEFAULT_RD])
        rb, rdb = ratings.setdefault(b, [BASE_RATING, DEFAULT_RD])

        ratings[a] = list(update_rating(ra, rda, rb, rdb, score_a))
        ratings[b] = list(update_rating(rb, rdb, ra, rda, 1 - score_a))
        processed += 1

    rows = sorted(ratings.items(), key=lambda kv: kv[1][0], reverse=True)
    with open(RATINGS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["fighter", "elo"])
        for name, (rating, _rd) in rows:
            writer.writerow([name, round(rating, 1)])

    print(f"Processed {processed} fights, rated {len(ratings)} fighters -> {RATINGS_CSV}")

if __name__ == "__main__":
    main()
