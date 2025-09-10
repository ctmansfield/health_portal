# Light Mode — Minimal Friction

This repo can run with **no automation overhead** while you iterate quickly.

## Toggle automation
```bash
# turn OFF all workflows and CODEOWNERS (keeps files, just moves them)
scripts/hp_light_mode.sh off

# turn ON again later
scripts/hp_light_mode.sh on

# see current state
scripts/hp_light_mode.sh status
```

## Manual commit flow
```bash
# optional: run your local verify script if present
./VERIFY_ALL.sh   # if it exists

# then make a commit (script will run VERIFY_ALL.sh if present and prompt you)
scripts/hp_manual_commit.sh "feature: update renderer with patient-mode"
```
