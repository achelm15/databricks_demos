# MLB 2025 Season Dataset Builder

This project fetches and combines data from three MLB APIs to create a comprehensive dataset of the 2025 baseball season including schedule, attendance, and uniform data.

## Features

- **Schedule Data**: Complete 2025 regular season schedule with team information, scores, and game details
- **Attendance Data**: Game attendance figures including handling of double headers
- **Uniform Data**: Home and away team uniform styles for each game
- **Flat Dataset**: All data merged into a single DataFrame for easy analysis

## APIs Used

1. **Schedule API**: `https://statsapi.mlb.com/api/v1/schedule?gameType=R&season=2025&sportId=1`
2. **Attendance API**: `https://statsapi.mlb.com/api/v1/attendance?sportId=1&date={date}&gameType=R&teamId={teamId}`
3. **Uniforms API**: `https://statsapi.mlb.com/api/v1/uniforms/game?gamePks={gamePk}`

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Simply open and run the notebook:

```bash
jupyter notebook build_mlb_dataset.ipynb
```

Or if using JupyterLab:

```bash
jupyter lab build_mlb_dataset.ipynb
```

The notebook will:
1. Fetch all 2025 regular season games
2. Parse schedule data into a structured format
3. Fetch attendance data for each game (using home team ID)
4. Fetch uniform data for each game
5. Merge everything into a single DataFrame
6. Save the result as both CSV and Parquet files

## Output

The notebook generates two files:
- `mlb_2025_complete_dataset.csv` - CSV format
- `mlb_2025_complete_dataset.parquet` - Parquet format (recommended for large datasets)

## Dataset Columns

The final dataset includes:
- **Game Info**: gamePk, date, gameDate, season, gameType, status, statusCode
- **Home Team**: home_team_id, home_team_name, home_score, home_wins, home_losses, home_pct, home_is_winner
- **Away Team**: away_team_id, away_team_name, away_score, away_wins, away_losses, away_pct, away_is_winner
- **Venue**: venue_id, venue_name
- **Attendance**: attendance, attendance_high_for_date, attendance_low_for_date, is_doubleheader_date
- **Home Uniforms**: home_jersey, home_pants, home_cap, home_jersey_code
- **Away Uniforms**: away_jersey, away_pants, away_cap, away_jersey_code
- **Game Details**: doubleHeader, gameNumber, dayNight, description, scheduledInnings, seriesGameNumber, gamesInSeries

## Notes

- The notebook includes progress bars (tqdm) for long-running API calls
- Small delays are added to avoid overwhelming the MLB API
- **Double header attendance handling**: The attendance API returns high/low attendance with corresponding gamePks, and the notebook matches these to assign the correct attendance to each game
- **Detailed uniform data**: Jersey, pants, and cap information extracted separately with descriptive names (e.g., "Royals Alt Baby Blue Jersey")
- Games that haven't been played yet will have null values for attendance, scores, and uniforms

