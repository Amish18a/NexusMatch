"""
NexusMatch - Dota 2 dataset import and preprocessing pipeline.

Selected source files from the Kaggle Dota 2 Matches dataset:
    - match.csv
    - players.csv
    - player_time.csv
    - chat.csv

The raw Kaggle files are NOT committed to GitHub because the full dataset is large.
This script downloads only the four selected files when Kaggle access is available.

Outputs:
    data/dota2_processed/match_processed.csv
    data/dota2_processed/players_processed.csv
    data/dota2_processed/player_time_processed.csv
    data/dota2_processed/chat_processed.csv
    data/dota2_processed/player_behavior_features.csv
    data/dota2_processed/player_reliability_summary.csv
"""

from __future__ import annotations

import csv
from pathlib import Path
import re
import zipfile

import numpy as np
import pandas as pd

try:
    import kagglehub
except ImportError as exc:
    raise SystemExit(
        "kagglehub is required. Install dependencies with: pip install -r requirements.txt"
    ) from exc


BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "dota2_raw"
PROCESSED_DIR = BASE_DIR / "data" / "dota2_processed"

DATASET_HANDLE = "devinanzelmo/dota-2-matches"
SELECTED_FILES = ("match.csv", "players.csv", "player_time.csv", "chat.csv")

PLAYER_SLOTS = (0, 1, 2, 3, 4, 128, 129, 130, 131, 132)


def materialize_dataset_file(path: Path) -> Path:
    """
    Return a real CSV path.

    KaggleHub can return a ZIP payload even when an individual dataset path is
    requested. The current downloaded files begin with the ZIP signature
    PK, so we detect and extract that payload before pandas reads it.
    """
    try:
        with path.open("rb") as file:
            signature = file.read(4)
    except OSError:
        return path

    if signature != b"PK\x03\x04":
        return path

    extract_dir = path.parent / "_extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    expected_name = path.name
    target = extract_dir / expected_name

    if target.exists():
        return target

    try:
        with zipfile.ZipFile(path, "r") as archive:
            members = archive.namelist()

            candidates = [
                member
                for member in members
                if Path(member).name.lower() == expected_name.lower()
            ]

            if not candidates:
                stem = Path(expected_name).stem.lower()
                candidates = [
                    member
                    for member in members
                    if Path(member).suffix.lower() == ".csv"
                    and Path(member).stem.lower() == stem
                ]

            if not candidates:
                raise RuntimeError(
                    f"ZIP archive {path.name} does not contain {expected_name}."
                )

            member = candidates[0]
            extracted = Path(archive.extract(member, extract_dir))

            if extracted.resolve() != target.resolve():
                if target.exists():
                    target.unlink()
                extracted.replace(target)

            print(
                f"  Extracted {path.name} -> {target.name} "
                f"from archive member {member}"
            )
            return target

    except zipfile.BadZipFile as exc:
        raise RuntimeError(
            f"{path.name} begins with a ZIP signature but is not a valid ZIP archive."
        ) from exc


