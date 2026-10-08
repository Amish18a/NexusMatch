import pandas as pd

df = pd.read_csv(
    "data/dota2_processed/player_reliability_summary.csv"
)

print("\n========== MATCH HISTORY DISTRIBUTION ==========")

print(
    pd.cut(
        df["matches_played"],
        bins=[0, 1, 2, 4, 9, 19, 49, float("inf")],
        labels=[
            "1",
            "2",
            "3-4",
            "5-9",
            "10-19",
            "20-49",
            "50+"
        ]
    ).value_counts().sort_index()
)

print("\n========== PLAYERS WITH 5+ MATCHES ==========")

df_5 = df[df["matches_played"] >= 5].copy()

print("Number of players:", len(df_5))

print("\nLeaver rate:")
print(df_5["leaver_rate"].describe())

print("\n========== PLAYERS BY LEAVER STATUS ==========")

print(
    df_5["leaver_rate"]
    .gt(0)
    .value_counts()
)

print("\n========== LEAVER RATE BANDS ==========")

print(
    pd.cut(
        df_5["leaver_rate"],
        bins=[-0.001, 0, 0.05, 0.10, 0.20, 0.50, 1.0],
        labels=[
            "0%",
            "0-5%",
            "5-10%",
            "10-20%",
            "20-50%",
            "50-100%"
        ]
    ).value_counts().sort_index()
)

print("\n========== FEATURES ==========")

features = [
    "matches_played",
    "avg_chat_messages",
    "avg_chat_length",
    "avg_time_samples",
    "avg_kda",
    "avg_gold_per_min",
    "avg_xp_per_min",
    "leaver_rate"
]

print(df_5[features].describe().T)

print("\n========== CORRELATION WITH LEAVER RATE ==========")

print(
    df_5[features]
    .corr(numeric_only=True)["leaver_rate"]
    .sort_values()
)