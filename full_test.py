"""
This is a test of the full pipeline from natural language to query results.
"""

from __future__ import annotations

import sys
from pathlib import Path
from rdflib import Graph
from transformation_algebra.namespace import TA, RDF
from transformation_algebra.query import TransformationQuery
from transformation_algebra.util.store import Fuseki
from cct.language import cct
from geo_question_parser.transformation_query import parse_question

store = Fuseki("http://localhost:3030/cct")

for arg in sys.argv[1:]:
    name = Path(arg).stem
    g = Graph()
    g.parse(arg, "ttl")

    expected_query = TransformationQuery(cct, g)

    root = g.value(None, RDF.type, TA.Task, any=False)
    question = str(g.value(root, TA.question, any=False) or "")

    if question:
        print("Question:", question)

        print
        print("Expected query:")
        print(expected_query.graph.serialize(format="turtle"))
        print(expected_query.sparql())

        print("Firing query...")
        print(store.query(expected_query))

        print()
        print("Parsed actual query:")
        actual_query = parse_question(question)

        print(actual_query.graph.serialize(format="turtle"))
        print(actual_query.sparql())

        print()
        print("Firing query...")
        print(store.query(actual_query))
    else:
        print(f"Skipping {arg}")