def download_selected_files() -> dict[str, Path]:
    """Download only the four required Kaggle files and return their paths."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    for filename in SELECTED_FILES:
        target = RAW_DIR / filename

        if not target.exists():
            downloaded = kagglehub.dataset_download(
                DATASET_HANDLE,
                path=filename,
                output_dir=str(RAW_DIR),
            )
            downloaded_path = Path(downloaded)
            if downloaded_path.is_file():
                target = downloaded_path

        if not target.exists():
            raise FileNotFoundError(
                f"Could not find {filename}. Expected it at {target}."
            )

        paths[filename] = materialize_dataset_file(target)

    return paths


def detect_delimiter(sample_text: str) -> str:
    """Detect common CSV delimiters, with comma as the default."""
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=",;\t|")
        if dialect.delimiter in {",", ";", "\t", "|"}:
            return dialect.delimiter
    except csv.Error:
        pass

    return ","


def read_match_csv_tolerant(path: Path) -> pd.DataFrame:
    """
    Read match.csv defensively.

    The published Dota 2 match table is a simple scalar table (historically
    50,000 matches and 13 columns). The local download currently contains
    malformed quote characters on some rows, so a strict CSV parser is not
    appropriate. We recover rows using the header width and comma separation,
    while recording any unrecoverable rows.
    """
    encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            text = path.read_text(encoding=encoding, errors="strict")
            lines = text.splitlines()

            header_index = None
            header = None

            for index, line in enumerate(lines[:50]):
                candidate = [
                    part.strip().strip('"').strip("'")
                    for part in line.replace("\ufeff", "").split(",")
                ]
                if "match_id" in candidate and "radiant_win" in candidate:
                    header_index = index
                    header = candidate
                    break

            if header_index is None or header is None:
                raise ValueError(
                    f"Could not locate a match.csv header in {path.name}"
                )

            expected_columns = len(header)
            rows = []
            bad_rows = []

            for line_number, line in enumerate(
                lines[header_index + 1 :], start=header_index + 2
            ):
                if not line.strip():
                    continue

                # First try the normal CSV reader. strict=False allows the
                # parser to recover some quote irregularities.
                try:
                    parsed = next(
                        csv.reader(
                            [line],
                            delimiter=",",
                            quotechar='"',
                            strict=False,
                        )
                    )
                except (csv.Error, StopIteration):
                    parsed = []

                parsed = [str(value).strip().strip('"') for value in parsed]

                # Fallback: match.csv has no free-text fields, so stripping
                # quote characters and splitting on commas is safe here.
                if len(parsed) != expected_columns:
                    parsed = [
                        part.strip().strip('"').strip("'")
                        for part in line.split(",")
                    ]

                if len(parsed) == expected_columns:
                    rows.append(parsed)
                else:
                    bad_rows.append(
                        {
                            "line_number": line_number,
                            "field_count": len(parsed),
                            "raw_line": line,
                        }
                    )

            frame = pd.DataFrame(rows, columns=header)

            bad_path = PROCESSED_DIR / "match_bad_rows.csv"
            if bad_rows:
                PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
                pd.DataFrame(bad_rows).to_csv(
                    bad_path, index=False, encoding="utf-8"
                )

            print(
                f"  Read {path.name}: encoding={encoding}, "
                f"rows={len(frame):,}, columns={len(frame.columns)}, "
                f"skipped_malformed_rows={len(bad_rows):,}"
            )

            if bad_rows:
                print(f"  Malformed match rows were saved to: {bad_path}")

            return frame

        except (UnicodeDecodeError, OSError, ValueError) as exc:
            last_error = exc

    raise RuntimeError(
        f"Could not recover {path.name} using the tolerant match parser. "
        f"Last error: {last_error}"
    )


def read_csv_with_encoding(path: Path) -> pd.DataFrame:
    """
    Read a Dota CSV with encoding/quoting fallbacks.

    match.csv is handled by a dedicated tolerant reader because the local
    downloaded copy contains malformed quote characters. The other selected
    files retain ordinary CSV parsing with common encoding fallbacks.
    """
    if path.name.lower() == "match.csv":
        return read_match_csv_tolerant(path)

    encodings = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
    last_error: Exception | None = None

    for encoding in encodings:
        try:
            with path.open(
                "r", encoding=encoding, errors="strict", newline=""
            ) as file:
                sample = file.read(20000)

            delimiter = detect_delimiter(sample)

            frame = pd.read_csv(
                path,
                encoding=encoding,
                sep=delimiter,
                engine="python",
            )

            print(
                f"  Read {path.name}: encoding={encoding}, "
                f"delimiter={repr(delimiter)}, rows={len(frame):,}, "
                f"columns={len(frame.columns)}"
            )
            return frame

        except (
            UnicodeDecodeError,
            pd.errors.ParserError,
            csv.Error,
            ValueError,
        ) as exc:
            last_error = exc

    raise RuntimeError(
        f"Could not parse {path.name} with the supported encodings/delimiters. "
        f"Last error: {last_error}"
    )


def load_selected_files(paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    """Load the four selected CSV files into pandas DataFrames."""
    frames = {
        "match": read_csv_with_encoding(paths["match.csv"]),
        "players": read_csv_with_encoding(paths["players.csv"]),
        "player_time": read_csv_with_encoding(paths["player_time.csv"]),
        "chat": read_csv_with_encoding(paths["chat.csv"]),
    }

    print("\nLoaded datasets:")
    for name, frame in frames.items():
        print(
            f"  {name:<12} rows={len(frame):>9,}  "
            f"columns={len(frame.columns):>3}"
        )

    return frames


def numeric_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Convert existing columns to numeric values in place."""
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")


