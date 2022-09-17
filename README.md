# Backup-and-cleanup-Minecraft-Worlds
This was created to back up the backups created by [MSM](https://msmhq.com/) (in the form of daily generated ZIP files),
while keeping a select few of them locally.
These ZIP files tend to be fairly large (ranging from a few hundred MB to multiple GB),
so this script ([`upload_and_clean_backups.py`](/upload_and_clean_backups.py)) was created to avoid backing up / keeping every single ZIP file,
but only the ones that contain notable changes (determined by file size difference).

### Setup
Create a `local_settings.py` file in the same folder as [`settings.py`](/settings.py), and define the following variables:
* `DRIVE_FOLDER_ID`: the ID of the Google Drive folder you want the backed up files uploaded to, as a string
* `WORLD_BACKUPS_FOLDER`: a path to the folder containing the world backup files, as a `Path` object

Also review the settings in [`settings.py`](/settings.py),
in case you want to customize any of the other settings (by defining them in `local_settings.py`),
like the command used for uploading the backup files
(which by default uses the Bash script in [the Backup-to-Drive repo](https://github.com/MAKENTNU/Backup-to-Drive)).

### Usage
Run the script like this:
```bash
python upload_and_clean_backups.py
```
