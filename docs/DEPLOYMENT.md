# Deployment guide: running the plugin host on your own machine

This guide is for trying the Second Brain plugins on your own computer. It is a **test build**. Read
[the README's "What it does not do"](../README.md#what-it-does-not-do) first.

Time needed: about 20 minutes, not counting the Python install.

---

## 1. What you need

| Need | Why | How to check |
|---|---|---|
| Python 3.11 or newer | runs the host | `python --version` |
| `git` | to get the plugin repositories | `git --version` |
| A folder of Markdown notes (your vault) | what the plugins read | any folder with `.md` files will do |
| The plugin repositories | the plugins themselves | see section 3 |

The host reads your notes but never changes them. Keep a copy of your vault if you want to be careful.

## 2. Get the host

Clone the host repository:

```bash
git clone https://github.com/zeemoussa-dev/sb_base_plugins_host.git
cd sb_base_plugins_host
```

Create a virtual environment and install the packages:

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS or Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Get the plugins

Clone each plugin you want into its own folder, next to the host or anywhere you like. For the first test
we recommend the two plugins the host has been run with:

```bash
git clone https://github.com/zeemoussa-dev/sb-plugins-entities.git
git clone https://github.com/zeemoussa-dev/sb-plugins-azure-cost-manager.git
```

Keep the folder names as they are. The host reads the plugin id from each folder's `plugin.json`, not from
the folder name, but the names are easier to recognise.

## 4. Choose three folders

You need three folders. You can create them anywhere:

| Folder | What goes in it | Example (Windows) | Example (macOS/Linux) |
|---|---|---|---|
| Vault | your Markdown notes | `C:\Users\you\Notes` | `~/Notes` |
| Data | each plugin's own files and settings | `C:\Users\you\sbhost-data` | `~/sbhost-data` |
| Plugins | the plugin folders from section 3 | the two clone folders | the two clone folders |

The data folder is created for you if it does not exist.

## 5. Start the host

**Windows (PowerShell):**

```powershell
python -m sbhost serve `
  --plugins C:\path\to\sb-plugins-entities C:\path\to\sb-plugins-azure-cost-manager `
  --vault C:\Users\you\Notes `
  --data C:\Users\you\sbhost-data `
  --port 8000
```

**macOS or Linux:**

```bash
python -m sbhost serve \
  --plugins ~/code/sb-plugins-entities ~/code/sb-plugins-azure-cost-manager \
  --vault ~/Notes \
  --data ~/sbhost-data \
  --port 8000
```

The terminal prints which plugins loaded and which were refused, with the reason. It keeps running until you
press `Ctrl+C`.

## 6. Open it

Open this address in your browser:

```
http://127.0.0.1:8000/host/plugins
```

It lists the loaded plugins and any refusals. The plugins' own screens are on the same address, under
each plugin's routes.

Only your own computer can reach `127.0.0.1`. Do not change the address to `0.0.0.0` or a network address:
there is no sign-in, so anyone on that network could see your notes through the screens.

## 7. Read a refusal

A plugin is refused, and not loaded, in these cases. Each refusal says which:

| Message contains | What to do |
|---|---|
| `requires ... which was refused` | Fix the required plugin first. It is listed in the same refusal list. |
| `its required plugins are not in the install` | Add the required plugin folder to `--plugins`. Azure Customer 360 needs `entities` only for its Entities features; it loads without it. |
| `its register failed` | Send us the whole line. It names the Plugin API call the host does not provide yet. |
| `its plugin.json cannot be read` | The folder has no valid `plugin.json`. Check the clone is complete. |

## 8. Run the nightly refresh (optional)

The host does not run a scheduler. To refresh Azure Customer 360 once, run:

```bash
python -m sbhost refresh --plugin azure-cost-manager \
  --plugins <plugin folders> --vault <vault folder> --data <data folder>
```

It starts the refresh, waits for it, and exits:

| Exit code | Meaning |
|---|---|
| 0 | It finished without errors. |
| 1 | It was refused, failed, or ran longer than six hours. The output says why. |
| 2 | Another refresh is running. |

To run it every night, use your system's scheduler:

- **Windows:** Task Scheduler, action "Start a program", with `python` as the program and the arguments
  above (run from the host folder, using the virtual environment's `python.exe`).
- **macOS or Linux:** `cron`, for example `0 2 * * * cd ~/sb_base_plugins_host && .venv/bin/python -m sbhost refresh ...`.

The Azure refresh needs your Azure sign-in. **That path has not been tested against a real account.** Run it
once by hand first and look at the output before you schedule it.

If a refresh was killed part-way (power cut, a crash), it can leave a lock file behind, and the next run
exits with code 2. Check that no refresh is running, then delete `refresh.lock` in the data folder.

## 9. Stop the host

Press `Ctrl+C` in the terminal where it is running.

## 10. Remove it

Delete the host folder, the plugin folders, and the data folder. Your vault is untouched by the host, so
you do not need to restore anything.

## Troubleshooting

| Problem | What to try |
|---|---|
| `python` not found | Use `python3` on macOS and Linux, or reinstall Python with "Add to PATH" ticked on Windows. |
| `ModuleNotFoundError` | The virtual environment is not active, or `pip install -r requirements.txt` failed. Activate and run it again. |
| The page is blank or says "not found" | Check the plugin loaded in `/host/plugins`. Some screens need a vault that has the notes they read. |
| Port 8000 is in use | Start with `--port 8001` (or any free port) and open that address. |
| The screens show nothing | The vault may not have the notes the plugin reads. The host reads only `.md` files under the vault folder. |

## Reporting a problem

Send us:
1. The exact command you ran (leave out personal paths if you like).
2. The terminal output, including any "not loaded" lines.
3. The contents of `http://127.0.0.1:8000/host/plugins`.
4. Your Python version (`python --version`) and operating system.
