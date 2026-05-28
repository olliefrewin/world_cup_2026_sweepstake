# 2026 World Cup Sweepstake

A Windows desktop app for running a workplace sweepstake for the 2026 FIFA World Cup (11 June – 19 July 2026).

---

## Getting the app running — step by step

### Step 1 — Install Python

1. Go to **https://www.python.org/downloads/**
2. Click the big **"Download Python 3.12.x"** button
3. Run the downloaded installer
4. **Important:** on the first screen, tick the box that says **"Add python.exe to PATH"** before clicking Install Now

   ![tick Add to PATH](https://www.python.org/static/img/python-logo.png)

5. Click **Install Now** and wait for it to finish

To check it worked, open **PowerShell** (search for it in the Start menu) and type:
```
python --version
```
You should see something like `Python 3.12.x`. If you get an error, restart your computer and try again.

---

### Step 2 — Download this project

If you have received a `.zip` file of this project, unzip it to somewhere easy to find, such as your Desktop or `C:\Sweepstake\`.

If you are cloning from GitHub:
```
git clone https://github.com/olliefrewin/world_cup_2026_sweepstake.git
```

---

### Step 3 — Install dependencies

Open **PowerShell** and navigate to the project folder. For example, if you unzipped it to your Desktop:
```
cd "$env:USERPROFILE\Desktop\world_cup_2026_sweepstake-main"
```

Then run:
```
python -m pip install -r requirements.txt
python -m pip install -e .
```

Wait for both commands to finish. You should see a list of packages being installed.

---

### Step 4 — Build the app

Still in PowerShell, run:
```
.\build.bat
```

This will take a minute or two. When it finishes you will see:
```
Done. Find your .exe in dist\WorldCupSweepstake.exe
```

---

### Step 5 — Run the app

Open the `dist` folder inside the project folder. Double-click **WorldCupSweepstake.exe**.

The app will open. You only need to repeat Step 5 from now on — you do not need to rebuild every time.

> **Tip:** You can copy `WorldCupSweepstake.exe` anywhere you like — your Desktop, a shared drive, etc. It is fully self-contained and does not need Python installed to run.

---

## Troubleshooting

**"python is not recognized"**
You did not tick "Add python.exe to PATH" during installation. Uninstall Python and reinstall it, making sure to tick that box.

**"pip is not recognized"**
Use `python -m pip` instead of `pip` in all commands above.

**The app opens but shows a blank screen or error**
Make sure you ran `build.bat` from inside the project folder, not from somewhere else.

**The app launches but says "index.html not found"**
You are running an old build. Delete the `dist` folder and run `.\build.bat` again to rebuild.

---

## For developers

Run from source (no build needed):
```
python -m sweepstake
```

Run tests:
```
pytest
```
