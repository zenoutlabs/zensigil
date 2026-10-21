"""Run from the repository root: python3 -m examples.embed

With an installed wheel, copy this file anywhere and run python embed.py.
No network calls, API keys or third-party Python dependencies.
"""
import json
from zensigil import check, run

source = '''rule "Reading reminder":
    when not book.finished:
        propose read_next(id: book.id, explanation: "This book is unfinished.")
'''
data = {"book": {"id": "B1", "finished": False}}
input_contract = {
    "type": "object",
    "required": ["book"],
    "properties": {"book": {
        "type": "object", "required": ["id", "finished"],
        "properties": {"id": {"type": "string"}, "finished": {"type": "boolean"}}
    }},
}
proposal_contract = {
    "read_next": {
        "type": "object", "required": ["id", "explanation"],
        "properties": {"id": {"type": "string"}, "explanation": {"type": "string"}},
        "additionalProperties": False,
    }
}

if __name__ == "__main__":
    checked = check(source, data, contract=input_contract,
                    proposal_contract=proposal_contract)
    result = run(source, data, contract=input_contract,
                 proposal_contract=proposal_contract) if checked["ok"] else checked
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
