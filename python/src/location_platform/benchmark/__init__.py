"""Business-facing benchmark computation and reporting.

Compares current-network and optimized-archive candidate sets. Evaluates
candidate sets it is given; it never selects or scores optimizer facilities
itself (that remains Java's job) and never re-derives or re-validates
scenario facilities independently — it is a read-only consumer of
``scenario.facilities[]``.
"""
