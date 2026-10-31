![Banner](banner.png)

# dm-data-format-permutator
Randomly permutes the format of data within a column while preserving its inherent characteristics (e.g., date formats, currency formats, telephone number formats). Takes a CSV file and a column name as input. - Focused on Tools designed to generate or mask sensitive data with realistic-looking but meaningless values

## Install
`git clone https://github.com/ShadowStrikeHQ/dm-data-format-permutator`

## Usage
`./dm-data-format-permutator [params]`

## Parameters
- `-h`: Show help message and exit
- `csv_file`: The CSV file to process (positional).
- `column_name`: The name of the column to permute (positional).
- `-o`: The output CSV file (default: <input_file>_masked.csv).
- `-l`: Faker locale (e.g., en_US, fr_FR). Defaults to en_US.

## Behavior notes
- The input is read and validated before the output file is opened. A run that fails, for example a missing column, an empty input, or an undecodable input, creates no output file.
- The output file may not be the input file. If the resolved output path is the input file, by the same spelling or through a symlink, the run refuses at exit 1 before any file is opened and the input is left untouched.
- The run counts the cells it actually replaces in the named column. If no cell was replaced, for example a column of dates that do not parse, the run prints "No values were permuted.", exits 1, and writes no output file.

## License
Copyright (c) ShadowStrikeHQ
