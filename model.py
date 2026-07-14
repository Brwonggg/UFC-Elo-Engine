import csv, os, pickle, random
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss
from elo import update_rating, BASE_RATING, DEFAULT_RD

FIGHTS_CSV = os.path.join(os.path.dirname(__file__), "data", "fights.csv")
MODEL_PKL = os.path.join(os.path.dirname(__file__), "data", "model.pkl")
STATS = ["str", "td", "kd", "sub"]

def new_fighter():
    """Starting pre-fight state: Glicko rating/RD + empty stat accumulators."""
    return {"elo": BASE_RATING, "rd": DEFAULT_RD,
            "n": 0, "str": 0, "td": 0, "kd": 0, "sub": 0}

def features(sa, sb):
    """Diff vector (fighter_a - fighter_b) from two pre-fight states."""
    avg = lambda s, k: s[k] / s["n"] if s["n"] else 0.0
    return [sa["elo"] - sb["elo"], sa["rd"] - sb["rd"]] + [avg(sa, k) - avg(sb, k) for k in STATS]

def build_dataset():
    """Replay every fight in date order, capturing each bout's PRE-fight diffs.

    Returns (X, y, state) where state is each fighter's final state for prediction.
    """
    with open(FIGHTS_CSV, newline="", encoding="utf-8") as f:
        fights = sorted(csv.DictReader(f), key=lambda r: r["date"])

    state, X, y = {}, [], []
    for fight in fights:
        a, b, winner = fight["fighter_a"], fight["fighter_b"], fight["winner"]
        if winner == "nc":
            continue
        sa = state.setdefault(a, new_fighter())
        sb = state.setdefault(b, new_fighter())

        if winner != "draw":
            X.append(features(sa, sb))
            y.append(1)

        score_a = 0.5 if winner == "draw" else 1.0
        ra, rda, rb, rdb = sa["elo"], sa["rd"], sb["elo"], sb["rd"]
        sa["elo"], sa["rd"] = update_rating(ra, rda, rb, rdb, score_a)
        sb["elo"], sb["rd"] = update_rating(rb, rdb, ra, rda, 1 - score_a)

        for s, side in ((sa, "a"), (sb, "b")):
            s["n"] += 1
            for k in STATS:
                s[k] += int(fight[f"{k}_{side}"])

    return X, y, state

def side_flip(X, y, seed=0):
    """Negate ~half the rows (target -> 0) so the label is balanced ~50/50.

    Without this the model would just learn "fighter_a always wins".
    """
    rng = random.Random(seed)
    for i in range(len(X)):
        if rng.random() < 0.5:
            X[i] = [-v for v in X[i]]
            y[i] = 0
    return X, y

def train():
    X, y, state = build_dataset()
    X, y = side_flip(X, y)

    cut = int(len(X) * 0.8)
    Xtr, ytr, Xval, yval = X[:cut], y[:cut], X[cut:], y[cut:]

    model = HistGradientBoostingClassifier(random_state=0)
    model.fit(Xtr, ytr)

    pred = model.predict(Xval)
    prob = model.predict_proba(Xval)
    print(f"Trained on {len(Xtr)} fights, validated on {len(Xval)}.")
    print(f"Label balance (all rows): {sum(y) / len(y):.1%} class 1")
    print(f"Validation accuracy: {accuracy_score(yval, pred):.3f}")
    print(f"Validation log-loss: {log_loss(yval, prob):.3f}")
    return model, state

def load_model():
    """Return (model, state), retraining only if the cache is missing or stale."""
    if os.path.exists(MODEL_PKL) and os.path.getmtime(MODEL_PKL) >= os.path.getmtime(FIGHTS_CSV):
        with open(MODEL_PKL, "rb") as f:
            return pickle.load(f)
    model, state = train()
    with open(MODEL_PKL, "wb") as f:
        pickle.dump((model, state), f)
    return model, state

def predict(model, state, f1, f2):
    """Return (winner_name, win_probability) for a hypothetical f1 vs f2."""
    if f1 not in state or f2 not in state:
        missing = [n for n in (f1, f2) if n not in state]
        raise KeyError(f"Unknown fighter(s): {', '.join(missing)}")

    p_fwd = model.predict_proba([features(state[f1], state[f2])])[0][1]
    p_rev = model.predict_proba([features(state[f2], state[f1])])[0][1]
    p1 = 0.5 * (p_fwd + (1 - p_rev))
    if p1 >= 0.5:
        return f1, p1
    return f2, 1 - p1

def main():
    model, state = train()
    print("\nEnter two fighters to predict a bout (blank to quit).")
    while True:
        f1 = input("\nFighter 1: ").strip()
        if not f1:
            return
        f2 = input("Fighter 2: ").strip()
        if not f2:
            return
        try:
            winner, prob = predict(model, state, f1, f2)
            print(f"-> {winner} wins ({prob:.1%})")
        except KeyError as e:
            print(e)

if __name__ == "__main__":
    main()
