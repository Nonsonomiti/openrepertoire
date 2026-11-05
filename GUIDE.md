# OpenRepertoire: user guide

OpenRepertoire helps you memorise chess openings. You load a course or a study, the app teaches you each line move by move, then brings it back at the right moment so you don't forget it. It runs on your own computer, your data stays with you, and it is free.

Italian version: [GUIDA.md](GUIDA.md)

## Contents

1. [Install and start](#1-install-and-start)
2. [The basics](#2-the-basics)
3. [Importing courses and studies](#3-importing-courses-and-studies)
4. [Learning and reviewing](#4-learning-and-reviewing)
5. [Managing your repertoire](#5-managing-your-repertoire)
6. [Explore](#6-explore)
7. [Stats](#7-stats)
8. [The Personal area](#8-the-personal-area)
9. [Using it from your phone](#9-using-it-from-your-phone)
10. [Lichess token](#10-lichess-token)
11. [Backup and moving to another computer](#11-backup-and-moving-to-another-computer)
12. [Keyboard shortcuts](#12-keyboard-shortcuts)
13. [Troubleshooting](#13-troubleshooting)

## 1. Install and start

Download the file for your system from the [releases page](https://github.com/Nonsonomiti/openrepertoire/releases). You don't need to install anything else.

**Windows.** Download `OpenRepertoire-Windows.zip`, extract `OpenRepertoire.exe` and open it. The first time, Windows may say "Windows protected your PC" because the app isn't signed: click More info, then Run anyway.

**Mac.** Download `OpenRepertoire-macOS-AppleSilicon.zip` (M1, M2, M3, M4 chips) or `OpenRepertoire-macOS-Intel.zip`. Extract `OpenRepertoire.app` and move it to Applications. The first time, macOS blocks it because it isn't signed by Apple: go to System Settings → Privacy & Security and click Open Anyway.

**Linux.** Download `OpenRepertoire-Linux.tar.gz`, extract `OpenRepertoire` and open it with a double click or with `./OpenRepertoire` from a terminal.

The app opens in your browser and keeps running in the background. On a Mac it has no Dock icon. Opening it again just reopens the page. To quit: the "⋯" menu at the top → Quit the app.

**Language.** The IT/EN button at the top switches between Italian and English. The app remembers your choice. On first start it follows your browser's language.

**From source (optional).** If you prefer the code, download it and run `MacOS_start_app.command`, `Windows_start_app.bat` or `start.sh`. You need Python 3; the other dependencies install themselves.

## 2. The basics

At the top left there are two areas:

- **Courses**: the PGN files you loaded. Sections: Learn, Repertoire, Explore, Review, Stats.
- **Personal**: tools that don't start from a course. Sections: Games, Opponent, Build, Sparring, Endgames.

A few words used throughout:

- **Line**: one sequence of moves to memorise.
- **Course** and **chapter**: how lines are grouped.
- The number at the top right is how many lines are due today.
- The theme icon offers five colour themes. Repertoire → Appearance lets you change the board, pieces, board size, animation speed and sounds.

No files yet? On the empty Repertoire page, press "Load an example course" to try the app in a minute.

## 3. Importing courses and studies

Go to Repertoire → **Import course (PGN)**.

1. Choose your colour: White, Black or Automatic.
2. Choose the PGN file.
3. Press Load file.

The course takes the file's name. If you import the same lines twice, the duplicates are skipped, so your progress is safe. Lines with illegal moves are skipped and the app tells you how many.

**Automatic** takes the colour from the Lichess study board. If there isn't one and the PGN starts from a set position, you play the side to move. This suits tactics and strategy courses.

**Lichess studies.** Download the study's PGN from Lichess and import it. The app reads the study name as the course, the chapter name as the chapter, and the board orientation as your colour (choose Automatic).

**"Each branch is a line to study".** Tick this for Lichess studies and for repertoires you built yourself with ChessBase or SCID: every branch becomes its own line. Leave it off for courses you bought: there the branches are the author's ideas, so only the main line is studied and the side moves appear inside the comment, where you can click them to preview them on the board.

Arrows and circles drawn by the author in the PGN appear on the board by themselves.

## 4. Learning and reviewing

**Learn** picks the first line you haven't studied. A new line goes through these stages:

1. **Stage 1**: the app shows the move to play with the author's comment, plus an arrow. Play it on the board, or press "Let me move" (Space) first.
2. **Stage 2**: you replay the whole line from memory, twice.
3. **Mistake review**: if you went wrong, you repeat those exact positions for three rounds.

The line then leaves the "to learn" list and comes back in **Review** when it's due.

**How the schedule works.** You don't rate yourself: the app counts your mistakes. In a review, no mistakes means Easy, one means Hard, two or more means Forgotten. A line played correctly returns after 6 hours, 1 day, 3 days, 7 days, then at growing intervals up to 6 months at most. A forgotten line returns after 10 minutes and starts its sequence again.

**During training:**

- **Hint** (H): first shows the piece, then the move. It counts as a mistake.
- **Blindfold** (B): hides the pieces.
- **Flip** (F): turns the board round.
- **Analyse on Lichess**: opens the position on the Lichess site.

**Reading a line.** Click a line in Repertoire to walk through it with its comments, without being tested. Use Space or the arrow keys.

**Reviewing ahead of time.** Before a tournament, the clock icon on a course or chapter makes its lines reviewable now. The schedule isn't otherwise changed.

**Skipping what you know.** In Repertoire → Appearance you can turn on "In review, skip the opening you already played correctly today". Lines sharing their first moves then start where they differ.

## 5. Managing your repertoire

The Repertoire page lists all lines by course and chapter. A filter box searches titles, courses and chapters. The coloured dot beside each line shows its status: to learn, to review or scheduled.

Icons on each row let you:

- **Course**: learn it, make it reviewable now, rename it, delete it. Deleting a whole course asks you to type `delete` to confirm.
- **Chapter**: add a line, make it reviewable now, rename it, merge it into another chapter.
- **Line**: edit moves, duplicate into a new line, export, move to another course or chapter, delete.

**Create / edit → New line** opens the editor. Play the moves on the board, then give a title, course, chapter and colour. Typing a new course or chapter name creates it. "Set up position" lets you start from any position by dragging pieces and setting the side to move, castling and en passant.

**Find position** tells you which lines reach a position: paste a FEN or use the one on the board.

**Export / backup** downloads your lines as PGN: everything, one course, one chapter, or lines you tick by hand. Options:

- **Moves only**: no comments, for a clean file.
- **Merge the lines into a tree**: gives one branching chapter on Lichess instead of many nearly identical ones.
- **Merge the chapters too**: one chapter per course, and you can pick which chapters to include.

Without "moves only", importing the file again restores course, chapter and colour.

## 6. Explore

Explore shows your whole repertoire as a tree. Choose the colour and course at the top, then play moves on the board or click them in the lists. The left and right arrows go back and forward.

- **Continuations in the repertoire**: your moves from this position and how many lines use them.
- **Coverage gap**: a warning when it's your turn and no move is prepared.
- **Lines ending here**: click to open them.
- **Note**: write your own notes on a position and tag them Key position, Needs analysis or Idea. A note belongs to the position, so it also appears if you reach it by another move order. **Position notes** lists them all, with a filter by tag and a link to Lichess. Your notes never change the course's comments.
- **Lichess database**: moves really played, from masters or online games, with filters by year, time control and rating. A tick marks moves in your repertoire; a warning sign marks opponent moves you have no reply to. It shows the share of games your repertoire covers, and model games with masters. This needs the [token](#10-lichess-token).
- **Lichess analysis (cloud)**: engine evaluation and best lines, when Lichess has them for that position. No token needed.
- **Transpositions & conflicts**: positions reached by more than one move order. "Conflict" means you have two different moves of yours from the same position, so it's worth checking.

## 7. Stats

Totals, accuracy, your study streak, recall rate over the last 14 days, accuracy by course and colour, reviews coming up in the next 14 days, and your hardest lines.

## 8. The Personal area

Games, opponents and endgames are stored separately from your courses (`personal.json`). Build and Sparring need the [token](#10-lichess-token).

**Games.** Enter your Lichess and/or Chess.com username and press Download: games are public, so no password is needed. The app compares them with your repertoire and shows:

- **Where you deviated**: you played something else where you had a prepared move. "Review" puts those lines back into review.
- **Where the opponent left the repertoire**: a move you have no reply to. "Prepare" opens the editor with the line already played up to there.

The board lets you browse what you played from each position, with results.

**Opponent.** Enter the username of someone you're about to play and your colour. The app downloads their public games and tells you what they play, where they leave your repertoire, and which of your lines matter against them. "Review these lines" starts one session with just those.

**Build.** Create a repertoire without a course. On your turn you choose a move; on the opponent's turn the app shows their most played replies in the database and marks those still to cover. You set the threshold (for example, replies played in at least 5% of games). "Save this line" stores it and takes you back to the opponent's last branching point. Lines go into a course of yours, "My repertoire" by default, and you study them from Courses.

**Sparring.** Play against the database: the opponent picks moves like real players at the chosen level, in proportion to how often they're played. Your moves are checked against your repertoire. At the end you see the replies you're missing, and you can prepare them or save the game as a line. The game ends when the database runs out of games.

**Endgames.** Lucena, Philidor, king and pawn, basic mates and more. You play against the Lichess tablebase, which defends perfectly, and positions come back with the same spaced repetition as your lines. Add your own under "Add a position": a FEN with 7 pieces at most. You play the side to move, and the tablebase decides whether the goal is to win or to hold the draw.

## 9. Using it from your phone

1. On the computer, click the phone icon at the top → Turn on.
2. Scan the QR code with your phone's camera. Phone and computer must be on the same Wi-Fi.
3. Enter the PIN shown on the computer. It's asked only once.

On the phone, Share → Add to Home Screen opens it full screen like an app. Your data stays on the computer, which must be on with the app open. The first time, the computer may ask whether to allow incoming connections: answer Allow. "New PIN" logs out the phones already connected.

Away from home it works with a private network such as Tailscale (free), installed on both computer and phone.

## 10. Lichess token

The Lichess database (Explore, Build, Sparring) needs a free personal token.

1. Sign in to Lichess and open [the token page](https://lichess.org/account/oauth/token/create?description=openrepertoire). You don't need to tick any permission.
2. Create the token and copy it.
3. In the app go to Courses → Explore → open "Lichess database", paste it and press Save.

The token stays on your computer in `lichess_token.txt`.

## 11. Backup and moving to another computer

"⋯" menu → **Data folder** shows where everything is and opens it. To back up or move your data, copy these files:

- `repertoire.json`: courses and progress
- `personal.json`: games, opponents, endgames, notes
- `lichess_token.txt`: your token

The default locations are `Library/Application Support/OpenRepertoire` in your home folder on a Mac, `%APPDATA%\OpenRepertoire` on Windows and `~/.local/share/openrepertoire` on Linux. With the source-code version, the files sit next to `app.py`.

You can also keep a PGN copy with Export / backup, though that doesn't include your progress.

## 12. Keyboard shortcuts

| Key | Action |
| --- | --- |
| Space | Next / confirm |
| ← → | Previous / next move (reading, Explore, Games, Opponent, Build) |
| F | Flip the board |
| H | Hint (review and endgames) |
| B | Blindfold |
| ? | Show the shortcuts |
| Esc | Close menus and windows |
| Right-click on the board | Draw arrows and circles (one click clears them) |

## 13. Troubleshooting

- **What works offline?** Learning, reviewing and managing your repertoire. The Lichess database, cloud analysis, tablebase and game downloads need internet.
- **"Lichess isn't responding" with a certificate error** (source-code version only): Python is missing its certificates. On a Mac open Applications → Python 3.x → Install Certificates.command and restart the app, or run `python3 -m pip install --user certifi`.
- **Too many requests**: Lichess limits how fast you can ask. Wait a minute.
- **The phone can't connect**: check both are on the same Wi-Fi and the app is open on the computer, then reopen the phone window on the computer.

Bug reports and suggestions: @nonsonomiti on Instagram.
