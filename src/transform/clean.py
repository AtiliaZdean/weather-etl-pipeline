"""
transform stage: validates n cleans raw weather records from the extract stage before theyre allowed into the load stage

design principle: this module never touches the network or the db. its pure data-in, data-out logic, which makes
it the easiest part of the whole pipeline to test in isolation (no mocking required, just call the function with
sample dicts)
"""

def validate_record(record: dict) -> tuple[bool, str | None]:   # is this safe to load at all?
    """
    -   check a single weather rec against data quality rules
    -   returns (is_valid, reason). if is_valid is False, 'reason' explains why - this string is wht we'll store
        in pipeline_runs on rejection, so it needs to be genuinely useful for debugging later, not just "bad row"
    """
    required_fields = ["temp_max_c", "temp_min_c", "temp_mean_c", "rainfall_mm"]

    # rule 1: reject if any core field is missing (None)
    # open-meteo returns null for fields it couldn't measure tht day
    for field in required_fields:
        if record.get(field) is None:
            return False, f"missing value for {field}"

    # rule 2: physically impossible - min temperature can never exceed max
    if record["temp_min_c"] > record["temp_max_c"]:
        return False, f"temp_min_c ({ record['temp_min_c'] }) > temp_max_c ({ record['temp_max_c'] })"

    # rule 3: rainfall can be zero, never negative
    if record["rainfall_mm"] < 0:
        return False, f"negative rainfall_mm ({ record['rainfall_mm'] })"

    return True, None

def flag_outliers(record: dict) -> list[str]:   # is this worth 's attention?
    """
    soft plausibility checks
    these do not reject the record, they just return warning strings for logging. Msia's tropical climate keeps
    temp in a fairly narrow band, so values outside this range are unusual enough to be worth a note, but not
    necessarily wrong
    """
    warnings = []
    if record["temp_max_c"] > 40:
        warnings.append(f"unusually high temp_max_c ({ record['temp_max_c'] })")
    if record["temp_max_c"] < 15:
        warnings.append(f"unusually low temp_max_c ({ record['temp_max_c'] })")
    return warnings

def clean_records(raw_records: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    -   runs the full validation pass over a batch of records
    -   returns (valid_records, rejected_records). rejected_records is a list of dicts like { "record": ...,
        "reason": ...} - kept alongside the reason so a human (or pipeline_runs log) can see exactly wht was
        thrown out n why, rather thn just a count
    -   outlier warnings r printed but dont affect wht get returned - theyre informational only, per design decision
    """
    valid_records = []
    rejected_records = []

    for record in raw_records:
        is_valid, reason = validate_record(record)
        if not is_valid:
            rejected_records.append({ "record": record, "reason": reason })
            continue

        warnings = flag_outliers(record)
        for warning in warnings:
            print(f"WARNING: { record['city_name'] } { record['reading_date'] }: {warning}")

        valid_records.append(record)

    return valid_records, rejected_records