from datetime import timedelta
from pathlib import Path


DRIVE_FOLDER_ID: str
WORLD_BACKUPS_FOLDER: Path
BASE_DIR = Path(__file__).resolve().parent
PINNED_WORLD_BACKUPS_FILE = BASE_DIR / 'pinned_world_backups.txt'
LAST_UPLOADED_WORLD_BACKUP_FILE = BASE_DIR / 'last_uploaded_world_backup.txt'

# The size of each world backup zip file changes every day, even if nobody has logged in to the world,
# simply due to the Minecraft server doing small adjustments to the state of the world while running
# (let's call them Server Simulation Changes - SSCs).
# This means that it's most likely not useful to back up the world when no changes by players have been done
# (in which case the file size difference is usually significantly greater).
# This value was chosen from comparing sizes of previous world backups;
# more specifically, the following file sizes (ignore that it's kind of structured like a table; it's really just one list):
#     1 030 175 KB        261 349 KB        261 394 KB
#     1 030 179 KB        261 349 KB        261 395 KB
#     1 030 169 KB        261 348 KB        261 395 KB
#     1 030 162 KB        261 349 KB        261 399 KB
#     1 030 166 KB        261 356 KB        261 395 KB
#     Here, the first column only contains SSCs, with a size diff of 1.0000165 between the largest and the smallest size.
#     Likewise with the third column, which has a size diff of 1.0000191 between the largest and the smallest size.
#     Aside from the obvious jump in size from 1 030 166 to 261 349 KB (when we made a new world),
#     the difference between 261 356 KB and 261 394 KB was caused by players,
#     which is a size diff of 1.000145 - an order of magnitude above the previously mentioned size diffs,
#     which means we probably do not want to ignore the 261 394 KB one.
#     (The slight jump from 261 349 to 261 356 could also have been caused by players,
#     but the difference is so small that it's also fairly likely that it was an SSC.)
SIZE_DIFF_THRESHOLD_FOR_UPLOADING_BACKUP = 0.0001


def get_upload_command_args(file_path: Path) -> list:
    # Uses the Bash script in https://github.com/MAKENTNU/Backup-to-Drive/tree/5451cb99959bc1728317aab908c22c222e29f138
    return ['backup-to-drive', file_path, '-i', DRIVE_FOLDER_ID, '-p']


MIN_FILE_AGE__SURVIVAL_PREDICATE__TUPLES = (
    # Should be sorted in ascending order of strictness
    (timedelta(days=0), lambda info: True),  # keep all backups less than 15 days old
    (timedelta(days=15), lambda info: (info.timestamp.day % 3 == 1  # day 1, 4, 7, ... of each month
                                       or info.size_diff_with_file_before >= SIZE_DIFF_THRESHOLD_FOR_UPLOADING_BACKUP)),
    (timedelta(days=30), lambda info: (info.timestamp.day % 7 == 1  # day 1, 8, 15, 22 and 29 of each month
                                       or info.size_diff_with_file_before >= SIZE_DIFF_THRESHOLD_FOR_UPLOADING_BACKUP)),
    (timedelta(days=60), lambda info: (info.timestamp.day % 14 == 1  # day 1, 15 and 29 of each month
                                       or info.size_diff_with_file_before >= 10 * SIZE_DIFF_THRESHOLD_FOR_UPLOADING_BACKUP)),
    (timedelta(days=180), lambda info: (info.timestamp.day % 14 == 1  # day 1, 15 and 29 of each month
                                        or info.size_diff_with_file_before >= 100 * SIZE_DIFF_THRESHOLD_FOR_UPLOADING_BACKUP)),
    (timedelta(days=365), lambda info: (info.timestamp.day == 1
                                        or info.size_diff_with_file_before >= 0.05)),
    (timedelta(days=2 * 365), lambda info: (info.timestamp.month % 3 == 1  # January, April, July and October
                                            or info.size_diff_with_file_before >= 0.1)),
    (timedelta(days=3 * 365), lambda info: (info.timestamp.month % 6 == 1  # January and July
                                            or info.size_diff_with_file_before >= 0.15)),
    (timedelta(days=4 * 365), lambda info: (info.timestamp.month == 1
                                            or info.size_diff_with_file_before >= 0.25)),
    (timedelta(days=5 * 365), lambda info: False),  # don't keep any backups older than 5 years (except pinned ones)
)

# Set local settings
try:
    from local_settings import *
except ImportError:
    pass
