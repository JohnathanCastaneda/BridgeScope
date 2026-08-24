# Local data files 

## `raw/` 

Contains unchanged files downloaded from external sources.

Raw files are excluded from Git. Each downloaded file must have its origin, retrieval timestamp, file size, and SHA-256 checksum recorded under `docs/data/`. 

Do not edit, normalize, reformat, or resave files in this directory. 

## `samples/` 

Will contain small, representative fixtures that are safe to commit and use in automated tests. 

Samples must be created through a documented process and should include both ordinary records and known edge cases.