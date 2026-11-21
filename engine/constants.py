# Editable allowlist of providers used for UPI IDs. Keep this separate from
# validation logic so provider coverage can be reviewed and updated easily.
UPI_PROVIDERS = frozenset({
    "okhdfcbank",
    "oksbi",
    "okicici",
    "okaxis",
    "paytm",
})
