import argparse
import csv
import logging
import random
import sys
from pathlib import Path
from faker import Faker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.

    Returns:
        argparse.ArgumentParser: The argument parser object.
    """
    parser = argparse.ArgumentParser(description="Randomly permutes the format of data within a column while preserving its inherent characteristics.")
    parser.add_argument("csv_file", help="The CSV file to process.")
    parser.add_argument("column_name", help="The name of the column to permute.")
    parser.add_argument("-o", "--output_file", help="The output CSV file (default: <input_file>_masked.csv)", default=None)
    parser.add_argument("-l", "--locale", help="Faker locale (e.g., en_US, fr_FR). Defaults to en_US.", default="en_US")

    return parser

def permute_data_format(data, data_type, locale="en_US"):
    """
    Permutes the format of the given data based on its type.

    Args:
        data (str): The data to permute.
        data_type (str): The type of data (e.g., 'date', 'currency', 'telephone').
        locale (str): The Faker locale to use.

    Returns:
        str: The permuted data, or the original data if permutation fails.
    """
    # A new Faker is built for every value this function is called
    # on, which in main is once per row of the column. Nothing seeds
    # any of them, so no run can be repeated, and construction cost is
    # paid per cell rather than once per file.
    fake = Faker(locale)
    try:
        if data_type == 'date':
            # Only the two formats detect_data_type recognises are parsed,
            # with strptime from the standard library. The old code imported
            # dateutil here, but python-dateutil was never declared in
            # requirements.txt, so on a clean install every date silently
            # fell through unchanged.
            from datetime import datetime
            for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
                try:
                    datetime.strptime(data, fmt)
                    return fake.date_time_this_decade().strftime('%Y-%m-%d')
                except ValueError:
                    continue
            logging.warning(f"Could not parse date: {data}. Returning original value.")
            return data
        elif data_type == 'currency':
            # The amount is parsed only to prove the value parses. The
            # replacement is always a three digit figure, so a salary
            # and a coffee price come out at the same scale: the dollar
            # and cents shape is kept, the magnitude is not.
            amount = float(data.replace('$', '').replace(',', ''))  # Remove currency symbols and commas

            # random_number returns an int, so the cents must be zero
            # padded: without it about a fifth of outputs came out with a
            # single decimal digit, which is not a currency format.
            return f"${fake.random_number(digits=3)}.{fake.random_number(digits=2):02d}"
        elif data_type == 'telephone':
            return fake.phone_number()
        else:
            logging.warning(f"Unknown data type: {data_type}. Returning random string.")
            return fake.pystr(min_chars=len(data), max_chars=len(data))
    except Exception as e:
        logging.error(f"Error permuting data: {e}. Returning original value.")
        return data  # Return original data on any error to prevent data loss

def detect_data_type(data):
    """
    Detects the type of data based on its format. This is a very basic implementation.

    Args:
        data (str): The data to analyze.

    Returns:
        str: The detected data type (e.g., 'date', 'currency', 'telephone', or 'unknown').
    """
    if isinstance(data, str):
        data = data.strip()
    if not isinstance(data, str) or not data:
        return 'unknown'  # Handle empty or non-string data
    
    # Basic date detection
    # Every pattern here is a prefix test: re.match anchors at the
    # start and none of the patterns ends with a $ anchor, so a value
    # only has to begin like a date, an amount, or a phone number to
    # be classified as one, whatever follows the matched prefix.
    import re
    if re.match(r'\d{4}-\d{2}-\d{2}', data):
        return 'date'
    if re.match(r'\d{2}/\d{2}/\d{4}', data): #added basic date detection
        return 'date'
    if re.match(r'\$\d+(\,\d{3})*(\.\d{2})?', data):
        return 'currency'
    if re.match(r'(\+\d{1,3})?\s?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', data):
        return 'telephone' #Very basic phone number detection

    return 'unknown'

def main():
    """
    Main function to execute the data format permutation process.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    csv_file = args.csv_file
    column_name = args.column_name
    output_file = args.output_file or csv_file.replace(".csv", "_masked.csv") #Default output file name
    locale = args.locale

    # The output may not name the input file, in any spelling. Resolved
    # paths are compared, so a symlink alias is caught as well as the
    # same string. Refuse before any file is opened.
    if Path(output_file).resolve() == Path(csv_file).resolve():
        logging.error("Output file must not be the input file. Choose a different output path.")
        sys.exit(1)

    try:
        # Read and validate the whole input first. The output file is
        # opened only after this succeeds, so a failed run (missing
        # column, empty input, undecodable input) creates no output
        # file. The old order opened the output first, which truncated
        # the input itself when both names pointed at it and left a
        # created output file behind on ordinary failures.
        with open(csv_file, 'r', newline='') as infile:
            reader = csv.reader(infile)

            try:
                header = next(reader)  # Read the header row
            except StopIteration:
                logging.error(f"Input file is empty: {csv_file}")
                sys.exit(1)

            try:
                column_index = header.index(column_name)
            except ValueError:
                logging.error(f"Column '{column_name}' not found in the CSV file.")
                sys.exit(1)

            output_rows = []
            replaced = 0
            for row in reader:
                try:
                    original_data = row[column_index]
                    data_type = detect_data_type(original_data)
                    masked_data = permute_data_format(original_data, data_type, locale)
                    if masked_data != original_data:
                        replaced += 1
                    row[column_index] = masked_data
                    output_rows.append(row)
                except IndexError:
                    logging.warning(f"Row has fewer columns than expected. Skipping row.")
                    output_rows.append(row) # Still write the row to avoid shifting data unexpectedly
                except Exception as e:
                    logging.error(f"Error processing row: {e}. Writing original row.")
                    output_rows.append(row) # Write original row on error

        if replaced == 0:
            # Nothing in the named column was permuted, so this run must
            # not report completion and must not write an output file.
            print("No values were permuted.")
            sys.exit(1)

        with open(output_file, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(header)
            writer.writerows(output_rows)
        logging.info(f"Data masking completed. Output written to {output_file}")

    except FileNotFoundError:
        logging.error(f"File '{csv_file}' not found.")
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Usage Examples:

1.  Basic Usage:
    python main.py data.csv phone_numbers

    This will read the 'data.csv' file, permute the data in the 'phone_numbers' column,
    and save the masked data to 'data_masked.csv'. It will default to en_US locale.

2.  Specifying Output File:
    python main.py data.csv credit_cards -o masked_data.csv

    This is similar to the first example, but the output will be saved to 'masked_data.csv'.

3.  Specifying Locale:
    python main.py data.csv dates -l fr_FR

    This will use the French locale ('fr_FR') for generating masked data, which affects date formats
    and other locale-specific data.  If data.csv has dates, it will replace them with new,
    fake dates generated using the French locale.
"""