def clean_text(value: object) -> str:
    """Normalize text without removing words that may be useful for NLP."""
    if pd.isna(value):
        return ""
    text = str(value).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


def preprocess_match(df: pd.DataFrame) -> pd.DataFrame:
    """Clean match-level records."""
    df = df.copy()

    df = df.drop_duplicates(
        subset=["match_id"] if "match_id" in df.columns else None
    )

    numeric_columns(
        df,
        [
            "match_id",
            "start_time",
            "duration",
            "tower_status_radiant",
            "tower_status_dire",
            "barracks_status_radiant",
            "barracks_status_dire",
            "first_blood_time",
            "game_mode",
            "positive_votes",
            "negative_votes",
            "cluster",
        ],
    )

    if "start_time" in df.columns:
        df["start_datetime"] = pd.to_datetime(
            df["start_time"], unit="s", errors="coerce", utc=True
        )

    if "radiant_win" in df.columns:
        radiant = df["radiant_win"].astype(str).str.strip().str.lower()
        df["radiant_win"] = radiant.map(
            {"true": 1, "false": 0, "1": 1, "0": 0}
        )

    if "duration" in df.columns:
        df["duration_minutes"] = df["duration"] / 60.0

    return df.reset_index(drop=True)


def preprocess_players(df: pd.DataFrame) -> pd.DataFrame:
    """Clean player-level records and add useful behavioral indicators."""
    df = df.copy()

    df = df.drop_duplicates(
        subset=["match_id", "player_slot"]
        if {"match_id", "player_slot"}.issubset(df.columns)
        else None
    )

    numeric_columns(
        df,
        [
            "match_id",
            "account_id",
            "hero_id",
            "player_slot",
            "gold",
            "gold_spent",
            "gold_per_min",
            "xp_per_min",
            "kills",
            "deaths",
            "assists",
            "denies",
            "last_hits",
            "stuns",
            "hero_damage",
            "hero_healing",
            "tower_damage",
            "leaver_status",
        ],
    )

    if "account_id" in df.columns:
        df["is_anonymous"] = df["account_id"].fillna(0).eq(0).astype(int)

    if "player_slot" in df.columns:
        df["team"] = np.where(df["player_slot"] >= 128, "Dire", "Radiant")

    if "leaver_status" in df.columns:
        df["leaver_status"] = df["leaver_status"].fillna(0).astype(int)
        df["leaver_flag"] = df["leaver_status"].gt(0).astype(int)

    if {"kills", "deaths", "assists"}.issubset(df.columns):
        df["kda_ratio"] = (
            df["kills"].fillna(0) + df["assists"].fillna(0)
        ) / (df["deaths"].fillna(0) + 1)

    performance_cols = [
        "gold",
        "gold_spent",
        "gold_per_min",
        "xp_per_min",
        "kills",
        "deaths",
        "assists",
        "denies",
        "last_hits",
        "stuns",
        "hero_damage",
        "hero_healing",
        "tower_damage",
    ]

    for column in performance_cols:
        if column in df.columns:
            df[column] = df[column].fillna(df[column].median())

    return df.reset_index(drop=True)


