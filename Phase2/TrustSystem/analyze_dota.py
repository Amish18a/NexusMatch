import pandas as pd

df = pd.read_csv(
    "data/dota2_processed/player_reliability_summary.csv"
)

print("\n========== COLUMNS ==========")
print(df.columns.tolist())

print("\n========== SHAPE ==========")
print(df.shape)

print("\n========== FIRST 10 ROWS ==========")
print(df.head(10))

print("\n========== MISSING VALUES ==========")
print(df.isnull().sum())

print("\n========== NUMERIC SUMMARY ==========")
print(df.describe().T)

print("\n========== LEAVER RATE ==========")
print(df["leaver_rate"].describe())

print("\n========== COMPLETION PROXY ==========")
print(df["completion_proxy"].describe())

print("\n========== TOP 20 MOST ACTIVE PLAYERS ==========")
print(
    df.sort_values("matches_played", ascending=False)
      .head(20)
)

print("\n========== HIGHEST LEAVER RATE ==========")
print(
    df.sort_values("leaver_rate", ascending=False)
      .head(20)[
          [
              "account_id",
              "matches_played",
              "leaver_rate",
              "completion_proxy",
              "avg_chat_messages",
              "avg_chat_length"
          ]
      ]
)