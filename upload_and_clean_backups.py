import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Union

import settings


NEARLY_ZERO = 0.1  # can't be 0, to prevent division by zero


def size_diff(size1: int, size2: int) -> float:
    size_increase_ratio = max(size1, size2) / min(size1, size2)
    return size_increase_ratio - 1


def parse_backup_file_timestamp(file: Union[Path, str]) -> datetime:
    if not isinstance(file, Path):
        file = Path(file)
    file_timestamp_parts = (int(part) for part in file.stem.split('-'))  # this will be, in order: year, month, day, hour, minute, second
    return datetime(*file_timestamp_parts)


def parse_pinned_backup_file_line(line: str) -> str:
    # Ignore line comments
    name, _sep, _comment = line.partition("#")
    return name.strip()


def delete_file(file: Path) -> bool:
    if file.name not in pinned_world_backup_names:
        file.unlink(missing_ok=True)
        return True
    return False


@dataclass
class BackupInfo:
    file: Path
    timestamp: datetime
    size_diff_with_file_before: float

    def __init__(self, file: Path, timestamp: datetime):
        self.file = file
        self.timestamp = timestamp


# --- Find relevant file info ---
# These lists should all be sorted in ascending order, so that the oldest files come first
all_files = sorted(settings.WORLD_BACKUPS_FOLDER.iterdir())
all_file_names = [file.name for file in all_files]
file_sizes = {file: os.path.getsize(file) for file in all_files}
backup_info_list = []
for file in all_files:
    backup_info = BackupInfo(file, parse_backup_file_timestamp(file))
    backup_info_list.append(backup_info)

pinned_world_backup_names = {parse_pinned_backup_file_line(line) for line in settings.PINNED_WORLD_BACKUPS_FILE.read_text().splitlines()}
last_uploaded_world_backup_name = settings.LAST_UPLOADED_WORLD_BACKUP_FILE.read_text().strip()
try:  # Try finding an existing file with the same name as `LAST_UPLOADED_WORLD_BACKUP_FILE` contains
    last_uploaded_world_backup_index = all_file_names.index(last_uploaded_world_backup_name)
    files_since_last_backup = all_files[last_uploaded_world_backup_index + 1:]
    last_file_size = file_sizes[all_files[last_uploaded_world_backup_index]]
except ValueError:
    print(f"Unable to find '{last_uploaded_world_backup_name}' among the files inside {settings.WORLD_BACKUPS_FOLDER}")
    try:  # If the timestamp in `last_uploaded_world_backup_name` is valid, resume backing up from that point in time
        last_uploaded_timestamp = parse_backup_file_timestamp(last_uploaded_world_backup_name)
        print(f"Using {last_uploaded_timestamp} as the timestamp to resume backup from")
        # Find the backup files that are newer than the timestamp:
        for i, backup_info in enumerate(backup_info_list):
            if last_uploaded_timestamp == backup_info.timestamp:
                files_since_last_backup = all_files[i + 1:]
                last_file_size = file_sizes[backup_info.file]
                break
            elif last_uploaded_timestamp < backup_info.timestamp:
                files_since_last_backup = all_files[i:]
                if i > 0:
                    last_file_size = file_sizes[all_files[i - 1]]
                else:
                    last_file_size = NEARLY_ZERO
                break
        else:  # No backup files were newer
            files_since_last_backup = []
            # Setting this variable is strictly unnecessary, as it won't be used as long as `files_since_last_backup` is empty
            last_file_size = file_sizes[-1]
    except (TypeError, ValueError):
        # Unable to get any info from `last_uploaded_world_backup_name`, so just start backing up from the beginning
        files_since_last_backup = all_files
        last_file_size = NEARLY_ZERO

# --- Find files to upload ---
files_to_upload = []
for file in files_since_last_backup:
    file_size = file_sizes[file]
    if (
            file.name in pinned_world_backup_names
            or size_diff(file_size, last_file_size) >= settings.SIZE_DIFF_THRESHOLD_FOR_UPLOADING_BACKUP
    ):
        files_to_upload.append(file)

    last_file_size = file_size

# --- Upload the found files ---
for file in files_to_upload:
    file_path = file.resolve()
    completed_process = subprocess.run(settings.get_upload_command_args(file_path))
    if completed_process.returncode != 0:
        raise RuntimeError(f"Failed to upload the following file: {file_path}")

    settings.LAST_UPLOADED_WORLD_BACKUP_FILE.write_text(f"{file.name}\n")

# --- Clean up the backup files ---
now = datetime.utcnow()
for min_file_age, survival_predicate in settings.MIN_FILE_AGE__SURVIVAL_PREDICATE__TUPLES:
    last_file_size = NEARLY_ZERO
    min_file_timestamp = now - min_file_age

    for backup_info in backup_info_list.copy():  # iterate through a copy, as elements are removed from the original below
        file_size = file_sizes[backup_info.file]
        backup_info.size_diff_with_file_before = size_diff(file_size, last_file_size)

        # If the file is older than `min_file_age`:
        if backup_info.timestamp < min_file_timestamp:
            if not survival_predicate(backup_info):
                success = delete_file(backup_info.file)
                if success:
                    print(f"Deleted file with {backup_info}")
                backup_info_list.remove(backup_info)
        else:
            # Remove from the list, so that it's not needlessly compared again
            backup_info_list.remove(backup_info)

        last_file_size = file_size
