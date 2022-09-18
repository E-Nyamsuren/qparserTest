"""
This module connects the full pipeline for transforming a natural language
question into a transformation query. In dire need of modularisation.
"""

from geo_question_parser.Identify import QuestionParser, TypesToQueryConverter
from rdflib import RDF
from rdflib.term import BNode
from transformation_algebra import \
    TransformationGraph, TransformationQuery, TA
from transformation_algebra.type import Product, TypeOperation
from cct.language import cct, R3, R2, Obj, Reg


def question2query(queryEx: dict) -> TransformationQuery:
    """
    Converts a query formatted as a dictionary into a `TransformationQuery`,
    which can be in turn translated to a SPARQL query.
    """
    # This should probably go in a more sane place eventually, when the
    # structure of the modules is more stable

    g = TransformationGraph(cct)
    task = BNode()
    g.add((task, RDF.type, TA.Task))

    def f(q: dict) -> BNode:
        node = BNode()
        t = cct.parse_type(q['after']['cct']).concretize(replace=True)

        # This is a temporary solution: R(x * z, y) is for now converted to the
        # old-style R3(x, y, z)
        if isinstance(t.params[0], TypeOperation) and \
                t.params[0].operator == Product:
            t = R3(t.params[0].params[0], t.params[1], t.params[0].params[1])

        # Another temporary solution. the question parser often returns `R(Obj,
        # x)` where the manually constructed queries ("gold standard") would
        # use `R(Obj, Reg * x)`. So, whenever we encounter the former, we will
        # manually also allow the latter
        # cf. <https://github.com/quangis/transformation-algebra/issues/79#issuecomment-1210661153>
        if isinstance(t.params[0], TypeOperation) and \
                t.operator == R2 and \
                t.params[0].operator == Obj and \
                t.params[1].operator != Product:
            g.add((node, TA.type, cct.uri(R2(t.params[0], Reg * t.params[1]))))

        g.add((node, TA.type, cct.uri(t)))
        for b in q.get('before') or ():
            g.add((node, TA['from'], f(b)))

        return node

    g.add((task, TA.output, f(queryEx)))
    return TransformationQuery(cct, g)


def parse_question(question: str) -> TransformationQuery:
    """
    Parse a natural language question into a `TransformationQuery` object.
    """

    parser = QuestionParser(None)
    qParsed = parser.parseQuestion(str(question))
    cctAnnotator = TypesToQueryConverter()
    cctAnnotator.algebraToQuery(qParsed, True, True)
    cctAnnotator.algebraToExpandedQuery(qParsed, False, False)
    return question2query(qParsed['queryEx'])
