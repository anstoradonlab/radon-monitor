import datetime

# database time format
DBTFMT = "%Y-%m-%d %H:%M:%S"

def format_date(t):
    """
    Format the timestamp so that the timezone gets dropped
    (All dates are assumed to be set to UTC)
    """
    # Enforce the use of timezone-aware datetimes
    if not t.tzinfo == datetime.timezone.utc:
        print("t.tzinfo is not UTC")
    return t.strftime(DBTFMT)


def parse_date(tstr):
    return datetime.datetime.strptime(tstr, DBTFMT).replace(
        tzinfo=datetime.timezone.utc
    )

def enquote(itm):
    """
    Add double quotes to a string so that it can be used as an SQL table or column name

    # TODO: decide how to handle SQL quoting/safety in general.  At present, all 
    # dynamic names come from the datalogger or the database, so it should not be
    # possible for them to be badly formed.
    """
    return '"' + itm + '"'
