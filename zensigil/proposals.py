"""Optional action contracts for reviewable proposal fields, never connectors."""
import json
import math

from .contracts import (MAX_CONTRACT_BYTES, MAX_DIAGNOSTICS, contract_diagnostics,
                        field_path, _validated_input_diagnostics)
from .syntax import IDENT, WORDS


def proposal_diagnostic(code, path, message, *, action=None, location=None, source=""):
    location = location or {}
    line, column = location.get("line", 1), location.get("column", 1)
    lines = source.split("\n")
    result = {"code": code, "message": message, "line": line, "column": column,
              "source_line": lines[line - 1] if 0 < line <= len(lines) else "",
              "output_path": path}
    if action is not None:
        result["action"] = action
    return result


def _mapping_error(contract):
    """Bound the mapping before serialization, including non-JSON Python values."""
    if type(contract) is not dict:
        return "Proposal contract must map action names to object contracts."
    stack, count, characters = [(contract, 0)], 0, 0
    while stack:
        value, depth = stack.pop()
        count += 1
        if count > 10000 or depth > 33:
            return "Proposal contract exceeds 10,000 entries or 33 levels of nesting."
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                return "Proposal contract field names must be strings."
            stack.extend((child, depth + 1) for pair in value.items() for child in pair)
        elif type(value) is list:
            stack.extend((child, depth + 1) for child in value)
        elif type(value) is str:
            try:
                characters += len(value.encode("utf-8"))
            except UnicodeError:
                return "Proposal contract must contain valid Unicode text."
            if characters > MAX_CONTRACT_BYTES:
                return "Proposal contract exceeds 256 KiB."
        elif value is None or type(value) is bool:
            pass
        elif type(value) in (int, float):
            if abs(value) > 1e100 or not math.isfinite(value):
                return "Proposal contract numbers must be finite and have magnitude at most 1e100."
        else:
            return "Proposal contract must contain only JSON values."
    if len(json.dumps(contract, ensure_ascii=True).encode("utf-8")) > MAX_CONTRACT_BYTES:
        return "Proposal contract exceeds 256 KiB."
    return None


def proposal_contract_diagnostics(contract):
    """Validate every definition, including actions which a program never emits."""
    issue = _mapping_error(contract)
    if issue:
        return [proposal_diagnostic("E_PROPOSAL_CONTRACT", "$", issue)]
    errors = []
    for action, schema in contract.items():
        path = field_path("$", action)
        if not IDENT.fullmatch(action) or action in WORDS:
            errors.append(proposal_diagnostic("E_PROPOSAL_CONTRACT", path,
                          "Action names must be ZenSigil identifiers and cannot be reserved words.", action=action))
        else:
            issues = contract_diagnostics(schema)
            for error in issues:
                errors.append(proposal_diagnostic("E_PROPOSAL_CONTRACT", path + error["data_path"][1:],
                                                  error["message"], action=action))
            if not issues and schema.get("type") not in ("object", ["object"]):
                errors.append(proposal_diagnostic("E_PROPOSAL_CONTRACT", path + ".type",
                              'Every action contract must explicitly declare type "object" for its fields.', action=action))
        if len(errors) >= MAX_DIAGNOSTICS:
            break
    return errors[:MAX_DIAGNOSTICS]


def proposal_diagnostics(proposals, contract, source=""):
    """Validate emitted fields against an already validated action mapping."""
    errors = []
    enum_values = {}
    for index, proposal in enumerate(proposals):
        action, location = proposal["action"], proposal["source"]
        path = f"$.proposals[{index}]"
        if action not in contract:
            errors.append(proposal_diagnostic("E_PROPOSAL", path + ".action",
                          f"Action {action!r} is not declared in the proposal contract. Add its contract or change the program.",
                          action=action, location=location, source=source))
        else:
            for error in _validated_input_diagnostics(proposal["fields"], contract[action], enum_values):
                message = error["message"].replace("Fix the input value", "Fix the proposal field")
                errors.append(proposal_diagnostic("E_PROPOSAL", path + ".fields" + error["data_path"][1:],
                                                  message, action=action, location=location, source=source))
                if len(errors) >= MAX_DIAGNOSTICS:
                    break
        if len(errors) >= MAX_DIAGNOSTICS:
            break
    return errors