def preprocess_player_time(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the time-series table and add a match sampling indicator."""
    df = df.copy()

    numeric_columns(df, ["match_id", "times"])

    time_columns = [
        column
        for column in df.columns
        if column.startswith(("gold_t_", "lh_t_", "xp_t_"))
    ]
    numeric_columns(df, time_columns)

    df = df.sort_values(["match_id", "times"]).reset_index(drop=True)
    df["time_seconds"] = df["times"]

    for column in time_columns:
        df[column] = df.groupby("match_id", sort=False)[column].ffill()

    return df


def preprocess_chat(df: pd.DataFrame) -> pd.DataFrame:
    """Clean chat logs while retaining text for later NLP work."""
    df = df.copy()

    numeric_columns(df, ["match_id", "slot", "time"])

    if "key" in df.columns:
        df["key"] = df["key"].fillna("unknown").map(clean_text)

    if "unit" in df.columns:
        df["text"] = df["unit"].map(clean_text)
    else:
        df["text"] = ""

    df["text"] = df["text"].fillna("")
    df = df[df["text"].ne("")].copy()

    df["text_length"] = df["text"].str.len()
    df["word_count"] = df["text"].str.split().str.len()
    df["has_question"] = df["text"].str.contains(r"\?", regex=True).astype(int)
    df["has_exclamation"] = df["text"].str.contains(r"!", regex=True).astype(int)

    return df.reset_index(drop=True)


def build_final_player_time_snapshot(
    player_time: pd.DataFrame,
) -> pd.DataFrame:
    """Convert the latest match snapshot from wide format to player format."""
    latest = (
        player_time.sort_values(["match_id", "times"])
        .groupby("match_id", as_index=False)
        .tail(1)
        .copy()
    )

    snapshots = []

    for slot in PLAYER_SLOTS:
        gold_col = f"gold_t_{slot}"
        lh_col = f"lh_t_{slot}"
        xp_col = f"xp_t_{slot}"

        available = [
            c for c in (gold_col, lh_col, xp_col)
            if c in latest.columns
        ]

        if len(available) != 3:
            continue

        snapshot = latest[["match_id", "times", *available]].copy()

        snapshot = snapshot.rename(
            columns={
                gold_col: "final_gold",
                lh_col: "final_last_hits",
                xp_col: "final_xp",
            }
        )

        snapshot["player_slot"] = slot
        snapshots.append(snapshot)

    if not snapshots:
        return pd.DataFrame(
            columns=[
                "match_id",
                "times",
                "player_slot",
                "final_gold",
                "final_last_hits",
                "final_xp",
            ]
        )

    return pd.concat(snapshots, ignore_index=True)


def build_chat_features(chat: pd.DataFrame) -> pd.DataFrame:
    """Aggregate chat activity per player per match for downstream modeling."""
    group_cols = ["match_id", "slot"]
    grouped = chat.groupby(group_cols, dropna=False)

    features = grouped.agg(
        chat_message_count=("text", "size"),
        avg_message_length=("text_length", "mean"),
        avg_word_count=("word_count", "mean"),
        first_chat_time=("time", "min"),
        last_chat_time=("time", "max"),
        question_count=("has_question", "sum"),
        exclamation_count=("has_exclamation", "sum"),
    ).reset_index()

    features["chat_active"] = features["chat_message_count"].gt(0).astype(int)
    features = features.rename(columns={"slot": "player_slot"})

    return features


def build_player_behavior_features(
    match: pd.DataFrame,
    players: pd.DataFrame,
    player_time: pd.DataFrame,
    chat: pd.DataFrame,
) -> pd.DataFrame:
    """Combine the four source files into a player-match feature table."""
    player = players.copy()

    match_cols = [
        column
        for column in [
            "match_id",
            "duration",
            "duration_minutes",
            "game_mode",
            "radiant_win",
            "cluster",
        ]
        if column in match.columns
    ]

    player = player.merge(
        match[match_cols],
        on="match_id",
        how="left",
    )

    snapshot = build_final_player_time_snapshot(player_time)

    player = player.merge(
        snapshot,
        on=["match_id", "player_slot"],
        how="left",
    )

    sample_counts = (
        player_time.groupby("match_id")["times"]
        .nunique()
        .rename("time_sample_count")
        .reset_index()
    )

    player = player.merge(
        sample_counts,
        on="match_id",
        how="left",
    )

    chat_features = build_chat_features(chat)

    player = player.merge(
        chat_features,
        on=["match_id", "player_slot"],
        how="left",
    )

    for column in [
        "chat_message_count",
        "question_count",
        "exclamation_count",
        "chat_active",
        "time_sample_count",
    ]:
        if column in player.columns:
            player[column] = player[column].fillna(0)

    for column in [
        "avg_message_length",
        "avg_word_count",
        "final_gold",
        "final_last_hits",
        "final_xp",
    ]:
        if column in player.columns:
            player[column] = player[column].fillna(0)

    return player


def build_reliability_summary(
    player_behavior: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate repeated non-anonymous player records into behavioral features."""
    if "account_id" not in player_behavior.columns:
        return pd.DataFrame()

    eligible = player_behavior[
        player_behavior["account_id"].fillna(0).ne(0)
    ].copy()

    if eligible.empty:
        return pd.DataFrame()

    summary = (
        eligible.groupby("account_id", as_index=False)
        .agg(
            matches_played=("match_id", "nunique"),
            avg_kda=("kda_ratio", "mean"),
            avg_gold_per_min=("gold_per_min", "mean"),
            avg_xp_per_min=("xp_per_min", "mean"),
            leaver_rate=("leaver_flag", "mean"),
            avg_chat_messages=("chat_message_count", "mean"),
            avg_chat_length=("avg_message_length", "mean"),
            avg_time_samples=("time_sample_count", "mean"),
        )
    )

    summary["completion_proxy"] = 1 - summary["leaver_rate"]

    summary["reliability_note"] = (
        "Dota 2 contains leaver/player-behavior signals but does not directly "
        "provide NexusMatch queue-abandonment or join-attempt logs."
    )

    return summary


def save_outputs(
    match: pd.DataFrame,
    players: pd.DataFrame,
    player_time: pd.DataFrame,
    chat: pd.DataFrame,
    player_behavior: pd.DataFrame,
    reliability: pd.DataFrame,
) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "match_processed.csv": match,
        "players_processed.csv": players,
        "player_time_processed.csv": player_time,
        "chat_processed.csv": chat,
        "player_behavior_features.csv": player_behavior,
        "player_reliability_summary.csv": reliability,
    }

    for filename, frame in outputs.items():
        frame.to_csv(PROCESSED_DIR / filename, index=False)
        print(
            f"Saved: {PROCESSED_DIR / filename} ({len(frame):,} rows)"
        )


def main() -> None:
    print("NexusMatch - Dota 2 Data Preprocessing")
    print("=" * 48)

    paths = download_selected_files()
    raw = load_selected_files(paths)

    match = preprocess_match(raw["match"])
    players = preprocess_players(raw["players"])
    player_time = preprocess_player_time(raw["player_time"])
    chat = preprocess_chat(raw["chat"])

    player_behavior = build_player_behavior_features(
        match=match,
        players=players,
        player_time=player_time,
        chat=chat,
    )

    reliability = build_reliability_summary(player_behavior)

    save_outputs(
        match,
        players,
        player_time,
        chat,
        player_behavior,
        reliability,
    )

    print("\nPreprocessing completed successfully.")
    print(f"Processed files are in: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
