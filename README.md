# MelonPop

> Can you reach the giant melon?

Physics-based vertical merge puzzle (Suika-style) for Android. Drop fruits into a glass jar; two identical fruits merge into the next, bigger fruit. Reach the melon — and merge two melons into the giant watermelon.

## Project layout

```
MelonPop/
├── backend/     FastAPI + SQLAlchemy + SQLite (anonymous device stats)
└── frontend/    Expo SDK 54 (React Native + TypeScript) game client
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8017
```

SQLite DB is created next to `main.py` (`melonpop.db`); override with the `MELONPOP_DB_PATH` env var (point it at a mounted volume when containerized).

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/devices/register` | Idempotent anonymous device registration |
| POST | `/sessions` | Submit a finished game (validated; returns updated best score) |
| GET | `/sessions/{device_uuid}?limit=50` | Recent sessions, newest first |
| GET | `/stats/{device_uuid}` | Aggregated stats (best, totals, tier distribution, games/day, moving averages) |
| DELETE | `/devices/{device_uuid}/reset` | Wipe the device's sessions (backs "Reset Progress") |

## Frontend

```powershell
cd frontend
npm install
npx expo start
```

Press `a` for the Android emulator, or scan the QR code with Expo Go.

**Backend URL:** by default the app talks to `http://10.0.2.2:8017` on Android (host machine as seen from the emulator) and `http://127.0.0.1:8017` elsewhere. For a real device/deployment set `extra.apiUrl` in `frontend/app.json`, e.g.:

```json
"extra": { "apiUrl": "http://192.168.1.50:8017" }
```

The game is fully playable offline — finished sessions queue locally and sync to the backend in the background whenever it becomes reachable.

## Gameplay

- Drag horizontally to aim, release to drop.
- Two touching fruits of the same tier merge into the next tier (pop animation, particles, sound, haptics, floating `+points`).
- Fruit chain: Cherry → Strawberry → Grape → Mandarin → Persimmon → Apple → Pear → Peach → Coconut → Melon → **Watermelon** (two melons merge into it; watermelon is the cap and doesn't merge further).
- If fruit sits above the dashed danger line for ~1.8 s continuously, the game ends (the line pulses red and the jar shakes as a warning).
- In-progress games are auto-saved and resume when you return to the game screen.

## Identity & data

No login anywhere. A UUID v4 is generated on first launch, stored locally, and silently registered with the backend. All stats/charts are computed from real recorded game sessions (local history merged with the backend mirror); the Stats screen shows a friendly empty state until the first game is played.
