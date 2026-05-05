# YourWatchDog

This is an educational project. Not a real antivirus. Not a replacement for Windows Defender.

The goal is simple — show you how ransomware actually behaves, and how detection systems respond to it. Most people have no idea what happens under the hood when ransomware hits. This makes it visible.

---

## What's inside

`attack.py` — simulates ransomware behavior by encrypting files in a folder you choose. You need to pause Windows real-time protection to run it — and that's the point. The moment your guard is down, even a basic script can cause chaos. The key is saved locally so everything is recoverable.

`shield.py` — watches the same folder in real time. When it detects mass file modifications, it freezes the suspicious process, asks what you want to do, and restores everything from a backup it made earlier.

`decrypt.py` — if any files got encrypted before the shield caught the attack, run this to recover them. It uses the same key that attack.py saved locally.

Together they show you the full picture — attack, defense, and recovery, back to back, in real time.

---

## How to run it

You need Python 3.8 or newer. Download from python.org and check *Add Python to PATH* during install.

Install dependencies:

```
pip install watchdog psutil setproctitle cryptography
```

Clone the repo:

```
git clone https://github.com/Koxns/YourWatchDog
cd YourWatchDog
```

Set up the shield and choose a folder to protect:

```
python shield.py --install
```

Start it:

```
python shield.py --start
```

In a new terminal, run the attack:

```
python attack.py
```

Before running attack.py — pause Windows real-time protection temporarily. Settings → Windows Security → Virus & threat protection → turn off real-time protection. Turn it back on after the demo.

Watch what happens. The shield catches it, kills the process, and restores your files.

---

## If files got encrypted before the shield caught it

Run decrypt.py to recover everything:

```
python decrypt.py
```

It will ask which folder to decrypt. Make sure simulation_key.key is in the same folder as decrypt.py — attack.py saves it there automatically.

---

## Commands

```
python shield.py --install      setup and pick folder to protect
python shield.py --start        start monitoring in background
python shield.py --stop         stop
python shield.py --status       check if running
python shield.py --uninstall    remove everything
python decrypt.py               recover files after demo
```

---

## Why I built this

I wanted to understand how ransomware detection actually works — not just read about it. So I built all three sides. The attacker, the defender, and the recovery.

The real lesson here isn't the code. It's that most successful ransomware attacks don't beat antivirus — they wait for someone to turn it off, click the wrong link, or ignore a warning. One moment of distraction is enough.

Keep your real-time protection on. Update your software. Don't open attachments you weren't expecting.

Start breaking, keep learning.

---

Abdul Rahaman — Koxns
